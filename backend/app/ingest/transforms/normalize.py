"""Normalized helper columns (SPEC section 3): component_family, mechanism_norm, eq_type_family."""

import re


def split_param_unit(header: str) -> tuple[str, str | None]:
    """"Overall Vibration (mm/s)" / "Overall Vibration\\n(mm/s)" -> ("Overall Vibration", "mm/s")."""
    match = re.match(r"(.+?)\s*\(([^()]+)\)\s*$", header.replace("\n", " "))
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return header.replace("\n", " ").strip(), None

COMPONENT_FAMILY_MAP = {
    "Journal Bearing": "Bearing",
    "Motor Bearing": "Bearing",
}

# DQ10: these single-word F Mechanism values are non-standard vocabulary, found only on the
# five RCA incident rows. The normalized value is read off the RCA's own Risk Case Title so
# similar-incident scoring (section 5.6) has something usable; the raw value is kept as-is and
# DQ10 still flags it as an open data-quality issue (see dq_checks.py).
NON_STANDARD_MECHANISMS = {"High", "Mechanical", "Motor"}

RCA_MECHANISM_OVERRIDE = {
    "PU-2101B": "Leakage",
    "KO-3201": "High Vibration",
    "PM-4405B": "Overheat",
    "HE-3301": "Fouling",
    "BL-5702": "High Vibration",
}

# Tag prefix -> Eq. Type code map documented as "not an error" in SPEC section 6.
TAG_PREFIX_TO_EQ_TYPE = {
    "PM": "EM",
    "HE": "HB",
    "FN": "FA",
    "CV": "VA",
    "AZ": "SX",
}

# Eq. Type code -> family, used by DQ3/DQ9 plausibility rules and similar-incident scoring.
EQ_TYPE_FAMILY = {
    "PU": "pump",
    "CO": "compressor",
    "EM": "motor",
    "HB": "heat_exchanger",
    "BL": "blower",
    "TX": "transformer",
    "CD": "condenser",
    "PZ": "pressure_vessel",
    "SW": "switchgear",
    "RX": "reactor",
    "SX": "sensor_analyzer",
    "TR": "transmitter",
    "TK": "tank",
    "FA": "fan",
    "VA": "valve",
}


def component_family(component: str | None) -> str | None:
    if component is None:
        return None
    return COMPONENT_FAMILY_MAP.get(component, component)


def mechanism_norm(tag_number: str | None, f_mechanism: str | None) -> str | None:
    if f_mechanism is None:
        return None
    if f_mechanism in NON_STANDARD_MECHANISMS and tag_number in RCA_MECHANISM_OVERRIDE:
        return RCA_MECHANISM_OVERRIDE[tag_number]
    return f_mechanism


def eq_type_family(eq_type_code: str | None) -> str | None:
    if eq_type_code is None:
        return None
    return EQ_TYPE_FAMILY.get(eq_type_code, "other")


def tag_prefix(tag: str) -> str:
    match = re.match(r"[A-Za-z]+", tag)
    return match.group(0) if match else tag


def dehyphenate(tag: str) -> str:
    """"KO-3201" -> "KO3201", matching the production-data column prefix."""
    return tag.replace("-", "")
