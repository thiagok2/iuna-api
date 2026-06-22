"""
CRUD routes for artefatos (teaching artifacts, plans, etc.).
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile

from app.api.dependencies import verify_token
from app.api.models.requests import ArtefatoMetadataUpdate
from app.api.models.responses import APIResponse, ErrorResponse, PaginatedResponse

router = APIRouter(
    prefix="/artefatos",
    tags=["artefatos"],
    dependencies=[Depends(verify_token)],
)


@router.post(
    "/upload",
    summary="Upload de artefato (PDF)",
    description="Faz upload de um artefato didático (plano de ensino, apostila, livro) em formato PDF. "
    "O texto é extraído automaticamente.",
    response_model=APIResponse,
    responses={400: {"model": ErrorResponse, "description": "Arquivo inválido ou não-PDF"}},
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
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/{artefato_id}",
    summary="Buscar artefato por ID",
    description="Retorna os metadados completos e texto de um artefato pelo seu ID.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Artefato não encontrado"}},
)
async def get_artefato(
    artefato_id: str = Path(..., description="ID do artefato no Elasticsearch", examples=["art-456"]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/by-filename/{filename}",
    summary="Buscar artefato por nome do arquivo",
    description="Retorna um artefato pelo nome original do arquivo PDF.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Artefato não encontrado"}},
)
async def get_artefato_by_filename(
    filename: str = Path(..., description="Nome do arquivo PDF", examples=["plano_ensino_prog1.pdf"]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/",
    summary="Listar artefatos",
    description="Lista artefatos didáticos com paginação e filtros opcionais.",
    response_model=PaginatedResponse,
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
    raise HTTPException(status_code=501, detail="Not implemented")


@router.patch(
    "/{artefato_id}",
    summary="Atualizar metadados do artefato",
    description="Atualiza parcialmente os metadados de um artefato. Campos não enviados permanecem inalterados.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Artefato não encontrado"}},
)
async def update_artefato(
    artefato_id: str = Path(..., description="ID do artefato", examples=["art-456"]),
    body: ArtefatoMetadataUpdate = ...,
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete(
    "/{artefato_id}",
    summary="Excluir artefato",
    description="Remove um artefato e todos os seus chunks associados do Elasticsearch.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Artefato não encontrado"}},
)
async def delete_artefato(
    artefato_id: str = Path(..., description="ID do artefato a excluir", examples=["art-456"]),
):
    raise HTTPException(status_code=501, detail="Not implemented")
