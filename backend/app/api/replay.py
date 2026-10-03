"""GET /api/replay (SPEC section 4): default date and per-equipment presets."""

from fastapi import APIRouter

from app.config import PRODUCT_NAME
from app.engine.replay import DEFAULT_REPLAY_DATE, REPLAY_PRESETS

router = APIRouter()


@router.get("/replay")
def get_replay_config():
    return {
        "product_name": PRODUCT_NAME,
        "default_replay_date": DEFAULT_REPLAY_DATE,
        "presets": [
            {"equipment_tag": tag, "label": "1 week before failure", "replay_date": d}
            for tag, d in REPLAY_PRESETS.items()
        ],
    }
