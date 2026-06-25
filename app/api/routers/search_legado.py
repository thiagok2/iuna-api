"""
Rotas de busca LEGADO — índice `documentos_ifal` (pré-enriquecimento).

Estas rotas são mantidas para compatibilidade com o sistema legado (Laravel).
O índice legado não possui resumo, keywords, entidades nem embedding_vector.
Prefixo: /api/v1/legado/documentos

IMPORTANTE: a rota /{doc_id}/similar deve ficar registrada ANTES de /{doc_id}
para que FastAPI não confunda o segmento "similar" com um doc_id.
"""

from typing import Optional

from elasticsearch import NotFoundError as ESNotFoundError
from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.api.dependencies import verify_token
from app.api.models.responses import APIResponse, SearchResponse
from app.clients.es_client import es_client
from app.config import settings
from app.services.legado_search_service import LegadoSearchService

router = APIRouter(
    prefix="/legado/documentos",
    tags=["legado - documentos_ifal"],
    dependencies=[Depends(verify_token)],
)

_INDEX = lambda: settings.index_documentos_ifal  # noqa: E731


def _svc() -> LegadoSearchService:
    return LegadoSearchService(es_client)


# ---------------------------------------------------------------------------
# Busca
# ---------------------------------------------------------------------------


@router.get(
    "/search",
    summary="[LEGADO] Busca full-text em documentos_ifal",
    description="Busca no índice legado `documentos_ifal` (pré-enriquecimento). "
    "Campos pesquisados: **attachment.content, ato.titulo, ato.ementa, ato.tags**. "
    "Sem resumo, keywords, entidades ou popularity_score. "
    "\n\n"
    "**exact_phrase**: envolve a query em match_phrase em vez de multi_match fuzzy. "
    "\n\n"
    "**with_aggregations**: retorna facets de tipo_doc, esfera e ano juntos com os resultados — "
    "recomendado na primeira página ou quando o cliente precisa dos filtros dinâmicos. "
    "Para páginas subsequentes, desative para menor latência. "
    "\n\n"
    "Se não há resultados com `tipo_doc`, retenta automaticamente sem ele (fallback do legado).",
    response_model=SearchResponse,
)
async def search_legado(
    q: str = Query(..., description="Termo de busca", examples=["processo seletivo"]),
    page: int = Query(1, ge=1, description="Página", examples=[1]),
    page_size: int = Query(10, ge=1, le=100, description="Itens por página (default legado: 10)", examples=[10]),
    exact_phrase: bool = Query(False, description="Busca por frase exata (match_phrase)"),
    with_aggregations: bool = Query(
        True,
        description="Incluir agregações de tipo_doc, esfera e ano. "
        "Default true (replica comportamento legado na pág. 1). "
        "Use false em páginas subsequentes para menor latência.",
    ),
    publico: Optional[bool] = Query(None, description="Filtro público/privado (null = todos)"),
    tipo_doc: Optional[str] = Query(None, description="Filtro por tipo de documento", examples=["resolucao"]),
    esfera: Optional[str] = Query(None, description="Filtro por esfera", examples=["federal"]),
    ano: Optional[int] = Query(None, description="Filtro por ano", examples=[2023]),
    orgao: Optional[str] = Query(None, description="Filtro por órgão (ato.fonte.orgao)", examples=["IFAL"]),
    periodo: Optional[str] = Query(
        None,
        description="Período de publicação: '2024' ou '2020-2024'",
        examples=["2020-2024"],
    ),
):
    result = await _svc().search(
        index=_INDEX(),
        q=q,
        page=page,
        page_size=page_size,
        exact_phrase=exact_phrase,
        tipo_doc=tipo_doc,
        esfera=esfera,
        ano=ano,
        orgao=orgao,
        publico=publico,
        periodo=periodo,
        with_aggregations=with_aggregations,
    )
    return SearchResponse(
        data=result["results"],
        meta={
            "page": page,
            "page_size": page_size,
            "total": result["total"],
            "query": q,
            "exact_phrase": exact_phrase,
        },
        facets=result.get("aggregations"),
    )


# ---------------------------------------------------------------------------
# Similar (registrado ANTES de /{doc_id} para evitar conflito de rotas)
# ---------------------------------------------------------------------------


@router.get(
    "/{doc_id}/similar",
    summary="[LEGADO] Documentos similares (More Like This) no documentos_ifal",
    description="Usa More Like This nos campos **ato.ementa** e **ato.tags** do índice legado. "
    "Equivale ao `likeDocuments` do sistema legado Laravel.",
    response_model=SearchResponse,
)
async def similar_legado(
    doc_id: str = Path(..., description="ID do documento de referência (ES _id)", examples=["abc123"]),
    page_size: int = Query(6, ge=1, le=20, description="Quantidade de similares", examples=[6]),
):
    try:
        result = await _svc().similar(_INDEX(), doc_id, page_size)
    except ESNotFoundError:
        raise HTTPException(status_code=404, detail=f"Documento não encontrado: {doc_id}")
    return SearchResponse(
        data=result["results"],
        meta={"total": result["total"]},
    )


# ---------------------------------------------------------------------------
# Get por ID (viewNormativa — registrado DEPOIS de /{doc_id}/similar)
# ---------------------------------------------------------------------------


@router.get(
    "/{doc_id}",
    summary="[LEGADO] Buscar documento por ID (viewNormativa)",
    description="Retorna o documento completo pelo **ES _id** no índice legado. "
    "Equivale ao `viewNormativa` do sistema legado Laravel. "
    "\n\nNo sistema legado, o `_id` do Elasticsearch é o próprio `ato.arquivo` "
    "(caminho/nome do arquivo). Use o `id` retornado pelos resultados de busca. "
    "\n\n**Nota**: keywords do legado eram armazenadas em MySQL (não disponíveis aqui).",
    response_model=APIResponse,
)
async def get_documento_legado(
    doc_id: str = Path(..., description="ES _id do documento (= ato.arquivo no legado)", examples=["abc123"]),
):
    try:
        doc = await _svc().get_by_id(_INDEX(), doc_id)
    except ESNotFoundError:
        raise HTTPException(status_code=404, detail=f"Documento não encontrado: {doc_id}")
    return APIResponse(data=doc)
