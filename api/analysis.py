"""Cached, serialised access to the financial engine.

One analysis (the current mix plus three recommendations) takes about a second, so results are kept in a
small cache keyed by the profile's content and the cover basis.

The engine always runs on ONE dedicated daemon thread:
- SciPy's SLSQP solver has historically kept shared state, so two solves are never allowed to overlap;
- a request waits at most `timeout` seconds and then gets a clear "busy" answer, instead of hanging;
- a daemon thread cannot stop the server from shutting down if a solve ever sticks.

An engine thread NEVER EXITS. The linear-programming solver inside SciPy (HiGHS, called by `engine.solve_weights`) can hang,
spinning a core, or crash the whole process when a thread that has used it ends, on Windows. A bare script that runs `linprog`
in short-lived threads hung in 27 of 30 runs; with a thread that stays alive, 0 of 30 (details in docs/migration/phase-4-report.md).
So a closed service does not stop its thread: the thread goes to a small pool and the next service reuses it.
"""
from __future__ import annotations

import json
import queue
import threading
from collections import OrderedDict
from concurrent.futures import Future
from dataclasses import dataclass

import pandas as pd

from fo import engine
from fo import plan as fo_plan
from fo.personas import Profile, profile_to_dict

from . import convert, history, scenarios
from . import schemas as s

COMPARISON_SCENARIO = "Equities fall 25%"
CACHE_SIZE = 64


class AnalysisTimeout(Exception):
    """The engine did not answer within the allowed time."""


@dataclass(frozen=True)
class _Entry:
    """One finished analysis: the response, and the engine portfolios behind it (history and scenarios reuse them)."""

    out: s.AnalysisOut
    current: engine.Portfolio
    options: list[engine.Portfolio]


_RELEASE = object()  # queued by release(): "after the jobs ahead of this, you are free for the next service"
_POOL: list["_EngineThread"] = []
_POOL_LOCK = threading.Lock()


class _EngineThread:
    """Runs callables one at a time on a single daemon thread that lives for the rest of the process."""

    def __init__(self) -> None:
        self._jobs: queue.Queue = queue.Queue()
        threading.Thread(target=self._run, name="engine", daemon=True).start()

    @classmethod
    def acquire(cls) -> "_EngineThread":
        """A thread nobody is using (kept alive by an earlier service), or a new one."""
        with _POOL_LOCK:
            if _POOL:
                return _POOL.pop()
        return cls()

    def _run(self) -> None:
        while True:  # never returns: see the module docstring
            job = self._jobs.get()
            if job is _RELEASE:
                with _POOL_LOCK:
                    _POOL.append(self)
                continue
            fn, future = job
            if not future.set_running_or_notify_cancel():  # the caller gave up while it was still queued
                continue
            try:
                future.set_result(fn())
            except BaseException as err:  # noqa: BLE001 - handed back to the waiting request
                future.set_exception(err)

    def call(self, fn, timeout: float):
        future: Future = Future()
        self._jobs.put((fn, future))
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            raise AnalysisTimeout from None

    def release(self) -> None:
        """Give the thread back. It finishes whatever is already queued (even a slow job), then waits in the pool."""
        self._jobs.put(_RELEASE)


class AnalysisService:
    def __init__(self, daily: pd.DataFrame, source: str, timeout: float = 90.0):
        self.daily = daily
        self.source = source
        self.timeout = timeout
        self.inputs = engine.estimate_inputs(daily)
        self._engine = _EngineThread.acquire()
        self._cache_lock = threading.Lock()
        self._cache: OrderedDict[tuple[str, str], _Entry] = OrderedDict()

    def close(self) -> None:
        self._engine.release()

    def _cached(self, key) -> _Entry | None:
        with self._cache_lock:
            hit = self._cache.get(key)
            if hit is not None:
                self._cache.move_to_end(key)
            return hit

    def _entry(self, profile: Profile, basis: str) -> _Entry:
        key = (json.dumps(profile_to_dict(profile), sort_keys=True), basis)

        def job() -> _Entry:
            hit = self._cached(key)  # an identical request queued ahead of this one may have just filled it
            if hit is None:
                hit = self._compute(profile, basis)
                with self._cache_lock:
                    self._cache[key] = hit
                    while len(self._cache) > CACHE_SIZE:
                        self._cache.popitem(last=False)
            return hit

        hit = self._cached(key)
        return hit if hit is not None else self._engine.call(job, self.timeout)

    def analyse(self, profile_id: int, profile: Profile, basis: str) -> s.AnalysisOut:
        return self._entry(profile, basis).out.model_copy(update={"profile_id": profile_id})

    def history(self, profile_id: int, profile: Profile, basis: str) -> s.HistoryOut:
        """Value and drawdown curves for the current mix and the three options (cheap once the analysis is cached)."""
        entry = self._entry(profile, basis)
        return history.build(profile_id, basis, self.source, profile.max_drawdown, [entry.current] + entry.options)

    def compare(self, profile_id: int, profile: Profile, basis: str, request: s.ScenarioRequest) -> s.ScenarioComparison:
        """One scenario applied to the current mix and every option. Plain arithmetic: no optimiser run."""
        entry = self._entry(profile, basis)
        return scenarios.compare(profile_id, profile, basis, request, entry.current, entry.options)

    def _compute(self, profile: Profile, basis: str) -> _Entry:
        current = engine.analyse_current(profile, self.daily, basis, self.inputs)
        options = engine.recommend(profile, self.daily, basis, self.inputs)
        details = [
            s.PortfolioDetail(
                portfolio=convert.portfolio_out(pf),
                action_plan=convert.action_rows(engine.action_plan(profile, pf)),
                scenarios=convert.scenario_rows(engine.run_scenarios(profile, pf)),
                insights=convert.insights_out(engine.build_insights(profile, current, pf)),
                ladder=convert.ladder_rows(engine.liquidity_ladder(profile, pf, years=min(profile.horizon_years, 12))),
                projection=convert.projection_rows(engine.project_corpus(profile, pf.exp_return)),
                year_range=s.YearRange(**fo_plan.rolling_year_range(pf.replay_returns)),
            )
            for pf in options
        ]
        table = engine.compare_options(profile, [current] + options, engine.SCENARIOS[COMPARISON_SCENARIO])
        out = s.AnalysisOut(
            profile_id=0, basis=basis, basis_label=engine.COVER_BASES[basis], data_source=self.source,
            current=convert.portfolio_out(current),
            current_projection=convert.projection_rows(engine.project_corpus(profile, current.exp_return)),
            current_ladder=convert.ladder_rows(engine.liquidity_ladder(profile, current, years=min(profile.horizon_years, 12))),
            current_scenarios=convert.scenario_rows(engine.run_scenarios(profile, current)),
            options=details,
            upcoming_outflows=convert.outflow_rows(engine.upcoming_outflows(profile, 5)),
            comparison_scenario=COMPARISON_SCENARIO,
            comparison=convert.compare_rows(table),
            comparison_insights=convert.insights_out(engine.comparison_insights(table)),
        )
        return _Entry(out=out, current=current, options=options)
