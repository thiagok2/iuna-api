"""
Request models (Pydantic schemas) for the IUNA API.
Used for Body payloads and documented Query dependencies.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# CRUD — Metadata updates
# ---------------------------------------------------------------------------


class MetadataUpdate(BaseModel):
    """Atualização parcial de metadados de um documento institucional."""

    titulo: Optional[str] = Field(None, description="Título do documento", examples=["Edital 01/2024"])
    ementa: Optional[str] = Field(
        None, description="Ementa/resumo curto", examples=["Processo seletivo para docentes"]
    )
    tipo_doc: Optional[str] = Field(None, description="Tipo do documento", examples=["edital"])
    tags: Optional[list[str]] = Field(
        None, description="Tags de classificação", examples=[["educação", "processo seletivo"]]
    )
    orgao: Optional[str] = Field(None, description="Órgão emissor", examples=["IFAL"])
    esfera: Optional[str] = Field(None, description="Esfera administrativa", examples=["federal"])
    ano: Optional[int] = Field(None, description="Ano de publicação", examples=[2024])
    publico: Optional[bool] = Field(None, description="Visibilidade pública", examples=[True])


class ArtefatoMetadataUpdate(BaseModel):
    """Atualização parcial de metadados de um artefato didático."""

    titulo: Optional[str] = Field(None, description="Título do artefato", examples=["Introdução à Programação"])
    tipo: Optional[str] = Field(None, description="Tipo do artefato (livro, plano, apostila...)", examples=["livro"])
    tags: Optional[list[str]] = Field(
        None, description="Tags de classificação", examples=[["programação", "python"]]
    )
    disciplina: Optional[str] = Field(None, description="Disciplina associada", examples=["Programação I"])
    curso: Optional[str] = Field(None, description="Curso associado", examples=["Ciência da Computação"])
    autor: Optional[str] = Field(None, description="Autor do artefato", examples=["Prof. João"])


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------


class EnrichmentRequest(BaseModel):
    """Requisição para gerar enriquecimento (summary, vectorization, entities, keywords)."""

    document_id: Optional[str] = Field(None, description="ID do documento no Elasticsearch", examples=["abc123"])
    filename: Optional[str] = Field(None, description="Nome do arquivo (alternativa ao ID)", examples=["edital_01_2024.pdf"])
    text: Optional[str] = Field(
        None,
        description="Texto direto (quando não há documento indexado)",
        examples=["Texto bruto para processar..."],
    )


class ChunkingRequest(BaseModel):
    """Requisição para gerar chunks de um documento."""

    document_id: Optional[str] = Field(None, description="ID do documento", examples=["abc123"])
    filename: Optional[str] = Field(None, description="Nome do arquivo", examples=["edital_01_2024.pdf"])
    chunk_size: int = Field(3000, ge=500, description="Tamanho de cada chunk (caracteres)", examples=[3000])
    chunk_overlap: int = Field(500, ge=0, description="Sobreposição entre chunks", examples=[500])


class EnrichAllRequest(BaseModel):
    """Requisição para pipeline completo de enriquecimento."""

    operations: Optional[list[str]] = Field(
        None,
        description="Operações a executar. Se None, executa todas.",
        examples=[["summary", "entities", "keywords", "vectorization", "chunking"]],
    )


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


class ChatMessageRequest(BaseModel):
    """Enviar mensagem ao chat RAG."""

    message: str = Field(
        ..., description="Mensagem do usuário",
        examples=["O que diz o edital 01/2024 sobre o prazo de inscrição?"],
    )
    session_id: str = Field(..., description="ID da sessão de chat", examples=["session-uuid-123"])
    source_type: Optional[str] = Field(
        None,
        description="Tipo de fonte para busca livre (documentos_ifal_v2, artefatos). "
        "Usado apenas quando a sessão não tem documentos específicos no contexto.",
        examples=["documentos_ifal_v2"],
    )


class AddDocumentoToSessionRequest(BaseModel):
    """Adicionar documento ao contexto de uma sessão."""

    document_id: str = Field(..., description="ID do documento a adicionar", examples=["abc123"])


class AddArtefatoToSessionRequest(BaseModel):
    """Adicionar artefato ao contexto de uma sessão."""

    artefato_id: str = Field(..., description="ID do artefato a adicionar", examples=["art-456"])


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


class ScoreRequest(BaseModel):
    """Registrar uma ação de interação do usuário."""

    action: Literal["click", "add_to_chat", "download", "share"] = Field(
        ...,
        description="Tipo de ação: click | add_to_chat | download | share",
        examples=["click"],
    )
