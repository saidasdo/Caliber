"""Phase 4 additions: gauges, status timeline, weekly series."""

import pytest
from fastapi.testclient import TestClient

from app.config import DB_PATH
from app.main import app

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="run `npm run ingest` first")

client = TestClient(app)

ALL_TAGS = ["PU-2101B", "KO-3201", "PM-4405B", "HE-3301", "BL-5702"]


@pytest.mark.parametrize("tag", ALL_TAGS)
def test_gauges_present_and_bounded(tag):
    r = client.get(f"/api/equipment/{tag}", params={"replay_date": "2026-04-08"})
    assert r.status_code == 200
    gauges = r.json()["gauges"]
    for name in ("availability", "health_margin", "production_vs_normal"):
        assert name in gauges
        g = gauges[name]
        assert "value" in g and "previous" in g and "sparkline" in g and "data_available" in g

    avail = gauges["availability"]
    if avail["data_available"]:
        assert 0 <= avail["value"] <= 100

    health = gauges["health_margin"]
    assert health["data_available"] is True  # weekly data always exists, no hourly gate
    assert health["worst_parameter"] is not None


def test_ko3201_health_margin_worst_parameter_matches_narrowest_trip_distance():
    r = client.get("/api/equipment/KO-3201", params={"replay_date": "2026-04-08"})
    gauges = r.json()["gauges"]
    # At this replay date KO-3201's bearing metal temp is proportionally closer to its trip
    # limit than the other three monitored parameters (see the diagnosis test in test_api.py
    # for the alarm-based ranking, which differs from this trip-based one by design).
    assert gauges["health_margin"]["worst_parameter"] == "Bearing Metal Temp"
    assert gauges["health_margin"]["value"] < 20


@pytest.mark.parametrize("tag", ALL_TAGS)
def test_status_timeline_covers_the_full_hourly_window(tag):
    r = client.get(f"/api/equipment/{tag}/status-timeline")
    assert r.status_code == 200
    body = r.json()
    total_hours = sum(d["duration_hours"] for d in body["distribution"])
    assert total_hours == 720  # 30 days x 24h, per SPEC section 2
    # segments are contiguous and cover the window with no gaps
    assert sum(s["hours"] for s in body["segments"]) == 720


@pytest.mark.parametrize("tag", ALL_TAGS)
def test_status_timeline_off_hours_match_acceptance_numbers(tag):
    expected_off = {
        "PU-2101B": 18, "KO-3201": 32, "PM-4405B": 8, "HE-3301": 13, "BL-5702": 14,
    }
    r = client.get(f"/api/equipment/{tag}/status-timeline")
    dist = {d["lane"]: d["duration_hours"] for d in r.json()["distribution"]}
    assert dist["trip_off"] == expected_off[tag]


@pytest.mark.parametrize("tag", ALL_TAGS)
def test_weekly_series_has_four_parameters_26_weeks_each(tag):
    r = client.get(f"/api/equipment/{tag}/weekly-series")
    assert r.status_code == 200
    parameters = r.json()["parameters"]
    assert len(parameters) == 4
    for p in parameters:
        assert len(p["points"]) == 26
        assert p["alarm"] is not None
        assert p["trip"] is not None


def test_status_timeline_unknown_tag_is_404():
    r = client.get("/api/equipment/NOT-A-TAG/status-timeline")
    assert r.status_code == 404


def test_plant_equipment_rows_include_worst_parameter():
    r = client.get("/api/plants/ZCU", params={"replay_date": "2026-04-08"})
    assert r.status_code == 200
    equipment = r.json()["equipment"]
    assert len(equipment) == 2  # KO-3201, HE-3301
    for row in equipment:
        assert "worst_parameter" in row
