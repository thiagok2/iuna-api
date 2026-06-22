"""
Statistics routes — index counts, enrichment coverage, etc.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import verify_token
from app.api.models.responses import StatsResponse

router = APIRouter(
    prefix="/stats",
    tags=["stats"],
    dependencies=[Depends(verify_token)],
)


@router.get(
    "/",
    summary="Estatísticas do sistema",
    description="Retorna estatísticas agregadas: contagem de documentos e artefatos, "
    "número de chunks, cobertura de enriquecimento (percentual de docs com summary, "
    "vectorization, entities, keywords).",
    response_model=StatsResponse,
)
async def get_stats():
    raise HTTPException(status_code=501, detail="Not implemented")
