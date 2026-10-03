"""Unit tests for hourly anomaly detection (SPEC section 5.5) against a synthetic in-memory
DB, so the baseline/deviation/consecutive-hour rules can be checked precisely, independent of
the real dataset's actual values."""

import sqlite3
from datetime import datetime, timedelta

import pytest

from app.engine.anomaly import detect_anomalies


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute(
        "CREATE TABLE sensor_hourly (equipment_tag TEXT, ts TEXT, signal TEXT, value REAL, run_status TEXT)"
    )
    return c


def _insert(conn, tag, signal, start, values_and_status):
    rows = []
    for i, (value, status) in enumerate(values_and_status):
        ts = (start + timedelta(hours=i)).strftime("%Y-%m-%d %H:%M:%S")
        rows.append((tag, ts, signal, value, status))
    conn.executemany(
        "INSERT INTO sensor_hourly (equipment_tag, ts, signal, value, run_status) VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()


BASE_START = datetime(2026, 1, 1, 0, 0, 0)


def test_no_anomaly_in_flat_baseline(conn):
    # 30 days of constant ON values: no spike anywhere, nothing should be flagged.
    values = [(100.0, "ON")] * (30 * 24)
    _insert(conn, "EQ1", "vibration", BASE_START, values)
    assert detect_anomalies(conn, "EQ1", "vibration") == []


def test_sustained_spike_after_baseline_is_detected(conn):
    # 7-day baseline at 100 +/- noise, then a sustained jump to 300 for 10 hours (well beyond
    # 3 sigma of the baseline's tiny spread, held for more than the 3-hour minimum).
    baseline = [(100.0 + (i % 2) * 0.1, "ON") for i in range(7 * 24)]
    spike = [(300.0, "ON")] * 10
    tail = [(100.0, "ON")] * (24 * 3)
    _insert(conn, "EQ1", "vibration", BASE_START, baseline + spike + tail)

    anomalies = detect_anomalies(conn, "EQ1", "vibration")
    assert len(anomalies) == 1
    assert anomalies[0]["peak_value"] == 300.0
    assert abs(anomalies[0]["baseline_mean"] - 100.05) < 0.1


def test_brief_mild_bump_within_baseline_noise_is_not_flagged(conn):
    # A baseline with real spread (std ~4), then a single-hour bump that a 24h rolling mean
    # dilutes to well under 3 sigma: normal noise, not a real event.
    noisy = [95.0, 105.0, 98.0, 102.0, 97.0, 103.0, 99.0, 101.0]
    baseline = [(noisy[i % len(noisy)], "ON") for i in range(7 * 24)]
    mild_bump = [(112.0, "ON")]
    tail = [(noisy[i % len(noisy)], "ON") for i in range(24 * 2)]
    _insert(conn, "EQ1", "vibration", BASE_START, baseline + mild_bump + tail)

    assert detect_anomalies(conn, "EQ1", "vibration") == []


def test_off_hours_are_ignored_not_treated_as_zero(conn):
    # A long OFF stretch reading 0 would look like a huge deviation if it were included;
    # SPEC section 5.5 says to ignore OFF hours entirely, and section 4 bans showing zeros
    # for missing/inapplicable data.
    baseline = [(100.0, "ON") for _ in range(7 * 24)]
    off_stretch = [(0.0, "OFF")] * 20
    tail = [(100.0, "ON")] * (24 * 2)
    _insert(conn, "EQ1", "vibration", BASE_START, baseline + off_stretch + tail)

    assert detect_anomalies(conn, "EQ1", "vibration") == []


def test_baseline_uses_only_first_seven_days(conn):
    # A later, unrelated sustained shift (after day 7) must not distort the baseline used to
    # judge it: baseline should stay ~100, so the day-10 shift to 130 is still flagged.
    baseline = [(100.0, "ON") for _ in range(7 * 24)]
    normal_gap = [(100.0, "ON")] * (2 * 24)
    later_shift = [(130.0, "ON")] * 10
    tail = [(100.0, "ON")] * 24
    _insert(conn, "EQ1", "vibration", BASE_START, baseline + normal_gap + later_shift + tail)

    anomalies = detect_anomalies(conn, "EQ1", "vibration")
    assert len(anomalies) == 1
    assert abs(anomalies[0]["baseline_mean"] - 100.0) < 0.01


def test_short_series_returns_no_anomalies(conn):
    _insert(conn, "EQ1", "vibration", BASE_START, [(100.0, "ON")] * 10)
    assert detect_anomalies(conn, "EQ1", "vibration") == []
