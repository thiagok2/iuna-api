"""
CRUD routes for documentos (institutional documents).
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile

from app.api.dependencies import verify_token
from app.api.models.requests import MetadataUpdate
from app.api.models.responses import APIResponse, ErrorResponse, PaginatedResponse

router = APIRouter(
    prefix="/documentos",
    tags=["documentos"],
    dependencies=[Depends(verify_token)],
)


@router.post(
    "/upload",
    summary="Upload de documento (PDF)",
    description="Faz upload de um arquivo PDF e indexa no Elasticsearch com metadados opcionais. "
    "O texto é extraído automaticamente do PDF.",
    response_model=APIResponse,
    responses={400: {"model": ErrorResponse, "description": "Arquivo inválido ou não-PDF"}},
)
async def upload_documento(
    file: UploadFile = File(..., description="Arquivo PDF para upload"),
    titulo: Optional[str] = Form(None, description="Título do documento (pode ser inferido do PDF)", examples=["Edital 01/2024"]),
    ementa: Optional[str] = Form(None, description="Ementa ou resumo curto do documento"),
    tipo_doc: Optional[str] = Form(None, description="Tipo do documento", examples=["edital"]),
    ano: Optional[int] = Form(None, description="Ano de publicação", examples=[2024]),
    publico: bool = Form(True, description="Se o documento é público"),
    tags: Optional[str] = Form(None, description="Tags separadas por vírgula", examples=["educação,seletivo"]),
    orgao: Optional[str] = Form(None, description="Órgão emissor", examples=["IFAL"]),
    esfera: Optional[str] = Form(None, description="Esfera administrativa (federal, estadual, municipal)", examples=["federal"]),
    fonte: Optional[str] = Form(None, description="Fonte/origem do documento", examples=["diario_oficial"]),
    categoria: Optional[str] = Form(None, description="Categoria: institucional | didatico | projeto", examples=["institucional"]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/{document_id}",
    summary="Buscar documento por ID",
    description="Retorna os metadados completos e texto de um documento pelo seu ID no Elasticsearch.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Documento não encontrado"}},
)
async def get_documento(
    document_id: str = Path(..., description="ID do documento no Elasticsearch", examples=["abc123"]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/by-filename/{filename}",
    summary="Buscar documento por nome do arquivo",
    description="Retorna um documento pelo nome original do arquivo PDF.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Documento não encontrado"}},
)
async def get_documento_by_filename(
    filename: str = Path(..., description="Nome do arquivo PDF", examples=["edital_01_2024.pdf"]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get(
    "/",
    summary="Listar documentos",
    description="Lista documentos com paginação. Retorna metadados sem o texto completo.",
    response_model=PaginatedResponse,
)
async def list_documentos(
    page: int = Query(1, ge=1, description="Número da página", examples=[1]),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página", examples=[20]),
    tipo_doc: Optional[str] = Query(None, description="Filtrar por tipo de documento", examples=["edital"]),
    orgao: Optional[str] = Query(None, description="Filtrar por órgão", examples=["IFAL"]),
    esfera: Optional[str] = Query(None, description="Filtrar por esfera", examples=["federal"]),
    ano: Optional[int] = Query(None, description="Filtrar por ano", examples=[2024]),
    publico: Optional[bool] = Query(None, description="Filtrar por visibilidade pública/privada"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoria", examples=["institucional"]),
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.patch(
    "/{document_id}",
    summary="Atualizar metadados do documento",
    description="Atualiza parcialmente os metadados de um documento. Campos não enviados permanecem inalterados.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Documento não encontrado"}},
)
async def update_documento(
    document_id: str = Path(..., description="ID do documento", examples=["abc123"]),
    body: MetadataUpdate = ...,
):
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete(
    "/{document_id}",
    summary="Excluir documento",
    description="Remove um documento e todos os seus chunks associados do Elasticsearch.",
    response_model=APIResponse,
    responses={404: {"model": ErrorResponse, "description": "Documento não encontrado"}},
)
async def delete_documento(
    document_id: str = Path(..., description="ID do documento a excluir", examples=["abc123"]),
):
    raise HTTPException(status_code=501, detail="Not implemented")
