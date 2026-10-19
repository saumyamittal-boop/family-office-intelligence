"""The engine runs on one dedicated thread, and a slow or stuck analysis can never hang a request."""
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from api import analysis as analysis_module
from api.analysis import AnalysisService
from fo import engine
from fo.personas import PERSONAS
from tests.helpers import demo

FAMILY = {"legacy": "A", "business": "B", "nextgen": "C", "gap": "D"}


def first_profile(client):
    return client.get("/api/profiles").json()[0]["id"]


def test_a_slow_analysis_answers_busy_in_time_instead_of_hanging(make_client):
    c = make_client(analysis_timeout=0.3)
    demo(c, "legacy")
    pid = first_profile(c)
    service = c.app.state.analysis
    real_compute = service._compute
    service._compute = lambda *a, **k: (time.sleep(1.5), real_compute(*a, **k))[1]

    started = time.perf_counter()
    r = c.get(f"/api/profiles/{pid}/analysis")
    waited = time.perf_counter() - started

    assert r.status_code == 503 and "busy" in r.json()["detail"] and int(r.headers["retry-after"]) > 0
    assert waited < 1.2, f"the request should give up after about 0.3 s, took {waited:.2f} s"

    service._compute = real_compute
    # The slow job is still running on the engine thread. Once it finishes its answer lands in the cache, and the service recovers
    # by itself. Poll instead of sleeping a fixed time, so a busy machine cannot make this test flaky.
    status = 503
    for _ in range(40):
        time.sleep(0.5)
        status = c.get(f"/api/profiles/{pid}/analysis").status_code
        if status == 200:
            break
    assert status == 200


def test_a_request_that_gave_up_while_queued_is_not_computed_later(make_client):
    c = make_client(analysis_timeout=0.2)
    demo(c, "legacy")
    pid = first_profile(c)
    service = c.app.state.analysis
    real_compute = service._compute
    calls = []

    def slow(*a, **k):
        calls.append(1)
        time.sleep(0.8)
        return real_compute(*a, **k)

    service._compute = slow
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(c.get, f"/api/profiles/{pid}/analysis", params={"basis": "all"})
        time.sleep(0.05)
        second = pool.submit(c.get, f"/api/profiles/{pid}/analysis", params={"basis": "strict"})
        assert first.result().status_code == 503 and second.result().status_code == 503
    time.sleep(1.2)
    assert len(calls) == 1  # the queued "strict" request was cancelled, so it never ran


def test_simultaneous_analyses_each_return_exactly_what_the_engine_gives_alone(make_client, sample_returns):
    clients = {family: make_client() for family in FAMILY}
    for family, c in clients.items():
        demo(c, family)

    def fetch(family):
        c = clients[family]
        return family, c.get(f"/api/profiles/{first_profile(c)}/analysis", params={"basis": "all"}).json()

    with ThreadPoolExecutor(4) as pool:
        results = dict(pool.map(fetch, FAMILY))

    for family, data in results.items():
        alone = engine.recommend(PERSONAS[FAMILY[family]], sample_returns, "all")
        for api_option, direct in zip(data["options"], alone):
            assert api_option["portfolio"]["exp_return"] == pytest.approx(direct.exp_return, abs=1e-12)
            assert api_option["portfolio"]["max_dd"] == pytest.approx(direct.max_dd, abs=1e-12)
            assert api_option["portfolio"]["weights_sleeve"] == pytest.approx(list(direct.weights_sleeve), abs=1e-12)


def test_the_engine_thread_is_a_daemon_so_a_stuck_solve_cannot_keep_the_server_from_exiting(make_client):
    make_client()
    thread = next(t for t in threading.enumerate() if t.name == "engine")
    assert thread.daemon


# ---- An engine thread never exits (SciPy's HiGHS solver hangs or crashes the process when a thread that used it ends) -------
def make_service(sample_returns, timeout=5.0):
    return AnalysisService(sample_returns, "sample", timeout)


def engine_threads() -> list[threading.Thread]:
    return [t for t in threading.enumerate() if t.name == "engine"]


def test_a_closed_service_hands_its_thread_to_the_next_one_instead_of_ending_it(sample_returns):
    first = make_service(sample_returns)
    thread = first._engine
    first.close()
    deadline = time.time() + 5
    while time.time() < deadline and thread not in analysis_module._POOL:
        time.sleep(0.01)
    second = make_service(sample_returns)
    assert second._engine is thread  # reused, not replaced
    assert second._engine.call(lambda: threading.current_thread().name, 5) == "engine"
    second.close()


def test_opening_and_closing_many_services_does_not_grow_the_number_of_engine_threads(sample_returns):
    before = len(engine_threads())
    for _ in range(25):
        service = make_service(sample_returns)
        assert service._engine.call(lambda: 1 + 1, 5) == 2
        service.close()
        time.sleep(0.01)
    assert len(engine_threads()) <= before + 1  # at most the one the loop itself needed
    assert all(t.is_alive() for t in engine_threads())  # and none of them ended


def test_a_thread_still_busy_when_its_service_closes_finishes_that_job_before_anyone_reuses_it(sample_returns):
    service = make_service(sample_returns)
    thread = service._engine
    started, results = threading.Event(), []

    def slow():
        started.set()
        time.sleep(0.4)
        results.append("done")

    with ThreadPoolExecutor(1) as pool:
        running = pool.submit(thread.call, slow, 5)
        assert started.wait(5)
        service.close()  # the job is still running
        other = make_service(sample_returns)
        assert other._engine is not thread  # not free yet, so a different thread is used
        other.close()
        running.result()
    assert results == ["done"]
    deadline = time.time() + 5
    while time.time() < deadline and thread not in analysis_module._POOL:
        time.sleep(0.01)
    assert thread in analysis_module._POOL  # and now it is free again


SCRIPT = """
import sys
from scipy.optimize import linprog
from api.analysis import _EngineThread

def solve():
    r = linprog(c=[1.0, 2.0, 3.0], A_ub=[[-1, -1, -1]], b_ub=[-1], bounds=[(0, None)] * 3, method="highs")
    return bool(r.success)

# Back to back, with nothing in between: the next thread is created while the last one is still leaving.
for i in range(int(sys.argv[1])):
    thread = _EngineThread()
    assert thread.call(solve, 20) is True
    thread.release()
print("finished", flush=True)
"""


def test_releasing_engine_threads_after_real_linprog_solves_never_hangs_or_crashes_the_process(tmp_path):
    """Regression for the stall seen since Phase 1.

    Run in a separate process with a time limit, because the failure is the whole process freezing (or crashing) in native
    code, which a test in this process could not survive. With engine threads that exit, a bare loop like this hung in
    27 of 30 runs; with threads that stay alive it ran clean 30 of 30.
    """
    script = tmp_path / "close_after_solve.py"
    script.write_text(SCRIPT, encoding="utf-8")
    root = Path(__file__).resolve().parent.parent
    try:
        done = subprocess.run(
            [sys.executable, str(script), "400"], cwd=root, env={**os.environ, "PYTHONPATH": str(root)},
            capture_output=True, text=True, timeout=120,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("The process froze: a thread that used SciPy's HiGHS solver ended. Engine threads must never exit.")
    assert done.returncode == 0, f"the process crashed (exit {done.returncode}): {done.stderr[-800:]}"
    assert "finished" in done.stdout
