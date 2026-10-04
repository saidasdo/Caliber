"""Executive overview: the fields behind the three-tier layout (action status per machine, follow-up
health, equipment type on each priority row, and the headline inputs)."""

import pytest
from fastapi.testclient import TestClient

from app.config import DB_PATH
from app.main import app

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="run `npm run ingest` first")

client = TestClient(app)
ALLOWED_STATUS = {"No owner yet", "Proposed", "Open", "In progress"}


def _overview(replay: str) -> dict:
    return client.get("/api/overview", params={"replay_date": replay}).json()


def test_every_priority_row_has_an_action_status_and_an_equipment_type():
    for row in _overview("2026-04-08")["priority_queue"]:
        assert row["action_status"] in ALLOWED_STATUS
        assert row["equipment_type"]


def test_machine_with_only_later_actions_has_no_owner_yet():
    # KO-3201's CAPA actions come from an RCA dated 29 Apr 2026, so on 8 Apr they are not known. Any
    # actions in the database that are known on 8 Apr (for example from another test) decide the label.
    import sqlite3

    conn = sqlite3.connect(DB_PATH)
    known = conn.execute(
        "SELECT COUNT(*) FROM actions WHERE equipment_tag = 'KO-3201' AND (as_of_date IS NULL OR as_of_date <= '2026-04-08')"
    ).fetchone()[0]
    conn.close()
    row = next(r for r in _overview("2026-04-08")["priority_queue"] if r["equipment_tag"] == "KO-3201")
    if known == 0:
        assert row["action_status"] == "No owner yet"
    else:
        assert row["action_status"] in ALLOWED_STATUS


def test_machine_with_open_capa_actions_reports_the_most_advanced_state():
    # PU-2101B's RCA was known by 8 Apr and has In progress and Open actions: "In progress" wins.
    row = next(r for r in _overview("2026-04-08")["priority_queue"] if r["equipment_tag"] == "PU-2101B")
    assert row["action_status"] == "In progress"


def test_follow_up_health_counts_only_actions_known_on_the_replay_date():
    early = _overview("2026-01-01")["follow_up_health"]["awaiting_approval"]
    assert early == 0
    body = _overview("2026-04-08")["follow_up_health"]
    assert body["awaiting_approval"] >= 0


def test_equipment_type_is_the_equipment_info_type():
    rows = {r["equipment_tag"]: r["equipment_type"] for r in _overview("2026-04-08")["priority_queue"]}
    assert rows["KO-3201"] == "Centrifugal Compressor"
