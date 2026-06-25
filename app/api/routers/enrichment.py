"""
Enrichment routes for documentos and artefatos.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.dependencies import verify_token
from app.api.models.requests import ChunkingRequest, EnrichAllRequest, EnrichmentRequest
from app.api.models.responses import APIResponse, EnrichmentStatusResponse, ErrorResponse
from app.clients.es_client import es_client
from app.config import settings
from app.core.exceptions import NotFoundError, ServiceUnavailableError, ValidationError
from app.providers.factory import get_llm_provider
from app.services.enrichment import EnrichmentService

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["enrichment"],
    dependencies=[Depends(verify_token)],
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DOC_INDEX = lambda: settings.index_documentos_ifal_v2  # noqa: E731
_DOC_CHUNKS = lambda: settings.index_documentos_ifal_v2_chunks  # noqa: E731
_ART_INDEX = lambda: settings.index_artefatos  # noqa: E731
_ART_CHUNKS = lambda: settings.index_artefatos_chunks  # noqa: E731


def _svc() -> EnrichmentService:
    return EnrichmentService(es_client, get_llm_provider())


async def _resolve_doc_id(body: EnrichmentRequest, index: str) -> str:
    """Resolve document_id from request (by id or filename)."""
    if body.document_id:
        return body.document_id
    if body.filename:
        result = await es_client.search(
            index=index,
            body={"query": {"term": {"filename.keyword": body.filename}}, "size": 1},
        )
        hits = result.get("hits", {}).get("hits", [])
        if not hits:
            raise HTTPException(status_code=404, detail=f"Documento não encontrado: {body.filename}")
        return hits[0]["_id"]
    if not body.text:
        raise HTTPException(status_code=422, detail="Forneça document_id, filename ou text")
    return ""  # text-only mode


def _handle_exc(exc: Exception):
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValidationError):
        raise HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, ServiceUnavailableError):
        raise HTTPException(status_code=503, detail=str(exc))
    raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Documentos enrichment
# ---------------------------------------------------------------------------


@router.post(
    "/documentos/summary/generate",
    summary="Gerar resumo de documento",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def generate_documento_summary(body: EnrichmentRequest):
    index = _DOC_INDEX()
    try:
        if body.text and not body.document_id and not body.filename:
            summary = await _svc().llm.generate_summary(body.text)
            return APIResponse(data={"resumo": summary})

        doc_id = await _resolve_doc_id(body, index)
        summary = await _svc().enrich_summary(index=index, doc_id=doc_id, root="ato")
        return APIResponse(data={"resumo": summary}, meta={"index": index})
    except HTTPException:
        raise
    except Exception as exc:
        _handle_exc(exc)


@router.post(
    "/documentos/vectorization/generate",
    summary="Gerar embedding de documento",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def generate_documento_vectorization(body: EnrichmentRequest):
    index = _DOC_INDEX()
    try:
        doc_id = await _resolve_doc_id(body, index)
        vector = await _svc().enrich_vector(index=index, doc_id=doc_id, root="ato")
        return APIResponse(data={"dims": len(vector)}, meta={"index": index})
    except HTTPException:
        raise
    except Exception as exc:
        _handle_exc(exc)


@router.post(
    "/documentos/entities/extract",
    summary="Extrair entidades nomeadas de documento",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def extract_documento_entities(body: EnrichmentRequest):
    index = _DOC_INDEX()
    try:
        if body.text and not body.document_id and not body.filename:
            entities = await _svc().llm.extract_entities(body.text)
            return APIResponse(data={"entidades": entities})

        doc_id = await _resolve_doc_id(body, index)
        entities = await _svc().enrich_entities(index=index, doc_id=doc_id, root="ato")
        return APIResponse(data={"entidades": entities}, meta={"index": index})
    except HTTPException:
        raise
    except Exception as exc:
        _handle_exc(exc)


@router.post(
    "/documentos/keywords/extract",
    summary="Extrair keywords de documento",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def extract_documento_keywords(body: EnrichmentRequest):
    index = _DOC_INDEX()
    try:
        if body.text and not body.document_id and not body.filename:
            keywords = await _svc().llm.extract_keywords(body.text)
            return APIResponse(data={"keywords": keywords})

        doc_id = await _resolve_doc_id(body, index)
        keywords = await _svc().enrich_keywords(index=index, doc_id=doc_id, root="ato")
        return APIResponse(data={"keywords": keywords}, meta={"index": index})
    except HTTPException:
        raise
    except Exception as exc:
        _handle_exc(exc)


@router.post(
    "/documentos/chunking/generate",
    summary="Gerar chunks de documento",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def generate_documento_chunking(body: ChunkingRequest):
    if body.chunk_size < 3000:
        raise HTTPException(status_code=422, detail="chunk_size mínimo é 3000")

    index = _DOC_INDEX()
    try:
        doc_id = await _resolve_doc_id(
            EnrichmentRequest(document_id=body.document_id, filename=body.filename), index
        )
        total = await _svc().enrich_chunks(
            index=index,
            chunks_index=_DOC_CHUNKS(),
            doc_id=doc_id,
            root="ato",
            chunk_size=body.chunk_size,
            overlap=body.chunk_overlap,
        )
        skipped = total == 0
        return APIResponse(
            data={"total_chunks": total, "skipped": skipped, **({"reason": "content < 10000 chars"} if skipped else {})},
            meta={"index": index},
        )
    except HTTPException:
        raise
    except Exception as exc:
        _handle_exc(exc)


@router.post(
    "/documentos/{document_id}/enrich",
    summary="Pipeline completo de enriquecimento de documento",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def enrich_documento(
    document_id: str = Path(..., description="ID do documento", examples=["abc123"]),
    body: EnrichAllRequest = EnrichAllRequest(),
):
    index = _DOC_INDEX()
    try:
        ops = set(body.operations) if body.operations else {"entities", "keywords", "summary", "vectorization", "chunking"}
        svc = _svc()
        result = {}

        if "entities" in ops:
            result["entities_count"] = len(await svc.enrich_entities(index, document_id, "ato"))
        if "keywords" in ops:
            result["keywords_count"] = len(await svc.enrich_keywords(index, document_id, "ato"))
        if "summary" in ops:
            result["summary_length"] = len(await svc.enrich_summary(index, document_id, "ato"))
        if "vectorization" in ops:
            result["vector_dims"] = len(await svc.enrich_vector(index, document_id, "ato"))
        if "chunking" in ops:
            result["total_chunks"] = await svc.enrich_chunks(index, _DOC_CHUNKS(), document_id, "ato")

        return APIResponse(data=result, meta={"index": index})
    except HTTPException:
        raise
    except Exception as exc:
        _handle_exc(exc)


@router.get(
    "/documentos/{document_id}/enrichment-status",
    summary="Status de enriquecimento do documento",
    response_model=EnrichmentStatusResponse,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def get_documento_enrichment_status(
    document_id: str = Path(..., description="ID do documento", examples=["abc123"]),
):
    try:
        status = await _svc().get_enrichment_status(_DOC_INDEX(), document_id, "ato")
        return EnrichmentStatusResponse(data=status)
    except Exception as exc:
        _handle_exc(exc)


# ---------------------------------------------------------------------------
# Artefatos enrichment
# ---------------------------------------------------------------------------


@router.post(
    "/artefatos/summary/generate",
    summary="Gerar resumo de artefato",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def generate_artefato_summary(body: EnrichmentRequest):
    index = _ART_INDEX()
    try:
        if body.text and not body.document_id and not body.filename:
            summary = await _svc().llm.generate_summary(body.text)
            return APIResponse(data={"resumo": summary})

        doc_id = await _resolve_doc_id(body, index)
        summary = await _svc().enrich_summary(index=index, doc_id=doc_id, root="artefato")
        return APIResponse(data={"resumo": summary}, meta={"index": index})
    except HTTPException:
        raise
    except Exception as exc:
        _handle_exc(exc)


@router.post(
    "/artefatos/vectorization/generate",
    summary="Gerar embedding de artefato",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def generate_artefato_vectorization(body: EnrichmentRequest):
    index = _ART_INDEX()
    try:
        doc_id = await _resolve_doc_id(body, index)
        vector = await _svc().enrich_vector(index=index, doc_id=doc_id, root="artefato")
        return APIResponse(data={"dims": len(vector)}, meta={"index": index})
    except HTTPException:
        raise
    except Exception as exc:
        _handle_exc(exc)


@router.post(
    "/artefatos/entities/extract",
    summary="Extrair entidades nomeadas de artefato",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def extract_artefato_entities(body: EnrichmentRequest):
    index = _ART_INDEX()
    try:
        if body.text and not body.document_id and not body.filename:
            entities = await _svc().llm.extract_entities(body.text)
            return APIResponse(data={"entidades": entities})

        doc_id = await _resolve_doc_id(body, index)
        entities = await _svc().enrich_entities(index=index, doc_id=doc_id, root="artefato")
        return APIResponse(data={"entidades": entities}, meta={"index": index})
    except HTTPException:
        raise
    except Exception as exc:
        _handle_exc(exc)


@router.post(
    "/artefatos/keywords/extract",
    summary="Extrair keywords de artefato",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def extract_artefato_keywords(body: EnrichmentRequest):
    index = _ART_INDEX()
    try:
        if body.text and not body.document_id and not body.filename:
            keywords = await _svc().llm.extract_keywords(body.text)
            return APIResponse(data={"keywords": keywords})

        doc_id = await _resolve_doc_id(body, index)
        keywords = await _svc().enrich_keywords(index=index, doc_id=doc_id, root="artefato")
        return APIResponse(data={"keywords": keywords}, meta={"index": index})
    except HTTPException:
        raise
    except Exception as exc:
        _handle_exc(exc)


@router.post(
    "/artefatos/chunking/generate",
    summary="Gerar chunks de artefato",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def generate_artefato_chunking(body: ChunkingRequest):
    if body.chunk_size < 3000:
        raise HTTPException(status_code=422, detail="chunk_size mínimo é 3000")

    index = _ART_INDEX()
    try:
        doc_id = await _resolve_doc_id(
            EnrichmentRequest(document_id=body.document_id, filename=body.filename), index
        )
        total = await _svc().enrich_chunks(
            index=index,
            chunks_index=_ART_CHUNKS(),
            doc_id=doc_id,
            root="artefato",
            chunk_size=body.chunk_size,
            overlap=body.chunk_overlap,
        )
        skipped = total == 0
        return APIResponse(
            data={"total_chunks": total, "skipped": skipped, **({"reason": "content < 10000 chars"} if skipped else {})},
            meta={"index": index},
        )
    except HTTPException:
        raise
    except Exception as exc:
        _handle_exc(exc)


@router.post(
    "/artefatos/{artefato_id}/enrich",
    summary="Pipeline completo de enriquecimento de artefato",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def enrich_artefato(
    artefato_id: str = Path(..., description="ID do artefato", examples=["art-456"]),
    body: EnrichAllRequest = EnrichAllRequest(),
):
    index = _ART_INDEX()
    try:
        ops = set(body.operations) if body.operations else {"entities", "keywords", "summary", "vectorization", "chunking"}
        svc = _svc()
        result = {}

        if "entities" in ops:
            result["entities_count"] = len(await svc.enrich_entities(index, artefato_id, "artefato"))
        if "keywords" in ops:
            result["keywords_count"] = len(await svc.enrich_keywords(index, artefato_id, "artefato"))
        if "summary" in ops:
            result["summary_length"] = len(await svc.enrich_summary(index, artefato_id, "artefato"))
        if "vectorization" in ops:
            result["vector_dims"] = len(await svc.enrich_vector(index, artefato_id, "artefato"))
        if "chunking" in ops:
            result["total_chunks"] = await svc.enrich_chunks(index, _ART_CHUNKS(), artefato_id, "artefato")

        return APIResponse(data=result, meta={"index": index})
    except HTTPException:
        raise
    except Exception as exc:
        _handle_exc(exc)


@router.get(
    "/artefatos/{artefato_id}/enrichment-status",
    summary="Status de enriquecimento do artefato",
    response_model=EnrichmentStatusResponse,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def get_artefato_enrichment_status(
    artefato_id: str = Path(..., description="ID do artefato", examples=["art-456"]),
):
    try:
        status = await _svc().get_enrichment_status(_ART_INDEX(), artefato_id, "artefato")
        return EnrichmentStatusResponse(data=status)
    except Exception as exc:
        _handle_exc(exc)
