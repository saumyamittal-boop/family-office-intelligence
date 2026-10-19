"""The engine runs on one dedicated thread, and a slow or stuck analysis can never hang a request."""
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

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
    time.sleep(1.8)  # let the slow job finish; its answer lands in the cache
    assert c.get(f"/api/profiles/{pid}/analysis").status_code == 200  # the service recovered by itself


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


def test_the_service_shuts_its_engine_thread_down_with_the_app(make_client):
    c = make_client()
    thread = next(t for t in __import__("threading").enumerate() if t.name == "engine")
    assert thread.daemon  # a stuck solve can never keep the server from exiting
