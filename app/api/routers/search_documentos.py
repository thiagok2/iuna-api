"""
Search routes for documentos.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.api.dependencies import verify_token
from app.api.models.responses import APIResponse, SearchResponse

router = APIRouter(
    prefix="/documentos/search",
    tags=["documentos - search"],
    dependencies=[Depends(verify_token)],
)


@router.get(
    "/",
    summary="Busca full-text em documentos",
    description="Busca com match_phrase + fuzziness nos documentos indexados. "
    "Suporta filtros por tipo, órgão, esfera, ano, categoria e intervalo de datas. "
    "Retorna highlights dos trechos relevantes.",
    response_model=SearchResponse,
)
async def search_documentos(
    q: str = Query(..., description="Termo de busca", examples=["edital processo seletivo"]),
    page: int = Query(1, ge=1, description="Página", examples=[1]),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página", examples=[20]),
    tipo_doc: Optional[str] = Query(None, description="Filtro por tipo de documento", examples=["edital"]),
    orgao: Optional[str] = Query(None, description="Filtro por órgão emissor", examples=["IFAL"]),
    esfera: Optional[str] = Query(None, description="Filtro por esfera (federal, estadual, municipal)", examples=["federal"]),
    ano: Optional[int] = Query(None, description="Filtro por ano de publicação", examples=[2024]),
    fonte: Optional[str] = Query(None, description="Filtro por fonte/origem", examples=["diario_oficial"]),
    publico: Optional[bool] = Query(None, description="Filtro público/privado"),
    data_inicio: Optional[str] = Query(None, description="Data início (YYYY-MM-DD)", examples=["2024-01-01"]),
    data_fim: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD)", examples=["2024-12-31"]),
    categoria: Optional[str] = Query(None, description="Filtro por categoria: institucional | didatico | projeto", examples=["institucional"]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/facets",
    summary="Facets/agregações da busca de documentos",
    description="Retorna agregações (counts por tipo_doc, orgao, esfera, ano) para a query fornecida. "
    "Útil para construir filtros dinâmicos na UI.",
    response_model=APIResponse,
)
async def search_documentos_facets(
    q: str = Query("", description="Termo de busca (vazio = todos)", examples=["edital"]),
    tipo_doc: Optional[str] = Query(None, description="Filtro por tipo", examples=["edital"]),
    orgao: Optional[str] = Query(None, description="Filtro por órgão", examples=["IFAL"]),
    esfera: Optional[str] = Query(None, description="Filtro por esfera", examples=["federal"]),
    ano: Optional[int] = Query(None, description="Filtro por ano", examples=[2024]),
    categoria: Optional[str] = Query(None, description="Filtro por categoria", examples=["institucional"]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/similar/{document_id}",
    summary="Documentos similares (More Like This)",
    description="Encontra documentos similares ao documento informado usando More Like This do Elasticsearch "
    "ou busca vetorial por similaridade de embeddings.",
    response_model=SearchResponse,
)
async def search_documentos_similar(
    document_id: str = Path(..., description="ID do documento de referência", examples=["abc123"]),
    page_size: int = Query(10, ge=1, le=50, description="Quantidade de resultados", examples=[10]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/by-entity",
    summary="Buscar documentos por entidade nomeada",
    description="Retorna documentos que contêm a entidade nomeada especificada "
    "(ex: nome de pessoa, organização, local).",
    response_model=SearchResponse,
)
async def search_documentos_by_entity(
    entity: str = Query(..., description="Nome da entidade a buscar", examples=["Instituto Federal de Alagoas"]),
    entity_type: Optional[str] = Query(None, description="Tipo da entidade: PER, ORG, LOC, etc.", examples=["ORG"]),
    page: int = Query(1, ge=1, description="Página", examples=[1]),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página", examples=[20]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/by-keyword",
    summary="Buscar documentos por keyword",
    description="Retorna documentos que possuem a keyword especificada em seus metadados extraídos.",
    response_model=SearchResponse,
)
async def search_documentos_by_keyword(
    keyword: str = Query(..., description="Keyword a buscar", examples=["processo seletivo"]),
    page: int = Query(1, ge=1, description="Página", examples=[1]),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página", examples=[20]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/suggest",
    summary="Autocomplete/sugestões de busca",
    description="Retorna sugestões de termos para autocomplete conforme o usuário digita.",
    response_model=APIResponse,
)
async def search_documentos_suggest(
    q: str = Query(..., min_length=2, description="Prefixo para sugestão (mín. 2 caracteres)", examples=["edi"]),
    size: int = Query(5, ge=1, le=20, description="Número de sugestões", examples=[5]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/chunks",
    summary="Buscar nos chunks de documentos",
    description="Busca full-text dentro dos chunks (trechos) dos documentos. "
    "Útil para encontrar passagens específicas em documentos longos.",
    response_model=SearchResponse,
)
async def search_documentos_chunks(
    q: str = Query(..., description="Termo de busca nos chunks", examples=["prazo de inscrição"]),
    page: int = Query(1, ge=1, description="Página", examples=[1]),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página", examples=[20]),
    document_id: Optional[str] = Query(None, description="Filtrar chunks de um documento específico", examples=["abc123"]),
):
    raise HTTPException(status_code=501, detail="Not implemented")
