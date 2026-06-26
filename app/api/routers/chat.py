"""
Chat routes — RAG-powered conversational interface.
"""

from fastapi import APIRouter, Depends, Path, Query

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
from app.clients.es_client import es_client
from app.clients.rasa_client import rasa_client
from app.providers.factory import get_embedding_provider, get_llm_provider
from app.services.chat import ChatService

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(verify_token)],
)


def _svc() -> ChatService:
    return ChatService(
        es_client=es_client,
        llm_provider=get_llm_provider(),
        embedding_provider=get_embedding_provider(),
        rasa_client=rasa_client,
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
    svc = _svc()
    result = await svc.handle_message(
        message=body.message,
        session_id=body.session_id,
        source_type=body.source_type,
    )
    return ChatMessageResponse(data=result)


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
    svc = _svc()
    session = await svc.get_session(session_id)
    return APIResponse(data=session)


@router.get(
    "/sessions",
    summary="Listar sessões de chat",
    description="Lista todas as sessões de chat ativas (expires_at > now), ordenadas por última atividade.",
    response_model=PaginatedResponse,
)
async def list_sessions(
    page: int = Query(1, ge=1, description="Página", examples=[1]),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página", examples=[20]),
):
    svc = _svc()
    result = await svc.list_sessions(page=page, page_size=page_size)
    return PaginatedResponse(
        data=result["sessions"],
        meta={
            "page": result["page"],
            "page_size": result["page_size"],
            "total": result["total"],
        },
    )


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
    svc = _svc()
    await svc.delete_session(session_id)
    return APIResponse(data={"session_id": session_id, "deleted": True})


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
    svc = _svc()
    result = await svc.add_document_to_context(
        session_id=session_id,
        document_id=body.document_id,
    )
    return APIResponse(data=result)


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
    svc = _svc()
    result = await svc.add_artefato_to_context(
        session_id=session_id,
        artefato_id=body.artefato_id,
    )
    return APIResponse(data=result)


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
    svc = _svc()
    result = await svc.clear_context(session_id)
    return APIResponse(data=result)
