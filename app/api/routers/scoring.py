"""
Scoring routes — popularity/relevance scoring for documents and artefatos.
"""

from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.dependencies import verify_token
from app.api.models.requests import ScoreRequest
from app.api.models.responses import APIResponse, ErrorResponse

router = APIRouter(
    tags=["scoring"],
    dependencies=[Depends(verify_token)],
)


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
    raise HTTPException(status_code=501, detail="Not implemented")


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
    raise HTTPException(status_code=501, detail="Not implemented")
