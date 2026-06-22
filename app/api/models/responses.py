"""
Response models for the IUNA API — used as response_model in route decorators.
"""

from pydantic import BaseModel, Field
from typing import Any, Optional


class APIResponse(BaseModel):
    """Resposta padrão de sucesso da API."""

    success: bool = Field(True, examples=[True])
    data: Optional[Any] = Field(None, description="Payload de dados da resposta")
    meta: Optional[dict] = Field(None, description="Metadados (paginação, contagens, etc.)")


class ErrorResponse(BaseModel):
    """Resposta padrão de erro da API."""

    success: bool = Field(False, examples=[False])
    error: str = Field(..., description="Mensagem de erro", examples=["Not found"])
    request_id: Optional[str] = Field(
        None, description="ID da requisição para rastreamento", examples=["req-uuid-123"]
    )


class PaginatedResponse(BaseModel):
    """Resposta paginada."""

    success: bool = Field(True, examples=[True])
    data: list[Any] = Field(default_factory=list, description="Lista de itens")
    meta: dict = Field(
        default_factory=dict,
        description="Metadados de paginação",
        examples=[{"page": 1, "page_size": 20, "total": 100, "total_pages": 5}],
    )


class SearchResponse(BaseModel):
    """Resposta de busca com highlights e facets."""

    success: bool = Field(True, examples=[True])
    data: list[Any] = Field(default_factory=list, description="Resultados da busca")
    meta: dict = Field(
        default_factory=dict,
        description="Metadados da busca",
        examples=[{"page": 1, "page_size": 20, "total": 42, "query": "edital"}],
    )
    facets: Optional[dict] = Field(None, description="Agregações/facets dos resultados")


class EnrichmentStatusResponse(BaseModel):
    """Status de enriquecimento de um documento/artefato."""

    success: bool = Field(True, examples=[True])
    data: dict = Field(
        default_factory=dict,
        description="Status de cada operação de enriquecimento",
        examples=[{
            "summary": True,
            "vectorization": True,
            "entities": True,
            "keywords": True,
            "chunking": False,
        }],
    )


class ChatMessageResponse(BaseModel):
    """Resposta do chat RAG."""

    success: bool = Field(True, examples=[True])
    data: dict = Field(
        default_factory=dict,
        description="Resposta gerada e fontes utilizadas",
        examples=[{
            "response": "De acordo com o edital 01/2024, o prazo de inscrição é de 15 a 30 de março.",
            "sources": [{"document_id": "abc123", "chunk": "...trecho relevante..."}],
            "session_id": "session-uuid-123",
        }],
    )


class StatsResponse(BaseModel):
    """Estatísticas do sistema."""

    success: bool = Field(True, examples=[True])
    data: dict = Field(
        default_factory=dict,
        description="Estatísticas agregadas",
        examples=[{
            "documentos_count": 1500,
            "artefatos_count": 320,
            "chunks_count": 12000,
            "enrichment_coverage": {"summary": 0.85, "vectorization": 0.92},
        }],
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Status geral: healthy | degraded", examples=["healthy"])
    dependencies: dict = Field(
        default_factory=dict,
        description="Status de cada dependência",
        examples=[{"elasticsearch": {"status": "up", "host": "http://localhost:9200"}}],
    )
