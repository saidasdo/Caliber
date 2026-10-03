"""Tests for similar-incidents scoring (SPEC section 5.6)."""

import sqlite3

import pytest

from app.config import DB_PATH
from app.engine.similar_incidents import find_similar

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="run `npm run ingest` first")


@pytest.fixture
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


@pytest.mark.parametrize("tag", ["PU-2101B", "KO-3201", "PM-4405B", "HE-3301", "BL-5702"])
def test_returns_at_most_five_sorted_descending(conn, tag):
    results = find_similar(conn, tag)
    assert len(results) <= 5
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.parametrize("tag", ["PU-2101B", "KO-3201", "PM-4405B", "HE-3301", "BL-5702"])
def test_score_matches_declared_breakdown(conn, tag):
    for row in find_similar(conn, tag):
        assert row["score"] == sum(row["score_breakdown"].values())
        # only these five weighted factors exist (SPEC 5.6)
        assert set(row["score_breakdown"].keys()) <= {
            "eq_type_family", "component_family", "mechanism_norm", "plant_code", "discipline",
        }
        assert row["score_breakdown"].get("eq_type_family", 0) in (0, 3)
        assert row["score_breakdown"].get("component_family", 0) in (0, 3)
        assert row["score_breakdown"].get("mechanism_norm", 0) in (0, 2)
        assert row["score_breakdown"].get("plant_code", 0) in (0, 1)
        assert row["score_breakdown"].get("discipline", 0) in (0, 1)


def test_excludes_the_anchor_equipments_own_incident(conn):
    results = find_similar(conn, "KO-3201")
    assert all(r["tag_number"] != "KO-3201" for r in results)


def test_ko3201_top_similar_includes_a_compressor_bearing_case():
    """SPEC section 9: top similar incidents for KO-3201 must include a compressor case."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    results = find_similar(conn, "KO-3201")
    assert any(r["eq_type_family"] == "compressor" for r in results)
    conn.close()


def test_dq9_flag_set_only_for_tube_bundle_on_non_heat_exchanger(conn):
    for tag in ["PU-2101B", "KO-3201", "PM-4405B", "HE-3301", "BL-5702"]:
        for row in find_similar(conn, tag):
            expected = row["component"] == "Tube Bundle" and row["eq_type_family"] != "heat_exchanger"
            assert row["dq9_flag"] == expected


def test_unknown_tag_returns_empty_list(conn):
    assert find_similar(conn, "NOT-A-REAL-TAG") == []


def test_max_possible_score_is_ten(conn):
    # +3 +3 +2 +1 +1 (SPEC 5.6), never exceeded.
    for tag in ["PU-2101B", "KO-3201", "PM-4405B", "HE-3301", "BL-5702"]:
        for row in find_similar(conn, tag):
            assert row["score"] <= 10
