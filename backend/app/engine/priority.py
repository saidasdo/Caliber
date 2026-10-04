"""Alert priority (SPEC section 5.4, revised): one urgency score that is both the rank and the number
shown.

urgency = 0.6 * proximity + 0.4 * alarm_share, where
- proximity   = clip(1 - worst_health_margin_pct / 100, 0, 1), replay-safe, baseline-relative
- alarm_share = parameters past their alarm limit / parameters monitored
- TRIP = 1.0 (the machine has tripped; no other floor applies)

Rank: by urgency, descending. Ties only: Criticality (High > Medium > Low), then estimated impact.
Labels come from urgency and status alone: Critical if urgency >= 0.7 or TRIP; High if >= 0.5;
Medium if >= 0.25 or status ALARM; otherwise Normal. Class and loss never change a label.

Thresholds and weights are an assumption pending product feedback (SPEC does not define them).
"""

import math
import sqlite3

from app.engine.diagnosis import diagnose
from app.engine.gauges import health_margin
from app.engine.impact import estimate_impact
from app.engine.replay import resolve_week

W_PROXIMITY = 0.6
W_SHARE = 0.4

CRITICAL_URGENCY = 0.7
HIGH_URGENCY = 0.5
MEDIUM_URGENCY = 0.25

CRITICALITY_RANK = {"High": 3, "Medium": 2, "Low": 1}


def _label(urgency: float, status: str | None) -> str:
    if status == "TRIP" or urgency >= CRITICAL_URGENCY:
        return "Critical"
    if urgency >= HIGH_URGENCY:
        return "High"
    if urgency >= MEDIUM_URGENCY or status == "ALARM":
        return "Medium"
    return "Normal"


def _weeks_in_current_status(conn: sqlite3.Connection, tag: str, replay_date: str) -> int | None:
    """Consecutive weeks (counting back from the replay date) the equipment has held its
    current health_status, for the plant manager alert wording ('in ALARM for 8 weeks')."""
    rows = conn.execute(
        "SELECT health_status FROM health_weekly WHERE equipment_tag = ? AND week_date <= ? "
        "ORDER BY week_date DESC",
        (tag, replay_date),
    ).fetchall()
    if not rows:
        return None
    current = rows[0][0]
    count = 0
    for (status,) in rows:
        if status != current:
            break
        count += 1
    return count


def _past_alarm(parameter: dict) -> bool:
    """A parameter is past its alarm limit when its value is on the alarm-or-worse side."""
    if parameter["alarm"] is None or parameter["value"] is None:
        return False
    if parameter["direction"] == "higher_is_worse":
        return parameter["value"] >= parameter["alarm"]
    return parameter["value"] <= parameter["alarm"]


def _urgency(week_state: dict | None, margin_pct: float | None) -> dict:
    """urgency = 0.6 x proximity + 0.4 x alarm share; TRIP is 1.0. Returns the terms as well."""
    if week_state is None:
        return {"urgency": 0.0, "proximity": 0.0, "alarm_share": 0.0, "past_alarm": 0, "total": 0}
    params = week_state["parameters"]
    past = sum(1 for p in params if _past_alarm(p))
    total = len(params)
    share = past / total if total else 0.0
    proximity = 0.0 if margin_pct is None else min(1.0, max(0.0, 1 - margin_pct / 100))
    urgency = 1.0 if week_state["health_status"] == "TRIP" else W_PROXIMITY * proximity + W_SHARE * share
    return {"urgency": urgency, "proximity": proximity, "alarm_share": share, "past_alarm": past, "total": total}


def _log_exposure(values: dict[str, float | None]) -> dict[str, float]:
    """Log-scale min-max of the estimated impact across the equipment: 0 for the smallest, 1 for the
    largest. Shown in the breakdown; it is a tie-break, not part of the urgency."""
    logs = {tag: math.log(v) for tag, v in values.items() if v is not None and v > 0}
    if not logs:
        return {tag: 0.0 for tag in values}
    lo, hi = min(logs.values()), max(logs.values())
    span = (hi - lo) or 1.0
    return {tag: (logs[tag] - lo) / span if tag in logs else 0.0 for tag in values}


