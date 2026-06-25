"""
Search routes for artefatos.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import verify_token
from app.api.models.responses import APIResponse, SearchResponse
from app.clients.es_client import es_client
from app.config import settings
from app.services.artefatos_search import ArtefatosSearchService
from app.services.chunks_search import ChunksSearchService

router = APIRouter(
    prefix="/artefatos/search",
    tags=["artefatos - search"],
    dependencies=[Depends(verify_token)],
)

_INDEX = lambda: settings.index_artefatos  # noqa: E731
_CHUNKS = lambda: settings.index_artefatos_chunks  # noqa: E731


def _svc() -> ArtefatosSearchService:
    return ArtefatosSearchService(es_client)


def _chunks_svc() -> ChunksSearchService:
    return ChunksSearchService(es_client)


@router.get(
    "/",
    summary="Busca full-text em artefatos",
    description="Busca com match_phrase + fuzziness nos artefatos didáticos. "
    "Suporta filtros por tipo, disciplina, curso, autor e ano.",
    response_model=SearchResponse,
)
async def search_artefatos(
    q: str = Query(..., description="Termo de busca", examples=["programação orientada a objetos"]),
    page: int = Query(1, ge=1, description="Página", examples=[1]),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página", examples=[20]),
    tipo: Optional[str] = Query(None, description="Filtro por tipo de artefato", examples=["livro"]),
    disciplina: Optional[str] = Query(None, description="Filtro por disciplina", examples=["Programação I"]),
    curso: Optional[str] = Query(None, description="Filtro por curso", examples=["Ciência da Computação"]),
    autor: Optional[str] = Query(None, description="Filtro por autor", examples=["Prof. João"]),
    ano: Optional[int] = Query(None, description="Filtro por ano", examples=[2024]),
    publico: Optional[bool] = Query(None, description="Filtro público/privado"),
    exact_phrase: bool = Query(False, description="Busca por frase exata (match_phrase)"),
    with_aggregations: bool = Query(
        False,
        description="Incluir agregações (tipo, disciplina) junto com os resultados.",
    ),
):
    filters: dict = {
        "artefato.tipo": tipo,
        "artefato.disciplina.keyword": disciplina,
    }
    result = await _svc().search_fulltext(
        _INDEX(), q, page, page_size, filters, exact_phrase, with_aggregations
    )
    return SearchResponse(
        data=result["results"],
        meta={"page": page, "page_size": page_size, "total": result["total"], "query": q},
        facets=result.get("aggregations"),
    )


@router.get(
    "/similar/{artefato_id}",
    summary="Artefatos similares (More Like This)",
    description="Encontra artefatos similares ao artefato informado usando More Like This "
    "ou busca vetorial por similaridade de embeddings.",
    response_model=SearchResponse,
)
async def search_artefatos_similar(
    artefato_id: str = Path(..., description="ID do artefato de referência", examples=["art-456"]),
    page_size: int = Query(10, ge=1, le=50, description="Quantidade de resultados", examples=[10]),
):
    result = await _svc().search_similar(_INDEX(), artefato_id, page_size)
    return SearchResponse(
        data=result["results"],
        meta={"total": result["total"]},
    )


@router.get(
    "/by-entity",
    summary="Buscar artefatos por entidade nomeada",
    description="Retorna artefatos que contêm a entidade nomeada especificada.",
    response_model=SearchResponse,
)
async def search_artefatos_by_entity(
    entity: str = Query(..., description="Nome da entidade a buscar", examples=["Python"]),
    entity_type: Optional[str] = Query(None, description="Tipo da entidade: PER, ORG, LOC, TECH, etc.", examples=["TECH"]),
    page: int = Query(1, ge=1, description="Página", examples=[1]),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página", examples=[20]),
):
    result = await _svc().search_by_entity(_INDEX(), entity, entity_type, page, page_size)
    return SearchResponse(
        data=result["results"],
        meta={"page": page, "page_size": page_size, "total": result["total"]},
    )


@router.get(
    "/by-keyword",
    summary="Buscar artefatos por keyword",
    description="Retorna artefatos que possuem a keyword especificada em seus metadados extraídos.",
    response_model=SearchResponse,
)
async def search_artefatos_by_keyword(
    keyword: str = Query(..., description="Keyword a buscar", examples=["estrutura de dados"]),
    page: int = Query(1, ge=1, description="Página", examples=[1]),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página", examples=[20]),
):
    result = await _svc().search_by_keyword(_INDEX(), keyword, page, page_size)
    return SearchResponse(
        data=result["results"],
        meta={"page": page, "page_size": page_size, "total": result["total"]},
    )


@router.get(
    "/suggest",
    summary="Autocomplete/sugestões de busca em artefatos",
    description="Retorna sugestões de termos para autocomplete conforme o usuário digita.",
    response_model=APIResponse,
)
async def search_artefatos_suggest(
    q: str = Query(..., min_length=2, description="Prefixo para sugestão (mín. 2 caracteres)", examples=["prog"]),
    size: int = Query(5, ge=1, le=20, description="Número de sugestões", examples=[5]),
):
    suggestions = await _svc().suggest(_INDEX(), q, size)
    return APIResponse(data=suggestions)


@router.get(
    "/chunks",
    summary="Buscar nos chunks de artefatos",
    description="Busca full-text dentro dos chunks (trechos) dos artefatos. "
    "Útil para encontrar passagens específicas em artefatos longos.",
    response_model=SearchResponse,
)
async def search_artefatos_chunks(
    q: str = Query(..., description="Termo de busca nos chunks", examples=["herança e polimorfismo"]),
    page: int = Query(1, ge=1, description="Página", examples=[1]),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página", examples=[20]),
    artefato_id: Optional[str] = Query(None, description="Filtrar chunks de um artefato específico", examples=["art-456"]),
):
    result = await _chunks_svc().search(_CHUNKS(), q, page, page_size, artefato_id)
    return SearchResponse(
        data=result["results"],
        meta={"page": page, "page_size": page_size, "total": result["total"], "query": q},
    )
