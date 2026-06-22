"""
Entity and keyword listing routes — aggregated views.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import verify_token
from app.api.models.responses import APIResponse

router = APIRouter(
    tags=["entities & keywords"],
    dependencies=[Depends(verify_token)],
)


@router.get(
    "/documentos/entities",
    summary="Listar entidades de documentos",
    description="Retorna todas as entidades nomeadas extraídas dos documentos, "
    "com contagem de ocorrências. Útil para nuvens de palavras e filtros.",
    response_model=APIResponse,
)
async def list_documento_entities(
    entity_type: Optional[str] = Query(
        None, description="Filtrar por tipo: PER, ORG, LOC, DATE", examples=["ORG"]
    ),
    min_count: int = Query(1, ge=1, description="Contagem mínima para incluir", examples=[2]),
    page: int = Query(1, ge=1, description="Página", examples=[1]),
    page_size: int = Query(50, ge=1, le=500, description="Itens por página", examples=[50]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/artefatos/entities",
    summary="Listar entidades de artefatos",
    description="Retorna todas as entidades nomeadas extraídas dos artefatos, com contagem de ocorrências.",
    response_model=APIResponse,
)
async def list_artefato_entities(
    entity_type: Optional[str] = Query(
        None, description="Filtrar por tipo: PER, ORG, LOC, TECH", examples=["TECH"]
    ),
    min_count: int = Query(1, ge=1, description="Contagem mínima para incluir", examples=[2]),
    page: int = Query(1, ge=1, description="Página", examples=[1]),
    page_size: int = Query(50, ge=1, le=500, description="Itens por página", examples=[50]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/documentos/keywords",
    summary="Listar keywords de documentos",
    description="Retorna todas as palavras-chave extraídas dos documentos, com contagem de ocorrências.",
    response_model=APIResponse,
)
async def list_documento_keywords(
    min_count: int = Query(1, ge=1, description="Contagem mínima para incluir", examples=[2]),
    page: int = Query(1, ge=1, description="Página", examples=[1]),
    page_size: int = Query(50, ge=1, le=500, description="Itens por página", examples=[50]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/artefatos/keywords",
    summary="Listar keywords de artefatos",
    description="Retorna todas as palavras-chave extraídas dos artefatos, com contagem de ocorrências.",
    response_model=APIResponse,
)
async def list_artefato_keywords(
    min_count: int = Query(1, ge=1, description="Contagem mínima para incluir", examples=[2]),
    page: int = Query(1, ge=1, description="Página", examples=[1]),
    page_size: int = Query(50, ge=1, le=500, description="Itens por página", examples=[50]),
):
    raise HTTPException(status_code=501, detail="Not implemented")