def _rank_key(row: dict) -> tuple:
    """Urgency, then Criticality, then estimated impact. Only urgency is the displayed number; the other
    two only separate machines with exactly the same urgency."""
    return (
        row["priority_score"],
        CRITICALITY_RANK.get(row["breakdown"]["criticality"], 0),
        row["estimated_impact"]["value_kusd"] or 0.0,
    )


def compute_priority(conn: sqlite3.Connection, replay_date: str) -> list[dict]:
    equipment = conn.execute(
        "SELECT tag, name, plant_code, eq_class, criticality, eq_type FROM equipment WHERE has_sensor_data = 1"
    ).fetchall()

    impact_by_tag = {tag: estimate_impact(conn, tag, replay_date) for tag, *_ in equipment}
    exposure = _log_exposure({tag: i["value_kusd"] for tag, i in impact_by_tag.items()})

    results = []
    for tag, name, plant_code, eq_class, criticality, eq_type in equipment:
        week_state = resolve_week(conn, tag, replay_date)
        margin = health_margin(conn, tag, replay_date)["value"]
        terms = _urgency(week_state, margin)
        impact = impact_by_tag[tag]
        diagnosis = diagnose(conn, tag, replay_date)
        status = week_state["health_status"] if week_state else None
        urgency = round(terms["urgency"], 4)

        worst_parameter = None
        if week_state and week_state["parameters"]:
            worst_parameter = max(
                week_state["parameters"],
                key=lambda p: (
                    (p["value"] - p["alarm"]) if p["direction"] == "higher_is_worse" and p["alarm"] is not None
                    else (p["alarm"] - p["value"]) if p["direction"] == "lower_is_worse" and p["alarm"] is not None
                    else float("-inf")
                ),
            )

        results.append(
            {
                "equipment_tag": tag,
                "equipment_name": name,
                "equipment_type": eq_type,
                "plant_code": plant_code,
                # The displayed number and the rank are the same value.
                "priority_score": urgency,
                "priority_label": _label(terms["urgency"], status),
                "breakdown": {
                    "urgency": urgency,
                    # Kept for existing readers: the urgency is the severity the card shows.
                    "severity": urgency,
                    "proximity": round(terms["proximity"], 4),
                    "alarm_share": round(terms["alarm_share"], 4),
                    "parameters_past_alarm": terms["past_alarm"],
                    "parameters_total": terms["total"],
                    "health_margin_pct": margin,
                    "criticality": criticality,
                    "loss_exposure": round(exposure[tag], 4),
                    "loss_exposure_raw_kusd": impact["value_kusd"],
                },
                "health_status": status,
                "weeks_in_status": _weeks_in_current_status(conn, tag, replay_date),
                "estimated_impact": impact,
                "diagnosis_rule_name": diagnosis["rule_name"],
                "diagnosis_confidence": diagnosis["confidence"],
                "worst_parameter": (
                    {
                        "parameter": worst_parameter["parameter"],
                        "value": worst_parameter["value"],
                        "unit": worst_parameter["unit"],
                        "alarm": worst_parameter["alarm"],
                        "trip": worst_parameter["trip"],
                        "direction": worst_parameter["direction"],
                    }
                    if worst_parameter
                    else None
                ),
                "reason": (
                    f"{tag}: {status or 'no data'}"
                    + (
                        f", {worst_parameter['parameter']} {worst_parameter['value']} "
                        f"vs alarm {worst_parameter['alarm']}"
                        if worst_parameter and worst_parameter["alarm"] is not None
                        else ""
                    )
                ),
            }
        )

    results.sort(key=_rank_key, reverse=True)
    for rank, row in enumerate(results, 1):
        row["rank"] = rank
    return results
