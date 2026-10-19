"""Cached, serialised access to the financial engine.

One analysis (the current mix plus three recommendations) takes about a second, so results are kept in a
small cache keyed by the profile's content and the cover basis.

The engine always runs on ONE dedicated daemon thread:
- SciPy's SLSQP solver has historically kept shared state, so two solves are never allowed to overlap;
- a request waits at most `timeout` seconds and then gets a clear "busy" answer, instead of hanging;
- a daemon thread cannot stop the server from shutting down if a solve ever sticks.
(During Phase 1 testing a few parity runs stalled for minutes without a reproducible cause; see the Phase 1 report.)
"""
from __future__ import annotations

import json
import queue
import threading
from collections import OrderedDict
from concurrent.futures import Future

import pandas as pd

from fo import engine
from fo import plan as fo_plan
from fo.personas import Profile, profile_to_dict

from . import convert
from . import schemas as s

COMPARISON_SCENARIO = "Equities fall 25%"
CACHE_SIZE = 64


class AnalysisTimeout(Exception):
    """The engine did not answer within the allowed time."""


class _EngineThread:
    """Runs callables one at a time on a single daemon thread."""

    def __init__(self) -> None:
        self._jobs: queue.Queue = queue.Queue()
        threading.Thread(target=self._run, name="engine", daemon=True).start()

    def _run(self) -> None:
        while True:
            job = self._jobs.get()
            if job is None:
                return
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

    def close(self) -> None:
        self._jobs.put(None)


class AnalysisService:
    def __init__(self, daily: pd.DataFrame, source: str, timeout: float = 90.0):
        self.daily = daily
        self.source = source
        self.timeout = timeout
        self.inputs = engine.estimate_inputs(daily)
        self._engine = _EngineThread()
        self._cache_lock = threading.Lock()
        self._cache: OrderedDict[tuple[str, str], s.AnalysisOut] = OrderedDict()

    def close(self) -> None:
        self._engine.close()

    def _cached(self, key) -> s.AnalysisOut | None:
        with self._cache_lock:
            hit = self._cache.get(key)
            if hit is not None:
                self._cache.move_to_end(key)
            return hit

    def analyse(self, profile_id: int, profile: Profile, basis: str) -> s.AnalysisOut:
        key = (json.dumps(profile_to_dict(profile), sort_keys=True), basis)

        def job() -> s.AnalysisOut:
            hit = self._cached(key)  # an identical request queued ahead of this one may have just filled it
            if hit is None:
                hit = self._compute(profile_id, profile, basis)
                with self._cache_lock:
                    self._cache[key] = hit
                    while len(self._cache) > CACHE_SIZE:
                        self._cache.popitem(last=False)
            return hit

        hit = self._cached(key)
        result = hit if hit is not None else self._engine.call(job, self.timeout)
        return result.model_copy(update={"profile_id": profile_id})

    def _compute(self, profile_id: int, profile: Profile, basis: str) -> s.AnalysisOut:
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
        return s.AnalysisOut(
            profile_id=profile_id, basis=basis, basis_label=engine.COVER_BASES[basis], data_source=self.source,
            current=convert.portfolio_out(current),
            current_projection=convert.projection_rows(engine.project_corpus(profile, current.exp_return)),
            options=details,
            upcoming_outflows=convert.outflow_rows(engine.upcoming_outflows(profile, 5)),
            comparison_scenario=COMPARISON_SCENARIO,
            comparison=convert.compare_rows(table),
            comparison_insights=convert.insights_out(engine.comparison_insights(table)),
        )
