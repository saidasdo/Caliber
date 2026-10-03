from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    actions,
    admin,
    assumptions,
    audit_log,
    backtest,
    data_quality,
    diagnosis_review,
    equipment,
    kpi_dictionary,
    overview,
    plants,
    problems,
    replay,
    source_map,
)
from app.config import DB_PATH, PRODUCT_NAME

app = FastAPI(title=PRODUCT_NAME)


@app.on_event("startup")
def ensure_db_built() -> None:
    """Build db/plantpulse.sqlite on first boot if missing. On Vercel this fires on every
    cold start, since DB_PATH there is an ephemeral /tmp path (see app/config.py)."""
    if not DB_PATH.exists():
        from app.ingest.run import run_ingestion

        run_ingestion(verbose=False)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(overview.router, prefix="/api")
app.include_router(plants.router, prefix="/api")
app.include_router(equipment.router, prefix="/api")
app.include_router(actions.router, prefix="/api")
app.include_router(problems.router, prefix="/api")
app.include_router(audit_log.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(data_quality.router, prefix="/api")
app.include_router(kpi_dictionary.router, prefix="/api")
app.include_router(replay.router, prefix="/api")
app.include_router(source_map.router, prefix="/api")
app.include_router(assumptions.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(diagnosis_review.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "product_name": PRODUCT_NAME}
