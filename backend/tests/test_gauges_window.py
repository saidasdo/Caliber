"""Regression tests: hourly-derived gauges must not show stale in-window values once the
replay date has moved outside an equipment's own hourly window (SPEC section 4)."""

import pytest
from fastapi.testclient import TestClient

from app.config import DB_PATH
from app.main import app

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="run `npm run ingest` first")

client = TestClient(app)


def test_hourly_gauges_unavailable_outside_own_window():
    # PU-2101B's hourly window is March 2026; 2026-04-08 is outside it (it belongs to
    # KO-3201/HE-3301/BL-5702's active period).
    r = client.get("/api/equipment/PU-2101B", params={"replay_date": "2026-04-08"})
    gauges = r.json()["gauges"]
    assert gauges["availability"]["data_available"] is False
    assert gauges["availability"]["value"] is None
    assert gauges["production_vs_normal"]["data_available"] is False
    assert gauges["production_vs_normal"]["value"] is None


def test_health_margin_gauge_stays_available_outside_hourly_window():
    # Health margin is weekly-data-derived, not hourly, so it must still populate even when
    # the equipment has no hourly coverage for this replay date.
    r = client.get("/api/equipment/PU-2101B", params={"replay_date": "2026-04-08"})
    health = r.json()["gauges"]["health_margin"]
    assert health["data_available"] is True
    assert health["value"] is not None


def test_hourly_gauges_available_inside_own_window():
    r = client.get("/api/equipment/PU-2101B", params={"replay_date": "2026-03-15"})
    gauges = r.json()["gauges"]
    assert gauges["availability"]["data_available"] is True
    assert gauges["production_vs_normal"]["data_available"] is True


@pytest.mark.parametrize("_", range(10))
def test_repeated_requests_do_not_hit_sqlite_thread_errors(_):
    # Regression for "SQLite objects created in a thread can only be used in that same
    # thread": under the real threadpool (unlike TestClient's default execution), a
    # connection opened with check_same_thread=True intermittently failed. Repeat the call
    # enough times to catch a reintroduced regression with reasonable confidence.
    r = client.get("/api/equipment/KO-3201", params={"replay_date": "2026-04-08"})
    assert r.status_code == 200
    assert r.json()["gauges"]["availability"]["data_available"] is True
