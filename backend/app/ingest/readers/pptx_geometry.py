"""Generic geometry-based table reconstruction for the RCA decks.

The decks draw tables as a grid of paired Rectangle (fill) + TextBox (label/value) shapes,
not native PowerPoint tables, so `shape.has_table` is always False. Cells in the same row
share an identical `top`; a full-width single-line shape (~content width) acts as a section
divider between stacked sub-tables on one slide. Row counts vary per deck, so rows are
discovered by clustering, never hardcoded.
"""

from dataclasses import dataclass

CONTENT_TOP_MIN = 1_100_000   # below the black title bar
CONTENT_TOP_MAX = 6_400_000   # above the footer strip
DIVIDER_MIN_WIDTH = 9_000_000  # full content-width single-line section headers


@dataclass
class TableBlock:
    label: str | None
    header: list[str]
    rows: list[list[str]]


def _fix_mojibake(text: str) -> str:
    """Some of these decks have UTF-8 em dashes (and possibly other punctuation) that were
    saved after a mis-decode as Windows-1252, which turns U+2014 into the 3-character garbage
    sequence "â€”". Re-encoding as cp1252 and decoding as UTF-8 reverses exactly
    that mistake; anything that isn't actually mojibake just fails the round trip and is
    returned unchanged."""
    try:
        return text.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def _text_shapes(shapes):
    out = []
    for shape in shapes:
        if not shape.has_text_frame:
            continue
        text = _fix_mojibake(shape.text_frame.text.strip())
        if not text:
            continue
        if not (CONTENT_TOP_MIN < shape.top < CONTENT_TOP_MAX):
            continue
        out.append((shape.top, shape.left, text, shape.width))
    return out


def extract_table_blocks(shapes) -> list[TableBlock]:
    items = _text_shapes(shapes)

    tops = {}
    for top, left, text, width in items:
        tops.setdefault(top, []).append((left, text, width))

    divider_tops = {
        top for top, cells in tops.items() if len(cells) == 1 and cells[0][2] >= DIVIDER_MIN_WIDTH
    }

    ordered_tops = sorted(tops)
    blocks: list[TableBlock] = []
    current_label = None
    current_rows: list[list[str]] = []

    def flush():
        if not current_rows:
            return
        header, *data = current_rows
        blocks.append(TableBlock(label=current_label, header=header, rows=data))

    for top in ordered_tops:
        cells = sorted(tops[top], key=lambda c: c[0])
        if top in divider_tops:
            flush()
            current_label = cells[0][1]
            current_rows = []
        else:
            current_rows.append([text for _, text, _ in cells])
    flush()

    return blocks


def extract_paired_rows(shapes) -> list[tuple[str, str]]:
    """For slides like chronology: two text columns sharing a row `top`, sorted by `left`."""
    items = _text_shapes(shapes)
    tops: dict[int, list[tuple[int, str]]] = {}
    for top, left, text, _ in items:
        tops.setdefault(top, []).append((left, text))
    pairs = []
    for top in sorted(tops):
        cells = sorted(tops[top], key=lambda c: c[0])
        if len(cells) >= 2:
            pairs.append((cells[0][1], cells[1][1]))
    return pairs


def get_subtitle(slide) -> str | None:
    for shape in slide.shapes:
        if shape.has_text_frame and shape.top == 402336:
            return shape.text_frame.text.strip()
    return None
