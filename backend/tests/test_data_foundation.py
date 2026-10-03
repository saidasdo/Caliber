"""Tests for phase 8: source map, KPI dictionary, data quality page, process flags."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.config import DB_PATH
from app.main import app

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="run `npm run ingest` first")

client = TestClient(app)


@pytest.fixture
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Source map
# ---------------------------------------------------------------------------


def test_source_map_has_entries_for_every_raw_source():
    r = client.get("/api/source-map")
    assert r.status_code == 200
    body = r.json()
    files = {e["source_file"] for e in body["entries"]}
    assert any("Production Data" in f for f in files)
    assert any("Equipment Performance" in f for f in files)
    assert any("Incident Database" in f for f in files)
    assert any(".pptx" in f for f in files)


def test_source_map_every_entry_states_what_it_feeds():
    r = client.get("/api/source-map")
    for entry in r.json()["entries"]:
        assert entry["feeds"], f"{entry['source_file']}/{entry['sheet']} has no 'feeds' list"


def test_source_map_join_keys_reference_real_columns():
    r = client.get("/api/source-map")
    keys = {k["key"] for k in r.json()["join_keys"]}
    assert {"Tag Number / Equipment Tag", "AR No.", "Serial No"} <= keys


# ---------------------------------------------------------------------------
# KPI dictionary (built in phase 1; re-checked here as part of the Data page)
# ---------------------------------------------------------------------------


def test_kpi_dictionary_covers_every_kpi_named_in_spec_5_9():
    required = {
        "Availability", "MTBF", "MTTR", "Downtime", "Production loss (t)", "Loss (USD)",
        "Health status", "Alarm lead time", "Open incidents", "CAPA overdue rate",
        "Data quality score", "Energy proxy",
    }
    r = client.get("/api/kpi-dictionary")
    names = {row["kpi_name"] for row in r.json()["results"]}
    assert required <= names


def test_kpi_dictionary_rows_have_all_required_fields():
    r = client.get("/api/kpi-dictionary")
    for row in r.json()["results"]:
        assert row["definition"]
        assert row["formula"]
        assert row["source"]
        assert row["refresh_frequency"]
        assert row["owner"]


# ---------------------------------------------------------------------------
# Data quality: all DQ1-DQ12 + not-errors
# ---------------------------------------------------------------------------


def test_data_quality_detects_all_twelve_checks():
    r = client.get("/api/data-quality")
    assert r.status_code == 200
    body = r.json()
    assert set(body["by_dq_id"].keys()) == {f"DQ{i}" for i in range(1, 13)}


def test_data_quality_score_between_0_and_100():
    r = client.get("/api/data-quality")
    assert 0 <= r.json()["score"] <= 100


def test_data_quality_includes_five_not_error_notes():
    r = client.get("/api/data-quality")
    assert len(r.json()["not_errors"]) == 5


def test_assumptions_endpoint_filters_by_area():
    r = client.get("/api/assumptions", params={"area": "not_error"})
    assert len(r.json()["results"]) == 5
    r_all = client.get("/api/assumptions")
    assert len(r_all.json()["results"]) >= 9


# ---------------------------------------------------------------------------
# Process flags (SPEC section 6)
# ---------------------------------------------------------------------------


def test_process_flags_match_spec_example_at_end_of_dataset():
    r = client.get("/api/process-flags", params={"replay_date": "2026-07-31"})
    assert r.status_code == 200
    body = r.json()
    assert body["rca_process_overdue"]["count"] == 69
    assert body["rca_process_overdue"]["of_total"] == 71
    assert body["new_registered_stale"]["oldest_date"] == "2024-01-15"
    assert body["incidents_without_ar_no"]["count"] == 226
    assert body["incidents_without_ar_no"]["of_total"] == 380


def test_process_flags_shrink_as_of_an_earlier_replay_date():
    early = client.get("/api/process-flags", params={"replay_date": "2024-06-01"}).json()
    late = client.get("/api/process-flags", params={"replay_date": "2026-07-31"}).json()
    assert early["incidents_without_ar_no"]["of_total"] < late["incidents_without_ar_no"]["of_total"]
    assert early["rca_process_overdue"]["of_total"] <= late["rca_process_overdue"]["of_total"]


def test_process_flags_computed_not_hardcoded(conn):
    # Recompute rca_process_overdue independently from raw rows and compare.
    replay_date = "2026-07-31"
    expected = conn.execute(
        "SELECT COUNT(*) FROM incidents WHERE overall_status = 'RCA PROCESS' "
        "AND date_of_occur <= ? AND rca_due_date IS NOT NULL AND rca_due_date < ?",
        (replay_date, replay_date),
    ).fetchone()[0]
    r = client.get("/api/process-flags", params={"replay_date": replay_date})
    assert r.json()["rca_process_overdue"]["count"] == expected
