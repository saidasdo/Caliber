"""GET /api/source-map (SPEC section 5.9)."""

from fastapi import APIRouter

from app.catalog.source_map import JOIN_KEYS, SOURCE_MAP

router = APIRouter()


@router.get("/source-map")
def get_source_map():
    return {"entries": SOURCE_MAP, "join_keys": JOIN_KEYS}
