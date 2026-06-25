"""
Scoring routes — popularity/relevance scoring for documents and artefatos.
"""

from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.dependencies import verify_token
from app.api.models.requests import ScoreRequest
from app.api.models.responses import APIResponse, ErrorResponse
from app.clients.es_client import es_client
from app.config import settings
from app.core.exceptions import NotFoundError
from app.services.scoring_service import ScoringService

router = APIRouter(
    tags=["scoring"],
    dependencies=[Depends(verify_token)],
)

_DOC_INDEX = lambda: settings.index_documentos_ifal_v2  # noqa: E731
_ART_INDEX = lambda: settings.index_artefatos  # noqa: E731


def _svc() -> ScoringService:
    return ScoringService(es_client)


@router.post(
    "/documentos/{document_id}/score",
    summary="Registrar interação com documento",
    description="Incrementa o score de popularidade/relevância de um documento. "
    "Ações suportadas: click, add_to_chat, download, share.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Documento não encontrado"}},
)
async def score_documento(
    document_id: str = Path(..., description="ID do documento", examples=["abc123"]),
    body: ScoreRequest = ...,
):
    try:
        new_score = await _svc().increment_score(_DOC_INDEX(), document_id, body.action, "ato")
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return APIResponse(data={"popularity_score": new_score})


@router.post(
    "/artefatos/{artefato_id}/score",
    summary="Registrar interação com artefato",
    description="Incrementa o score de popularidade/relevância de um artefato. "
    "Ações suportadas: click, add_to_chat, download, share.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Artefato não encontrado"}},
)
async def score_artefato(
    artefato_id: str = Path(..., description="ID do artefato", examples=["art-456"]),
    body: ScoreRequest = ...,
):
    try:
        new_score = await _svc().increment_score(_ART_INDEX(), artefato_id, body.action, "artefato")
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return APIResponse(data={"popularity_score": new_score})
