"""Health check - najprostszy endpoint, ale ważny.

Służy do sprawdzenia czy API żyje. Przydatny dla:
- Docker health checks
- Load balancerów
- Twojego spokoju ducha ("czy to w ogóle działa?")
"""

from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
