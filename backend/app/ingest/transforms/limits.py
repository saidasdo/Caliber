"""Parse "Alarm / Trip" limit strings and infer alert direction (SPEC section 2)."""

import re

# Parameters explicitly called out as "lower is worse" in SPEC section 2.
LOWER_IS_WORSE_KEYWORDS = (
    "seal flush flow",
    "discharge pressure",
    "lube oil supply press",
    "heat duty",
    "cold outlet temp",
)


def parse_alarm_trip(raw: str) -> tuple[float, float]:
    """"7.0 / 11.0" -> (7.0, 11.0)"""
    match = re.match(r"\s*([-\d.]+)\s*/\s*([-\d.]+)\s*", raw)
    if not match:
        raise ValueError(f"Cannot parse alarm/trip value: {raw!r}")
    return float(match.group(1)), float(match.group(2))


def infer_direction(parameter_name: str, alarm: float, trip: float) -> str:
    """Prefer the explicit numeric relationship; fall back to the parameter-name keyword list."""
    if alarm != trip:
        return "lower_is_worse" if alarm > trip else "higher_is_worse"
    name = parameter_name.lower()
    if any(keyword in name for keyword in LOWER_IS_WORSE_KEYWORDS):
        return "lower_is_worse"
    return "higher_is_worse"
