"""Extract structured data from one RCA deck (SPEC section 2, last bullet).

Falls back to `data/seed/rca_manual.json` entries (source = manual_extraction) when a
slide's layout cannot be matched by the geometry clustering in pptx_geometry.py.
"""

import json
import re
from collections import defaultdict

from pptx import Presentation

from app.ingest.readers.pptx_geometry import (
    extract_paired_rows,
    extract_table_blocks,
    get_subtitle,
)
from app.ingest.transforms.text_cleanup import display_text

# Ordered most-specific-first: several blocks share a "Corrective Action" column, so that
# generic name is checked last, only once the more distinctive column names have failed to match.
CAPA_CATEGORY_BY_HEADER_COLUMN = [
    ("Pro-Active Action", "pro_active"),
    ("Preventive Action", "preventive"),
    ("Countermeasure", "risk_countermeasure"),
    ("PM No.", "pm_schedule"),
    ("Corrective Action", "corrective"),
]


def _label_value_tiles(shapes) -> dict[str, str]:
    by_left = defaultdict(list)
    for shape in shapes:
        if not shape.has_text_frame:
            continue
        text = shape.text_frame.text.strip()
        if not text or shape.top < 1_100_000 or shape.top > 6_400_000:
            continue
        by_left[shape.left].append((shape.top, text))

    tiles: dict[str, str] = {}
    for _, items in by_left.items():
        items.sort(key=lambda t: t[0])
        for i in range(0, len(items) - 1, 2):
            tiles[items[i][1]] = items[i + 1][1]
    return tiles


def _problem_statement(shapes) -> str | None:
    candidates = [
        s.text_frame.text.strip()
        for s in shapes
        if s.has_text_frame and s.left > 7_000_000 and s.top > 3_700_000 and len(s.text_frame.text.strip()) > 60
    ]
    return max(candidates, key=len) if candidates else None


def _capa_rows_from_block(block, rca_id: int, tag: str) -> list[dict]:
    category = None
    for col, cat in CAPA_CATEGORY_BY_HEADER_COLUMN:
        if col in block.header:
            category = cat
            break
    if category is None:
        return []

    out = []
    for row in block.rows:
        cells = dict(zip(block.header, row))
        if category in ("corrective", "pro_active"):
            action_text = cells.get("Corrective Action") or cells.get("Pro-Active Action")
            item_code = cells.get("RC")
            plan_date, pic, status = cells.get("Plan Date"), cells.get("PIC"), cells.get("Status")
            extra = {}
        elif category == "preventive":
            action_text = cells.get("Preventive Action")
            item_code = cells.get("Item")
            plan_date, pic, status = cells.get("Plan Date"), cells.get("PIC"), None
            extra = {"possible_root_cause": cells.get("Possible Root Cause")}
        elif category == "risk_countermeasure":
            action_text = cells.get("Countermeasure")
            item_code = None
            plan_date, pic, status = cells.get("Plan Date"), cells.get("PIC"), None
            extra = {
                "corrective_action": cells.get("Corrective Action"),
                "potential_risk": cells.get("Potential Risk"),
            }
        else:  # pm_schedule
            action_text = cells.get("Description")
            item_code = cells.get("PM No.")
            plan_date, pic, status = None, None, None
            extra = {"group": cells.get("Group"), "interval": cells.get("Interval")}

        out.append(
            {
                "rca_id": rca_id,
                "equipment_tag": tag,
                "action_category": category,
                "item_code": item_code,
                "action_text": action_text,
                "plan_date": plan_date,
                "pic": pic,
                "status": status,
                "extra_json": json.dumps(extra) if any(extra.values()) else None,
                "source": "pptx_extraction",
            }
        )
    return out


def _four_col_rows(block, key_names) -> list[dict]:
    """SPEC 8: em dash never appears on screen; these evidence cells are free text copied
    from the deck author and are the one place in the RCA extraction that has them."""
    out = []
    for row in block.rows:
        out.append(
            {key_names[i]: display_text(row[i]) if i < len(row) else None for i in range(len(row))}
        )
    return out


def read_rca_deck(path, rca_id: int, tag: str) -> dict:
    prs = Presentation(path)
    result = {
        "problem_statement": None,
        "chronology": [],
        "four_p": [],
        "four_m_1e": [],
        "root_cause": None,
        "capa_actions": [],
        "loss_summary": {},
    }

    for slide in prs.slides:
        subtitle = get_subtitle(slide)
        shapes = list(slide.shapes)

        if subtitle == "AR Details & Problem Statement":
            result["problem_statement"] = _problem_statement(shapes)

        elif subtitle == "Chronology of Events":
            result["chronology"] = [
                {"datetime": dt, "event": event} for dt, event in extract_paired_rows(shapes)
            ]

        elif subtitle == "Parameter Verification (4P)":
            for block in extract_table_blocks(shapes):
                result["four_p"] = _four_col_rows(block, ["item", "parameter", "result", "evidence"])

        elif subtitle == "4M + 1E Verification":
            for block in extract_table_blocks(shapes):
                result["four_m_1e"] = _four_col_rows(block, ["item", "factor", "result", "evidence"])
            for shape in shapes:
                if shape.has_text_frame and shape.text_frame.text.strip().startswith("ROOT CAUSE:"):
                    result["root_cause"] = re.sub(
                        r"^ROOT CAUSE:\s*", "", shape.text_frame.text.strip()
                    )

        elif subtitle == "Corrective & Pro-Active Action (CAPAA)":
            for block in extract_table_blocks(shapes):
                result["capa_actions"] += _capa_rows_from_block(block, rca_id, tag)

        elif subtitle == "Preventive & Risk Analysis":
            for block in extract_table_blocks(shapes):
                result["capa_actions"] += _capa_rows_from_block(block, rca_id, tag)

        elif subtitle is None:
            tiles = _label_value_tiles(shapes)
            if "DOWNTIME" in tiles:
                result["loss_summary"] = tiles
                if not result["root_cause"] and "ROOT CAUSE" in tiles:
                    result["root_cause"] = tiles["ROOT CAUSE"]

    return result


def load_manual_seed(seed_path) -> list[dict]:
    if not seed_path.exists():
        return []
    with open(seed_path, encoding="utf-8") as f:
        return json.load(f)
