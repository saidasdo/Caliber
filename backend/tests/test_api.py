"""API smoke tests for phase 2. Run `npm run ingest` first to build db/plantpulse.sqlite."""

import pytest
from fastapi.testclient import TestClient

from app.config import DB_PATH
from app.main import app

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="run `npm run ingest` first")

client = TestClient(app)


def backend_failure_date(tag: str) -> str:
    import sqlite3

    from app.config import DB_PATH

    conn = sqlite3.connect(DB_PATH)
    try:
        return conn.execute("SELECT failure_date FROM equipment WHERE tag = ?", (tag,)).fetchone()[0]
    finally:
        conn.close()

REPLAY_DATE = "2026-04-08"


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_overview_replay_date_matches_spec_example():
    r = client.get("/api/overview", params={"replay_date": REPLAY_DATE})
    assert r.status_code == 200
    body = r.json()
    status_by_tag = {row["equipment_tag"]: row["health_status"] for row in body["priority_queue"]}
    assert status_by_tag == {
        "KO-3201": "ALARM",
        "HE-3301": "ALARM",
        "BL-5702": "ALARM",
        "PU-2101B": "NORMAL",
        "PM-4405B": "NORMAL",
    }
    # KO-3201 is first on 8 Apr: it has the lowest margin with all four parameters past alarm.
    assert body["priority_queue"][0]["equipment_tag"] == "KO-3201"
    assert len(body["loss_by_plant"]) == 12


def test_overview_default_replay_date_works_without_query_param():
    r = client.get("/api/overview")
    assert r.status_code == 200


@pytest.mark.parametrize("tag", ["PU-2101B", "KO-3201", "PM-4405B", "HE-3301", "BL-5702"])
def test_equipment_detail_for_all_five(tag):
    r = client.get(f"/api/equipment/{tag}", params={"replay_date": REPLAY_DATE})
    assert r.status_code == 200
    body = r.json()
    assert body["tag"] == tag
    assert body["weekly_state"] is not None
    # Replay rule: the RCA panel is shown only once the failure date is on or before the replay date.
    failure_date = backend_failure_date(tag)
    if failure_date <= REPLAY_DATE:
        assert body["linked_rca"]["root_cause"]
    else:
        assert body["linked_rca"] is None


def test_equipment_unknown_tag_is_404():
    r = client.get("/api/equipment/NOT-A-TAG")
    assert r.status_code == 404


def test_ko3201_diagnosis_matches_spec_section_9_example():
    r = client.get("/api/equipment/KO-3201/diagnosis", params={"replay_date": REPLAY_DATE})
    assert r.status_code == 200
    body = r.json()
    assert "Lube oil water ingress" in body["rule_name"]
    assert body["confidence"] in ("High", "Medium")
    assert all(c["pass"] for c in body["conditions"]) or body["passes"] >= 2


def test_ko3201_similar_incidents_include_a_compressor_case():
    r = client.get("/api/equipment/KO-3201/similar-incidents")
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 5
    assert any(row["eq_type_family"] == "compressor" for row in results)


def test_equipment_series_returns_points():
    r = client.get(
        "/api/equipment/KO-3201/series",
        params={"signal": "vibration", "start": "2026-04-07T00:00:00", "end": "2026-04-08T23:00:00"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["signal"] == "vibration"
    assert len(body["points"]) == 48  # 2 days x 24 hours


def test_equipment_series_unknown_signal_is_404():
    r = client.get("/api/equipment/KO-3201/series", params={"signal": "not_a_signal"})
    assert r.status_code == 404


def test_plant_detail():
    r = client.get("/api/plants/ZCU", params={"replay_date": REPLAY_DATE})
    assert r.status_code == 200
    body = r.json()
    assert body["plant_code"] == "ZCU"
    assert body["kpis"]["incident_count"] > 0


def test_plant_unknown_code_is_404():
    r = client.get("/api/plants/XXX")
    assert r.status_code == 404


def test_backtest_lead_times_match_spec_section_9():
    r = client.get("/api/backtest")
    assert r.status_code == 200
    lead_weeks = {row["equipment_tag"]: row["lead_time_weeks"] for row in r.json()["results"]}
    assert lead_weeks == {
        "PU-2101B": 6, "KO-3201": 11, "PM-4405B": 6, "HE-3301": 10, "BL-5702": 15,
    }


def test_data_quality_has_all_twelve_dq_ids():
    r = client.get("/api/data-quality")
    assert r.status_code == 200
    body = r.json()
    assert set(body["by_dq_id"].keys()) == {f"DQ{i}" for i in range(1, 13)}
    assert 0 <= body["score"] <= 100


def test_kpi_dictionary_is_seeded():
    r = client.get("/api/kpi-dictionary")
    assert r.status_code == 200
    names = {row["kpi_name"] for row in r.json()["results"]}
    assert "Availability" in names
    assert "Data quality score" in names


def test_actions_endpoint_returns_preloaded_capa_actions():
    # Populated in phase 6 (see tests/test_actions_phase6.py for full coverage); this just
    # keeps the phase 2 smoke test accurate now that the endpoint has real data.
    # Full record: a replay date after every RCA failure date shows all preloaded CAPA actions.
    r = client.get("/api/actions", params={"replay_date": "2099-12-31"})
    assert r.status_code == 200
    assert len(r.json()["results"]) >= 47


def test_replay_presets_cover_all_five_equipment():
    r = client.get("/api/replay")
    assert r.status_code == 200
    tags = {p["equipment_tag"] for p in r.json()["presets"]}
    assert tags == {"PU-2101B", "KO-3201", "PM-4405B", "HE-3301", "BL-5702"}
