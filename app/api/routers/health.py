"""
Health-check and system info endpoints.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import verify_token
from app.clients.es_client import es_client
from app.config import settings

router = APIRouter()


@router.get("/health-check")
async def health_check():
    """Basic liveness probe — no dependencies checked. No auth required."""
    return {"status": "ok", "message": "IUNA API is running"}


@router.get("/info")
async def info():
    """Return basic API metadata. No auth required."""
    return {"name": settings.PROJECT_NAME, "version": "0.1.0"}


@router.get("/health", dependencies=[Depends(verify_token)])
async def health():
    """Deep health check — verifies connectivity to each dependency. Requires auth."""
    es_ok = await es_client.ping()

    dependencies = {
        "elasticsearch": {
            "status": "up" if es_ok else "down",
            "host": settings.ELASTICSEARCH_HOSTS,
        }
    }

    overall = "healthy" if es_ok else "degraded"

    return {
        "status": overall,
        "dependencies": dependencies,
    }
