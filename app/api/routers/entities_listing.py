"""
Entity and keyword listing routes — aggregated views.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import verify_token
from app.api.models.responses import APIResponse
from app.clients.es_client import es_client
from app.config import settings
from app.services.entities_listing_service import EntitiesListingService

router = APIRouter(
    tags=["entities & keywords"],
    dependencies=[Depends(verify_token)],
)

_DOC_INDEX = lambda: settings.index_documentos_ifal_v2  # noqa: E731
_ART_INDEX = lambda: settings.index_artefatos  # noqa: E731


def _svc() -> EntitiesListingService:
    return EntitiesListingService(es_client)


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
    items = await _svc().list_entities(_DOC_INDEX(), "ato", entity_type, min_count, page, page_size)
    return APIResponse(data=items, meta={"page": page, "page_size": page_size})


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
    items = await _svc().list_entities(_ART_INDEX(), "artefato", entity_type, min_count, page, page_size)
    return APIResponse(data=items, meta={"page": page, "page_size": page_size})


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
    items = await _svc().list_keywords(_DOC_INDEX(), "ato", min_count, page, page_size)
    return APIResponse(data=items, meta={"page": page, "page_size": page_size})


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
    items = await _svc().list_keywords(_ART_INDEX(), "artefato", min_count, page, page_size)
    return APIResponse(data=items, meta={"page": page, "page_size": page_size})
