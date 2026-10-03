"""Rule-based diagnosis engine (SPEC section 5.5).

Rules are keyed on parameter-name keywords found in an equipment's weekly parameters, not on
tag names, so the same rule set applies to any other equipment with a matching parameter set.
"""

import sqlite3

from app.engine.replay import resolve_week

# Each rule: name, and a list of (keyword, check) where check is "level_worse", "rising" or
# "falling". "level_worse" means the current value is on the alarm-or-worse side of the alarm
# limit (direction-aware); "rising"/"falling" checks the 4-week trend slope.
RULES = [
    {
        "name": "Seal leakage (pump)",
        "conditions": [
            ("seal flush flow", "falling"),
            ("vibration", "rising"),
            ("bearing temp", "rising"),
            ("discharge pressure", "falling"),
        ],
    },
    {
        "name": "Lube oil water ingress, bearing distress (compressor)",
        "conditions": [
            ("water content", "level_worse"),
            ("supply press", "falling"),
            ("radial vibration", "rising"),
            ("bearing metal temp", "rising"),
        ],
    },
    {
        "name": "Motor bearing lubrication failure",
        "conditions": [
            ("de bearing temp", "level_worse"),
            ("motor vibration", "rising"),
            ("ampere", "rising"),
            ("winding temp", "rising"),
        ],
    },
    {
        "name": "Exchanger fouling",
        "conditions": [
            ("tube-side dp", "level_worse"),
            ("heat duty", "level_worse"),
            ("cold outlet temp", "falling"),
            ("feed heavy-ends", "rising"),
        ],
    },
    {
        "name": "Coupling misalignment",
        "conditions": [
            ("coupling offset", "level_worse"),
            ("2x harmonic", "rising"),
            ("overall vibration", "rising"),
            ("bearing temp", "rising"),
        ],
    },
]

CONFIDENCE_BY_PASS_COUNT = {4: "High", 3: "Medium", 2: "Low"}


def _match_rule(parameter_names: list[str]) -> dict | None:
    names_lower = [p.lower() for p in parameter_names]
    best_rule, best_score = None, 0
    for rule in RULES:
        score = sum(
            1 for keyword, _ in rule["conditions"] if any(keyword in name for name in names_lower)
        )
        if score > best_score:
            best_rule, best_score = rule, score
    if best_rule is None or best_score < 2:
        return None
    return best_rule


def _level_worse(param: dict) -> bool:
    if param["alarm"] is None or param["value"] is None:
        return False
    if param["direction"] == "higher_is_worse":
        return param["value"] >= param["alarm"]
    return param["value"] <= param["alarm"]


def diagnose(conn: sqlite3.Connection, tag: str, replay_date: str) -> dict:
    week_state = resolve_week(conn, tag, replay_date)
    if week_state is None:
        return {
            "rule_name": None,
            "confidence": None,
            "conditions": [],
            "note": "Suggested, needs engineer review",
            "reason": "No weekly condition data on or before the replay date.",
        }

    parameter_names = [p["parameter"] for p in week_state["parameters"]]
    rule = _match_rule(parameter_names)
    if rule is None:
        return {
            "rule_name": None,
            "confidence": None,
            "conditions": [],
            "note": "Suggested, needs engineer review",
            "reason": "No diagnosis rule matches this equipment's monitored parameters.",
        }

    by_name = {p["parameter"].lower(): p for p in week_state["parameters"]}

    condition_rows = []
    passes = 0
    for keyword, check in rule["conditions"]:
        match = next((p for name, p in by_name.items() if keyword in name), None)
        if match is None:
            condition_rows.append(
                {
                    "parameter": keyword,
                    "value": None,
                    "limit": None,
                    "trend": None,
                    "pass": False,
                }
            )
            continue
        if check == "level_worse":
            ok = _level_worse(match)
            limit_label = match["alarm"]
        else:
            ok = match["trend"] == check
            limit_label = match["alarm"]
        passes += 1 if ok else 0
        condition_rows.append(
            {
                "parameter": match["parameter"],
                "value": match["value"],
                "limit": limit_label,
                "direction": match["direction"],
                "trend": match["trend"],
                "check": check,
                "pass": ok,
            }
        )

    confidence = CONFIDENCE_BY_PASS_COUNT.get(passes)

    return {
        "rule_name": rule["name"] if confidence else None,
        "confidence": confidence,
        "conditions": condition_rows,
        "passes": passes,
        "of": len(rule["conditions"]),
        "week": week_state["week"],
        "week_date": week_state["week_date"],
        "note": "Suggested, needs engineer review",
    }
