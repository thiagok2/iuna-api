"""
Search routes for artefatos.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.api.dependencies import verify_token
from app.api.models.responses import APIResponse, SearchResponse

router = APIRouter(
    prefix="/artefatos/search",
    tags=["artefatos - search"],
    dependencies=[Depends(verify_token)],
)


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
):
    raise HTTPException(status_code=501, detail="Not implemented")


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
    raise HTTPException(status_code=501, detail="Not implemented")


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
    raise HTTPException(status_code=501, detail="Not implemented")


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
    raise HTTPException(status_code=501, detail="Not implemented")


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
    raise HTTPException(status_code=501, detail="Not implemented")


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
    raise HTTPException(status_code=501, detail="Not implemented")
