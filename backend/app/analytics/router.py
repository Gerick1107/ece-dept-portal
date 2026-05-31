"""Analytics module — aggregate APIs only (no heavy client-side computation)."""

from fastapi import APIRouter

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/health")
def analytics_health():
    return {"module": "analytics", "status": "planned"}
