"""
Chat routes — RAG-powered conversational interface.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.api.dependencies import verify_token
from app.api.models.requests import (
    AddArtefatoToSessionRequest,
    AddDocumentoToSessionRequest,
    ChatMessageRequest,
)
from app.api.models.responses import (
    APIResponse,
    ChatMessageResponse,
    ErrorResponse,
    PaginatedResponse,
)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(verify_token)],
)


@router.post(
    "/message",
    summary="Enviar mensagem ao chat RAG",
    description="Envia uma mensagem do usuário e recebe uma resposta gerada por IA "
    "com base nos documentos do contexto da sessão (RAG). "
    "Cria a sessão automaticamente se não existir.",
    response_model=ChatMessageResponse,
    responses={400: {"model": ErrorResponse, "description": "Requisição inválida"}},
)
async def send_message(body: ChatMessageRequest):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/sessions/{session_id}",
    summary="Obter sessão de chat",
    description="Retorna uma sessão de chat com todo o histórico de mensagens e documentos no contexto.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Sessão não encontrada"}},
)
async def get_session(
    session_id: str = Path(..., description="ID da sessão de chat", examples=["session-uuid-123"]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/sessions",
    summary="Listar sessões de chat",
    description="Lista todas as sessões de chat com paginação, ordenadas por última atividade.",
    response_model=PaginatedResponse,
)
async def list_sessions(
    page: int = Query(1, ge=1, description="Página", examples=[1]),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página", examples=[20]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete(
    "/sessions/{session_id}",
    summary="Excluir sessão de chat",
    description="Remove permanentemente uma sessão de chat e todo seu histórico.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Sessão não encontrada"}},
)
async def delete_session(
    session_id: str = Path(..., description="ID da sessão a excluir", examples=["session-uuid-123"]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/sessions/{session_id}/add-documento",
    summary="Adicionar documento ao contexto da sessão",
    description="Adiciona um documento institucional ao contexto da sessão de chat "
    "para que a IA considere seu conteúdo nas respostas.",
    response_model=APIResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Sessão ou documento não encontrado"},
    },
)
async def add_documento_to_session(
    session_id: str = Path(..., description="ID da sessão", examples=["session-uuid-123"]),
    body: AddDocumentoToSessionRequest = ...,
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post(
    "/sessions/{session_id}/add-artefato",
    summary="Adicionar artefato ao contexto da sessão",
    description="Adiciona um artefato didático ao contexto da sessão de chat "
    "para que a IA considere seu conteúdo nas respostas.",
    response_model=APIResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Sessão ou artefato não encontrado"},
    },
)
async def add_artefato_to_session(
    session_id: str = Path(..., description="ID da sessão", examples=["session-uuid-123"]),
    body: AddArtefatoToSessionRequest = ...,
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete(
    "/sessions/{session_id}/context",
    summary="Limpar contexto da sessão",
    description="Remove todos os documentos e artefatos do contexto da sessão de chat. "
    "O histórico de mensagens é preservado.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Sessão não encontrada"}},
)
async def clear_session_context(
    session_id: str = Path(..., description="ID da sessão", examples=["session-uuid-123"]),
):
    raise HTTPException(status_code=501, detail="Not implemented")
