"""
Health-check and system info endpoints.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import verify_token
from app.api.models.responses import HealthResponse
from app.clients.es_client import es_client
from app.config import settings

router = APIRouter()


@router.get(
    "/health-check",
    summary="Liveness probe",
    description="Verificação simples de que a API está respondendo. Não verifica dependências.",
    tags=["health"],
)
async def health_check():
    """Basic liveness probe — no dependencies checked. No auth required."""
    return {"status": "ok", "message": "IUNA API is running"}


@router.get(
    "/info",
    summary="Informações da API",
    description="Retorna nome e versão da API.",
    tags=["health"],
)
async def info():
    """Return basic API metadata. No auth required."""
    return {"name": settings.PROJECT_NAME, "version": "0.1.0"}


@router.get(
    "/health",
    summary="Deep health check",
    description="Verifica conectividade com todas as dependências (Elasticsearch). Requer autenticação.",
    response_model=HealthResponse,
    dependencies=[Depends(verify_token)],
    tags=["health"],
)
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
