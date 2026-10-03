"""Print and assert the section 9 acceptance checks against the freshly built database."""

import re
import sqlite3
from pathlib import Path

from app.engine.diagnosis import diagnose
from app.engine.similar_incidents import find_similar

PLANT_EXPECTED = {
    "ZCU": 62, "ARP": 49, "OPP": 42, "SMX": 42, "OP2": 37, "OP3": 32,
    "BRP": 26, "CRP": 25, "NUP": 24, "BDX": 20, "OPU": 14, "TKX": 7,
}
STATUS_EXPECTED = {
    "RISK CLOSED": 113, "CA/PA EXECUTION": 92, "RCA PROCESS": 71,
    "RISK CANCELED": 47, "MONITORING RESULT": 37, "NEW REGISTERED": 20,
}
OFF_HOURS_EXPECTED = {
    "PU-2101B": 18, "KO-3201": 32, "PM-4405B": 8, "HE-3301": 13, "BL-5702": 14,
}
ALARM_TO_TRIP_EXPECTED = {
    "PU-2101B": 6, "KO-3201": 11, "PM-4405B": 6, "HE-3301": 10, "BL-5702": 15,
}
RCA_LOSS_EXPECTED = {
    "PU-2101B": 226.44, "KO-3201": 1584.00, "PM-4405B": 112.00,
    "HE-3301": 183.60, "BL-5702": 478.80,
}
REPLAY_DATE_STATUS_EXPECTED = {
    "KO-3201": "ALARM", "HE-3301": "ALARM", "BL-5702": "ALARM",
    "PU-2101B": "NORMAL", "PM-4405B": "NORMAL",
}
DQ_IDS_EXPECTED = [f"DQ{i}" for i in range(1, 13)]


class Check:
    def __init__(self, name, passed, detail):
        self.name = name
        self.passed = passed
        self.detail = detail


def _check(results, name, passed, detail):
    results.append(Check(name, passed, detail))


def check_incident_plant_equipment_counts(conn, results):
    total_incidents = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
    total_plants = conn.execute("SELECT COUNT(*) FROM plants").fetchone()[0]
    sensor_equipment = conn.execute("SELECT COUNT(*) FROM equipment WHERE has_sensor_data = 1").fetchone()[0]
    _check(
        results, "380 incidents, 12 plants, 5 equipment with sensor data",
        total_incidents == 380 and total_plants == 12 and sensor_equipment == 5,
        f"incidents={total_incidents}, plants={total_plants}, sensor_equipment={sensor_equipment}",
    )


def check_incidents_per_plant(conn, results):
    rows = dict(conn.execute("SELECT plant_code, COUNT(*) FROM incidents GROUP BY plant_code").fetchall())
    mismatches = {p: (rows.get(p), exp) for p, exp in PLANT_EXPECTED.items() if rows.get(p) != exp}
    _check(
        results, "Incidents per plant matches section 9 table",
        not mismatches,
        "all 12 plants match" if not mismatches else f"mismatches (actual, expected): {mismatches}",
    )


def check_overall_status_counts(conn, results):
    rows = dict(conn.execute("SELECT overall_status, COUNT(*) FROM incidents GROUP BY overall_status").fetchall())
    mismatches = {s: (rows.get(s), exp) for s, exp in STATUS_EXPECTED.items() if rows.get(s) != exp}
    _check(
        results, "Overall Status counts match section 9 table",
        not mismatches,
        "all 6 statuses match" if not mismatches else f"mismatches (actual, expected): {mismatches}",
    )


def check_total_downtime_and_loss(conn, results):
    downtime, loss = conn.execute(
        "SELECT SUM(downtime_hrs), SUM(total_loss_kusd) FROM incidents"
    ).fetchone()
    downtime_ok = abs(downtime - 2261) < 1
    loss_ok = abs(loss - 67194.43) < 50  # "about 67.2 M USD"
    _check(
        results, "Total downtime about 2,261 h; total loss about 67.2 M USD",
        downtime_ok and loss_ok,
        f"downtime={downtime:.1f} h, loss={loss:.2f} k USD ({loss / 1000:.2f} M USD)",
    )


def check_off_hours(conn, results):
    rows = dict(
        conn.execute(
            "SELECT equipment_tag, COUNT(*) FROM sensor_hourly "
            "WHERE signal = 'vibration' AND run_status = 'OFF' GROUP BY equipment_tag"
        ).fetchall()
    )
    mismatches = {t: (rows.get(t), exp) for t, exp in OFF_HOURS_EXPECTED.items() if rows.get(t) != exp}
    _check(
        results, "OFF hours in hourly data match section 9 table",
        not mismatches,
        "all 5 equipment match" if not mismatches else f"mismatches (actual, expected): {mismatches}",
    )


