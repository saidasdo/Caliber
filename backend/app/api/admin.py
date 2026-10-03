"""POST /api/reset-demo-data (SPEC section 10 phase 9: "Reset demo data" button).

Re-runs the full ingestion pipeline in-process, discarding any approved/rejected/status-
changed actions made during the session and restoring the pristine seed state.
"""

from fastapi import APIRouter

from app.ingest.run import run_ingestion

router = APIRouter()


@router.post("/reset-demo-data")
def reset_demo_data():
    results = run_ingestion(verbose=False)
    all_pass = all(r.passed is not False for r in results)
    return {
        "status": "ok" if all_pass else "acceptance_checks_failed",
        "checks": [
            {"name": r.name, "passed": r.passed, "detail": r.detail} for r in results
        ],
    }
