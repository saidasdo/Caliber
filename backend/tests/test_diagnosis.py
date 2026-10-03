"""Tests for the rule-based diagnosis engine (SPEC section 5.5)."""

import sqlite3

import pytest

from app.config import DB_PATH
from app.engine.diagnosis import RULES, _match_rule, diagnose
from app.engine.replay import REPLAY_PRESETS

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="run `npm run ingest` first")

# Each equipment's dominant_failure_mode (SPEC section 2) maps to exactly one rule.
EXPECTED_RULE_BY_TAG = {
    "PU-2101B": "Seal leakage (pump)",
    "KO-3201": "Lube oil water ingress, bearing distress (compressor)",
    "PM-4405B": "Motor bearing lubrication failure",
    "HE-3301": "Exchanger fouling",
    "BL-5702": "Coupling misalignment",
}


@pytest.fixture
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


@pytest.mark.parametrize("tag,expected_rule", EXPECTED_RULE_BY_TAG.items())
def test_diagnosis_one_week_before_failure_matches_known_failure_mode(conn, tag, expected_rule):
    """SPEC section 4 preset: '1 week before failure' for each equipment."""
    replay_date = REPLAY_PRESETS[tag]
    result = diagnose(conn, tag, replay_date)
    assert result["rule_name"] == expected_rule
    assert result["confidence"] in ("High", "Medium")
    assert result["note"] == "Suggested, needs engineer review"


def test_ko3201_replay_default_date_matches_spec_section_9_example():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    result = diagnose(conn, "KO-3201", "2026-04-08")
    assert "Lube oil water ingress" in result["rule_name"]
    assert result["confidence"] in ("High", "Medium")
    conn.close()


def test_confidence_buckets_match_pass_count(conn):
    for tag in EXPECTED_RULE_BY_TAG:
        result = diagnose(conn, tag, REPLAY_PRESETS[tag])
        passes = result["passes"]
        expected = {4: "High", 3: "Medium", 2: "Low"}.get(passes)
        assert result["confidence"] == expected


def test_first_week_has_no_trend_history_so_no_confident_diagnosis(conn):
    # Week 1 (2025-10-23, PU-2101B's very first weekly reading): the trend check needs at
    # least two weekly points, so nothing can pass yet regardless of the raw values.
    result = diagnose(conn, "PU-2101B", "2025-10-23")
    assert result["confidence"] is None
    assert result["passes"] == 0


def test_confidence_builds_up_over_the_weeks_before_trip(conn):
    # Not monotonic week-to-week in general, but the arc from week 1 to the TRIP week should
    # go from nothing to a confident match as the 4-week trend develops.
    early = diagnose(conn, "PU-2101B", "2025-10-23")
    mid = diagnose(conn, "PU-2101B", "2025-11-15")
    late = diagnose(conn, "PU-2101B", "2026-03-05")  # 1 week before the 2026-03-12 trip
    assert early["passes"] < mid["passes"] < late["passes"]


def test_every_condition_row_has_pass_fail_and_parameter_shown():
    """SPEC 5.5: 'Show every condition as a row: parameter, value, limit, trend, pass/fail.'"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    result = diagnose(conn, "KO-3201", "2026-04-08")
    assert len(result["conditions"]) == 4
    for row in result["conditions"]:
        assert "parameter" in row
        assert "value" in row
        assert "limit" in row
        assert "trend" in row
        assert "pass" in row
    conn.close()


def test_rule_matching_is_keyed_on_parameter_names_not_tag_names():
    """SPEC 5.5: rules must work for other equipment of the same type, i.e. they must not be
    keyed on the tag. Feed a synthetic parameter list with no real tag involved."""
    synthetic_params = [
        "Seal Flush Flow (L/min)",
        "Overall Vibration (mm/s)",
        "Bearing Temp (C)",
        "Discharge Pressure (barg)",
    ]
    rule = _match_rule(synthetic_params)
    assert rule is not None
    assert rule["name"] == "Seal leakage (pump)"


def test_rule_matching_requires_at_least_two_keyword_matches():
    # A parameter list matching only one rule keyword should not produce a confident match.
    rule = _match_rule(["Some Unrelated Parameter (unit)"])
    assert rule is None


def test_all_five_rules_have_four_conditions():
    for rule in RULES:
        assert len(rule["conditions"]) == 4