def check_alarm_to_trip_lead_time(conn, results):
    mismatches = {}
    actuals = {}
    for tag, expected_weeks in ALARM_TO_TRIP_EXPECTED.items():
        weeks = conn.execute(
            "SELECT week, health_status FROM health_weekly WHERE equipment_tag = ? ORDER BY week", (tag,)
        ).fetchall()
        first_alarm = next((w for w, s in weeks if s == "ALARM"), None)
        first_trip = next((w for w, s in weeks if s == "TRIP"), None)
        actual_lead = (first_trip - first_alarm) if (first_alarm is not None and first_trip is not None) else None
        actuals[tag] = actual_lead
        if actual_lead != expected_weeks:
            mismatches[tag] = (actual_lead, expected_weeks)
    _check(
        results, "First ALARM to TRIP lead time (weeks) matches section 9 table",
        not mismatches,
        f"actual={actuals}" if mismatches else "all 5 equipment match",
    )


def check_rca_actual_loss(conn, results):
    rows = dict(
        conn.execute("SELECT equipment_tag, estimated_loss_kusd FROM performance_summary").fetchall()
    )
    mismatches = {
        t: (rows.get(t), exp) for t, exp in RCA_LOSS_EXPECTED.items() if rows.get(t) != exp
    }
    total = sum(v for v in rows.values() if v is not None)
    total_ok = abs(total - 2584.84) < 0.1
    _check(
        results, "RCA actual loss (k USD) per equipment matches section 9 (total 2,584.84)",
        not mismatches and total_ok,
        f"total={total:.2f}" if not mismatches else f"mismatches (actual, expected): {mismatches}",
    )


def check_replay_date_status(conn, results):
    mismatches = {}
    for tag, expected_status in REPLAY_DATE_STATUS_EXPECTED.items():
        row = conn.execute(
            "SELECT health_status FROM health_weekly WHERE equipment_tag = ? AND week_date <= '2026-04-08' "
            "ORDER BY week_date DESC LIMIT 1",
            (tag,),
        ).fetchone()
        actual = row[0] if row else None
        if actual != expected_status:
            mismatches[tag] = (actual, expected_status)
    _check(
        results, "On 8 Apr 2026: KO-3201/HE-3301/BL-5702 ALARM, PU-2101B/PM-4405B NORMAL",
        not mismatches,
        "all 5 equipment match" if not mismatches else f"mismatches (actual, expected): {mismatches}",
    )


def check_diagnosis_on_replay_date(conn, results):
    diagnosis = diagnose(conn, "KO-3201", "2026-04-08")
    rule_ok = bool(diagnosis["rule_name"]) and "lube oil water ingress" in diagnosis["rule_name"].lower()
    confidence_ok = diagnosis["confidence"] in ("High", "Medium")

    similar = find_similar(conn, "KO-3201")
    compressor_case = next((s for s in similar if s["eq_type_family"] == "compressor"), None)

    passed = rule_ok and confidence_ok and compressor_case is not None
    detail = (
        f"rule={diagnosis['rule_name']!r}, confidence={diagnosis['confidence']}, "
        f"compressor case in top {len(similar)}: "
        f"{compressor_case['tag_number'] if compressor_case else None}"
    )
    _check(
        results,
        "On 8 Apr 2026 KO-3201 diagnosis returns 'Lube oil water ingress' (High/Medium) "
        "with a compressor bearing case in top similar incidents",
        passed,
        detail,
    )


def check_all_dq_findings_detected(conn, results):
    found = {row[0] for row in conn.execute("SELECT DISTINCT dq_id FROM dq_issues").fetchall()}
    missing = [d for d in DQ_IDS_EXPECTED if d not in found]
    _check(
        results, "All DQ1 to DQ12 findings in section 6 are detected",
        not missing,
        "all 12 present" if not missing else f"missing: {missing}",
    )


def check_no_em_dash(results, root_dir: Path):
    em_dash = "\u2014"
    offenders = []
    targets = [root_dir / "frontend" / "src", root_dir / "backend", root_dir / "README.md"]
    for target in targets:
        if not target.exists():
            continue
        paths = [target] if target.is_file() else list(target.rglob("*"))
        for path in paths:
            if not path.is_file():
                continue
            if path.suffix in (".pyc",) or "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue
            if em_dash in text:
                offenders.append(str(path.relative_to(root_dir)))
    _check(
        results, "No em dash character in frontend/src, backend/, README.md",
        not offenders,
        "clean" if not offenders else f"found in: {offenders}",
    )


def run_acceptance_checks(conn: sqlite3.Connection, root_dir: Path) -> list[Check]:
    results: list[Check] = []
    check_incident_plant_equipment_counts(conn, results)
    check_incidents_per_plant(conn, results)
    check_overall_status_counts(conn, results)
    check_total_downtime_and_loss(conn, results)
    check_off_hours(conn, results)
    check_alarm_to_trip_lead_time(conn, results)
    check_rca_actual_loss(conn, results)
    check_replay_date_status(conn, results)
    check_diagnosis_on_replay_date(conn, results)
    check_all_dq_findings_detected(conn, results)
    check_no_em_dash(results, root_dir)
    return results


def print_report(results: list[Check]) -> bool:
    print()
    print("=" * 78)
    print("ACCEPTANCE CHECKS (SPEC section 9)")
    print("=" * 78)
    all_pass = True
    for r in results:
        if r.passed is None:
            label = "SKIP"
        elif r.passed:
            label = "PASS"
        else:
            label = "FAIL"
            all_pass = False
        print(f"[{label}] {r.name}")
        print(f"       {r.detail}")
    print("=" * 78)
    return all_pass
