"""
Enrichment routes for documentos and artefatos.

Handles: summary generation, vectorization, entity extraction,
keyword extraction, chunking, and full enrichment pipeline.
"""

from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.dependencies import verify_token
from app.api.models.requests import ChunkingRequest, EnrichAllRequest, EnrichmentRequest
from app.api.models.responses import (
    APIResponse,
    EnrichmentStatusResponse,
    ErrorResponse,
)

router = APIRouter(
    tags=["enrichment"],
    dependencies=[Depends(verify_token)],
)

# ---------------------------------------------------------------------------
# Documentos enrichment
# ---------------------------------------------------------------------------


@router.post(
    "/documentos/summary/generate",
    summary="Gerar resumo de documento",
    description="Gera um resumo usando IA (LLM) para o documento especificado. "
    "O resumo é salvo no campo `summary` do documento.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Documento não encontrado"}},
)
async def generate_documento_summary(body: EnrichmentRequest):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/documentos/vectorization/generate",
    summary="Gerar embedding de documento",
    description="Gera o vetor de embedding para o documento usando modelo de embeddings. "
    "Necessário para buscas por similaridade semântica.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Documento não encontrado"}},
)
async def generate_documento_vectorization(body: EnrichmentRequest):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/documentos/entities/extract",
    summary="Extrair entidades nomeadas de documento",
    description="Extrai entidades nomeadas (pessoas, organizações, locais, datas) do documento usando NLP.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Documento não encontrado"}},
)
async def extract_documento_entities(body: EnrichmentRequest):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/documentos/keywords/extract",
    summary="Extrair keywords de documento",
    description="Extrai palavras-chave representativas do documento usando TF-IDF ou LLM.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Documento não encontrado"}},
)
async def extract_documento_keywords(body: EnrichmentRequest):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/documentos/chunking/generate",
    summary="Gerar chunks de documento",
    description="Divide o texto do documento em chunks menores com sobreposição configurável. "
    "Necessário para busca granular e RAG.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Documento não encontrado"}},
)
async def generate_documento_chunking(body: ChunkingRequest):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/documentos/{document_id}/enrich",
    summary="Pipeline completo de enriquecimento de documento",
    description="Executa todas (ou um subconjunto) das operações de enriquecimento: "
    "summary, entities, keywords, vectorization, chunking.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Documento não encontrado"}},
)
async def enrich_documento(
    document_id: str = Path(..., description="ID do documento", examples=["abc123"]),
    body: EnrichAllRequest = EnrichAllRequest(),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/documentos/{document_id}/enrichment-status",
    summary="Status de enriquecimento do documento",
    description="Retorna quais operações de enriquecimento já foram executadas para este documento.",
    response_model=EnrichmentStatusResponse,
    responses={404: {"model": ErrorResponse, "description": "Documento não encontrado"}},
)
async def get_documento_enrichment_status(
    document_id: str = Path(..., description="ID do documento", examples=["abc123"]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


# ---------------------------------------------------------------------------
# Artefatos enrichment
# ---------------------------------------------------------------------------


@router.post(
    "/artefatos/summary/generate",
    summary="Gerar resumo de artefato",
    description="Gera um resumo usando IA (LLM) para o artefato especificado.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Artefato não encontrado"}},
)
async def generate_artefato_summary(body: EnrichmentRequest):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/artefatos/vectorization/generate",
    summary="Gerar embedding de artefato",
    description="Gera o vetor de embedding para o artefato usando modelo de embeddings.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Artefato não encontrado"}},
)
async def generate_artefato_vectorization(body: EnrichmentRequest):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/artefatos/entities/extract",
    summary="Extrair entidades nomeadas de artefato",
    description="Extrai entidades nomeadas do artefato usando NLP.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Artefato não encontrado"}},
)
async def extract_artefato_entities(body: EnrichmentRequest):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/artefatos/keywords/extract",
    summary="Extrair keywords de artefato",
    description="Extrai palavras-chave representativas do artefato.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Artefato não encontrado"}},
)
async def extract_artefato_keywords(body: EnrichmentRequest):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/artefatos/chunking/generate",
    summary="Gerar chunks de artefato",
    description="Divide o texto do artefato em chunks menores com sobreposição configurável.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Artefato não encontrado"}},
)
async def generate_artefato_chunking(body: ChunkingRequest):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/artefatos/{artefato_id}/enrich",
    summary="Pipeline completo de enriquecimento de artefato",
    description="Executa todas (ou um subconjunto) das operações de enriquecimento no artefato.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Artefato não encontrado"}},
)
async def enrich_artefato(
    artefato_id: str = Path(..., description="ID do artefato", examples=["art-456"]),
    body: EnrichAllRequest = EnrichAllRequest(),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/artefatos/{artefato_id}/enrichment-status",
    summary="Status de enriquecimento do artefato",
    description="Retorna quais operações de enriquecimento já foram executadas para este artefato.",
    response_model=EnrichmentStatusResponse,
    responses={404: {"model": ErrorResponse, "description": "Artefato não encontrado"}},
)
async def get_artefato_enrichment_status(
    artefato_id: str = Path(..., description="ID do artefato", examples=["art-456"]),
):
    raise HTTPException(status_code=501, detail="Not implemented")
