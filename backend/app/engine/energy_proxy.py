"""Energy proxy (SPEC section 5.10, low priority, built last).

"No metered energy data exists. Daily sum of motor current per equipment as a 'Motor load
index', 7-day moving average forecast for the next 7 days. Always labeled 'Proxy derived
from motor current, not metered energy'."
"""

import math
import sqlite3
import statistics
from datetime import date, timedelta

LABEL = "Proxy derived from motor current, not metered energy"
MOVING_AVERAGE_DAYS = 7
FORECAST_DAYS = 7


def get_energy_proxy(conn: sqlite3.Connection, tag: str, replay_date: str | None = None) -> dict:
    """Motor load index up to the replay date (replay_date=None is the retrospective full record).
    The 7-day forecast is anchored at the replay date: it starts the day after it and uses only
    data up to it. Forecast entries are marked kind="forecast"; they are the only dates after the
    replay date this endpoint returns, and they are projections, not data."""
    sql = (
        "SELECT substr(ts, 1, 10) AS day, SUM(value) AS daily_sum FROM sensor_hourly "
        "WHERE equipment_tag = ? AND signal = 'motor_current' AND value IS NOT NULL"
    )
    params: list = [tag]
    if replay_date is not None:
        sql += " AND ts <= ?"
        params.append(replay_date + " 23:59:59")
    rows = conn.execute(sql + " GROUP BY day ORDER BY day", params).fetchall()

    axis_days = conn.execute(
        "SELECT COUNT(DISTINCT substr(ts, 1, 10)) FROM sensor_hourly "
        "WHERE equipment_tag = ? AND signal = 'motor_current' AND value IS NOT NULL",
        (tag,),
    ).fetchone()[0]

    if not rows:
        return {"label": LABEL, "axis_days": axis_days, "history": [], "moving_average": [], "forecast": []}

    days = [r[0] for r in rows]
    daily_sums = [r[1] for r in rows]

    moving_average = []
    for i in range(len(daily_sums)):
        window = daily_sums[max(0, i - MOVING_AVERAGE_DAYS + 1) : i + 1]
        moving_average.append(round(statistics.mean(window), 2))

    # Forecast: the last 7-day moving average held flat for the next 7 days, starting the day
    # after the replay date. Documented assumption, not a fitted model.
    last_value = moving_average[-1]
    # Anchored at the replay date when the data reaches it, otherwise at the last day with data.
    anchor_day = min(date.fromisoformat(replay_date), date.fromisoformat(days[-1])) if replay_date else date.fromisoformat(days[-1])
    forecast = [
        {"day": (anchor_day + timedelta(days=i)).isoformat(), "value": last_value, "kind": "forecast"}
        for i in range(1, FORECAST_DAYS + 1)
    ]

    return {
        "label": LABEL,
        "axis_days": axis_days,
        "history": [{"day": d, "motor_load_index": round(v, 2)} for d, v in zip(days, daily_sums)],
        "moving_average": [{"day": d, "value": v} for d, v in zip(days, moving_average)],
        "forecast": forecast,
        "assumption": (
            f"Forecast is the {MOVING_AVERAGE_DAYS}-day moving average on the replay date held flat for the "
            f"next {FORECAST_DAYS} days, not a fitted model: the hourly record has no seasonality to learn from."
        ),
    }


def motor_load_week(conn: sqlite3.Connection, tag: str, replay_date: str) -> dict:
    """Motor load index for the replay week (the 7 days up to and including the replay date), the
    week before it, and the forecast for the next 7 days, plus the forecast direction."""
    proxy = get_energy_proxy(conn, tag, replay_date)
    history = {h["day"]: h["motor_load_index"] for h in proxy["history"]}
    anchor = date.fromisoformat(replay_date)

    def total(first_offset: int, last_offset: int) -> float | None:
        values = [
            history[(anchor - timedelta(days=k)).isoformat()]
            for k in range(first_offset, last_offset + 1)
            if (anchor - timedelta(days=k)).isoformat() in history
        ]
        return round(sum(values), 2) if values else None

    week = total(0, 6)
    previous = total(7, 13)
    forecast = round(sum(f["value"] for f in proxy["forecast"]), 2) if proxy["forecast"] else None
    return {
        "week": week,
        "previous_week": previous,
        "forecast_next_7_days": forecast,
        "forecast_direction": _direction(forecast, week),
    }


def _direction(forecast: float | None, current: float | None) -> str | None:
    """Forecast next 7 days vs the replay week: up or down beyond 2%, otherwise flat."""
    if forecast is None or not current:
        return None
    change = (forecast - current) / current
    if change > 0.02:
        return "up"
    if change < -0.02:
        return "down"
    return "flat"


# Emission estimate, motor-driven equipment only (heat exchangers have no motor drive, see DQ3).
# Per ON hour: power kW = sqrt(3) x V(kV) x I(A) x PF, so energy kWh = kW x 1 h, summed per
# day; CO2e kg = kWh x grid factor. Labeled as an estimate from motor current, not metered.
EMISSION_LABEL = "Estimate from motor current, not metered"
NON_MOTOR_FAMILIES = {"heat_exchanger"}
EMISSION_SERIES_DAYS = 7


def _emission_factors() -> dict:
    from app import config

    return {
        "motor_voltage_kv": config.MOTOR_VOLTAGE_KV,
        "power_factor": config.POWER_FACTOR,
        "grid_emission_factor_kg_per_kwh": config.GRID_EMISSION_FACTOR_KG_PER_KWH,
    }


def _kwh_per_current_amp_hour(factors: dict) -> float:
    return math.sqrt(3) * factors["motor_voltage_kv"] * factors["power_factor"]


def get_emission(conn: sqlite3.Connection, tag: str, replay_date: str) -> dict:
    """Daily CO2e estimate on or before the replay date (never after it)."""
    family_row = conn.execute("SELECT eq_type_family FROM equipment WHERE tag = ?", (tag,)).fetchone()
    factors = _emission_factors()
    if family_row is None or family_row[0] in NON_MOTOR_FAMILIES:
        return {"applicable": False, "label": EMISSION_LABEL, "factors": factors, "series": [], "today_kg": None, "week_kg": None}

    rows = conn.execute(
        "SELECT substr(ts, 1, 10) AS day, SUM(value) FROM sensor_hourly "
        "WHERE equipment_tag = ? AND signal = 'motor_current' AND run_status = 'ON' "
        "AND value IS NOT NULL AND substr(ts, 1, 10) <= ? GROUP BY day ORDER BY day",
        (tag, replay_date),
    ).fetchall()
    kwh_factor = _kwh_per_current_amp_hour(factors)
    series = [
        {"day": day, "kwh": round(amp_hours * kwh_factor, 1), "kg_co2e": round(amp_hours * kwh_factor * factors["grid_emission_factor_kg_per_kwh"], 1)}
        for day, amp_hours in rows
    ]
    recent = series[-EMISSION_SERIES_DAYS:]
    today = series[-1] if series and series[-1]["day"] == replay_date else None
    return {
        "applicable": True,
        "label": EMISSION_LABEL,
        "factors": factors,
        "series": recent,
        "today_kg": today["kg_co2e"] if today else None,
        "week_kg": round(sum(p["kg_co2e"] for p in recent), 1) if recent else None,
    }
