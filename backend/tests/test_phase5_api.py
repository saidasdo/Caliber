"""Phase 5 API additions: hourly anomaly markers, and the diagnosis presets story."""

import pytest
from fastapi.testclient import TestClient

from app.config import DB_PATH
from app.engine.replay import REPLAY_PRESETS
from app.main import app

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="run `npm run ingest` first")

client = TestClient(app)

EXPECTED_RULE_BY_TAG = {
    "PU-2101B": "Seal leakage (pump)",
    "KO-3201": "Lube oil water ingress, bearing distress (compressor)",
    "PM-4405B": "Motor bearing lubrication failure",
    "HE-3301": "Exchanger fouling",
    "BL-5702": "Coupling misalignment",
}


def test_anomalies_endpoint_returns_a_list():
    r = client.get("/api/equipment/KO-3201/anomalies", params={"signal": "vibration"})
    assert r.status_code == 200
    body = r.json()
    assert body["signal"] == "vibration"
    assert isinstance(body["anomalies"], list)
    for a in body["anomalies"]:
        assert "start_ts" in a and "end_ts" in a and "peak_value" in a and "baseline_mean" in a


def test_anomalies_unknown_tag_is_404():
    r = client.get("/api/equipment/NOT-A-TAG/anomalies", params={"signal": "vibration"})
    assert r.status_code == 404


@pytest.mark.parametrize("tag,expected_rule", EXPECTED_RULE_BY_TAG.items())
def test_diagnosis_endpoint_one_week_before_failure(tag, expected_rule):
    """Direct answer to: diagnosis output for all 5 equipment, one week before failure."""
    replay_date = REPLAY_PRESETS[tag]
    r = client.get(f"/api/equipment/{tag}/diagnosis", params={"replay_date": replay_date})
    assert r.status_code == 200
    body = r.json()
    assert body["rule_name"] == expected_rule
    assert body["confidence"] == "High"
    assert body["passes"] == body["of"] == 4


def test_priority_queue_top_pick_is_explainable_via_breakdown():
    r = client.get("/api/overview", params={"replay_date": "2026-04-08"})
    top = r.json()["priority_queue"][0]
    assert top["equipment_tag"] == "KO-3201"
    b = top["breakdown"]
    assert round(0.4 * b["severity"] + 0.3 * b["class_score"] + 0.3 * b["loss_exposure"], 4) == top["priority_score"]
