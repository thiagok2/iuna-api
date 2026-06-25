"""
CRUD routes for artefatos (teaching artifacts, plans, etc.).
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile

from app.api.dependencies import verify_token
from app.api.models.requests import ArtefatoMetadataUpdate
from app.api.models.responses import APIResponse, ErrorResponse, PaginatedResponse
from app.clients.es_client import es_client
from app.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ServiceUnavailableError, ValidationError
from app.services.artefatos_crud import ArtefatosCrudService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/artefatos",
    tags=["artefatos"],
    dependencies=[Depends(verify_token)],
)


def _get_service() -> ArtefatosCrudService:
    return ArtefatosCrudService(es_client)


@router.post(
    "/upload",
    summary="Upload de artefato (PDF)",
    description="Faz upload de um artefato didático (plano de ensino, apostila, livro) em formato PDF. "
    "O texto é extraído automaticamente.",
    response_model=APIResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Arquivo inválido ou não-PDF"},
        409: {"model": ErrorResponse, "description": "Artefato já existe"},
        503: {"model": ErrorResponse, "description": "Elasticsearch indisponível"},
    },
)
async def upload_artefato(
    file: UploadFile = File(..., description="Arquivo PDF do artefato"),
    titulo: Optional[str] = Form(None, description="Título do artefato", examples=["Introdução à Programação"]),
    tipo: Optional[str] = Form(None, description="Tipo: livro, plano_ensino, apostila, artigo", examples=["livro"]),
    disciplina: Optional[str] = Form(None, description="Disciplina associada", examples=["Programação I"]),
    curso: Optional[str] = Form(None, description="Curso associado", examples=["Ciência da Computação"]),
    autor: Optional[str] = Form(None, description="Autor do artefato", examples=["Prof. João"]),
    ano: Optional[int] = Form(None, description="Ano de publicação", examples=[2024]),
    publico: bool = Form(True, description="Se o artefato é público"),
    tags: Optional[str] = Form(None, description="Tags separadas por vírgula", examples=["programação,python,algoritmos"]),
    uploaded_by: Optional[str] = Form(None, description="Quem fez upload", examples=["admin"]),
    force: bool = Form(False, description="Sobrescrever artefato existente com mesmo filename"),
):
    # Validate file
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos")

    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    # Parse tags from comma-separated string
    parsed_tags = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    metadata = {
        "titulo": titulo,
        "tipo": tipo,
        "disciplina": disciplina,
        "curso": curso,
        "autor": autor,
        "ano": ano,
        "publico": publico,
        "tags": parsed_tags,
        "uploaded_by": uploaded_by or "system",
    }

    service = _get_service()
    result = await service.upload(file_content, file.filename, metadata, force=force)
    return APIResponse(data=result, meta={"index": settings.index_artefatos})


@router.get(
    "/{artefato_id}",
    summary="Buscar artefato por ID",
    description="Retorna os metadados completos e texto de um artefato pelo seu ID.",
    response_model=APIResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Artefato não encontrado"},
        503: {"model": ErrorResponse, "description": "Elasticsearch indisponível"},
    },
)
async def get_artefato(
    artefato_id: str = Path(..., description="ID do artefato no Elasticsearch", examples=["art-456"]),
):
    service = _get_service()
    doc = await service.get_by_id(artefato_id)
    return APIResponse(data=doc, meta={"index": settings.index_artefatos})


@router.get(
    "/by-filename/{filename}",
    summary="Buscar artefato por nome do arquivo",
    description="Retorna um artefato pelo nome original do arquivo PDF.",
    response_model=APIResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Artefato não encontrado"},
        503: {"model": ErrorResponse, "description": "Elasticsearch indisponível"},
    },
)
async def get_artefato_by_filename(
    filename: str = Path(..., description="Nome do arquivo PDF", examples=["plano_ensino_prog1.pdf"]),
):
    service = _get_service()
    doc = await service.get_by_filename(filename)
    return APIResponse(data=doc, meta={"index": settings.index_artefatos})


@router.get(
    "/",
    summary="Listar artefatos",
    description="Lista artefatos didáticos com paginação e filtros opcionais.",
    response_model=PaginatedResponse,
    responses={503: {"model": ErrorResponse, "description": "Elasticsearch indisponível"}},
)
async def list_artefatos(
    page: int = Query(1, ge=1, description="Número da página", examples=[1]),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página", examples=[20]),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo de artefato", examples=["livro"]),
    disciplina: Optional[str] = Query(None, description="Filtrar por disciplina", examples=["Programação I"]),
    curso: Optional[str] = Query(None, description="Filtrar por curso", examples=["Ciência da Computação"]),
    autor: Optional[str] = Query(None, description="Filtrar por autor", examples=["Prof. João"]),
    ano: Optional[int] = Query(None, description="Filtrar por ano", examples=[2024]),
    publico: Optional[bool] = Query(None, description="Filtrar por visibilidade"),
):
    filters = {}
    if tipo:
        filters["tipo"] = tipo
    if disciplina:
        filters["disciplina"] = disciplina
    if curso:
        filters["curso"] = curso
    if autor:
        filters["uploaded_by"] = autor
    if ano:
        filters["ano"] = ano
    if publico is not None:
        filters["publico"] = publico

    service = _get_service()
    result = await service.list_all(page=page, page_size=page_size, filters=filters if filters else None)

    hits = result.get("hits", {})
    total = hits.get("total", {}).get("value", 0)
    items = [hit.get("_source", {}) | {"_id": hit["_id"]} for hit in hits.get("hits", [])]
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return PaginatedResponse(
        data=items,
        meta={"page": page, "page_size": page_size, "total": total, "total_pages": total_pages, "index": settings.index_artefatos},
    )


@router.patch(
    "/{artefato_id}",
    summary="Atualizar metadados do artefato",
    description="Atualiza parcialmente os metadados de um artefato. Campos não enviados permanecem inalterados.",
    response_model=APIResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Artefato não encontrado"},
        503: {"model": ErrorResponse, "description": "Elasticsearch indisponível"},
    },
)
async def update_artefato(
    artefato_id: str = Path(..., description="ID do artefato", examples=["art-456"]),
    body: ArtefatoMetadataUpdate = ...,
):
    fields = body.model_dump(exclude_unset=True)
    service = _get_service()
    result = await service.update_metadata(artefato_id, fields)
    return APIResponse(data=result, meta={"index": settings.index_artefatos})


@router.delete(
    "/{artefato_id}",
    summary="Excluir artefato",
    description="Remove um artefato e todos os seus chunks associados do Elasticsearch.",
    response_model=APIResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Artefato não encontrado"},
        503: {"model": ErrorResponse, "description": "Elasticsearch indisponível"},
    },
)
async def delete_artefato(
    artefato_id: str = Path(..., description="ID do artefato a excluir", examples=["art-456"]),
):
    service = _get_service()
    result = await service.delete(artefato_id)
    return APIResponse(data=result, meta={"index": settings.index_artefatos})
