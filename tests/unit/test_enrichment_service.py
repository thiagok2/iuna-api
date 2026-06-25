"""
Unit tests for EnrichmentService.
All external dependencies (ESClient, LLM provider) are mocked.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.exceptions import ValidationError
from app.services.enrichment import EnrichmentService

SHORT_TEXT = "Texto curto para teste unitário."
LONG_TEXT = "palavra " * 1_500  # ~12.000 chars — ultrapassa threshold de 10.000


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_es():
    es = MagicMock()
    es.get = AsyncMock()
    es.update = AsyncMock(return_value={})
    es.delete_by_query = AsyncMock(return_value={})
    es.bulk_index = AsyncMock(return_value={})
    return es


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.generate_summary = AsyncMock(return_value="Resumo gerado pelo LLM.")
    llm.generate_embedding = AsyncMock(return_value=[0.1] * 768)
    llm.extract_entities = AsyncMock(
        return_value=[{"texto": "IFAL", "categoria": "ORGANIZACAO", "confianca": 0.95}]
    )
    llm.extract_keywords = AsyncMock(return_value=["edital", "seleção", "IFAL"])
    return llm


@pytest.fixture
def svc(mock_es, mock_llm):
    return EnrichmentService(mock_es, mock_llm)


def _doc(content: str, root: str = "artefato", resumo: str | None = None) -> dict:
    """Helper: monta um doc no formato retornado pelo ES."""
    return {
        "_id": "13e17202-2843-4827-be0d-1e8b62e7d4a9",
        "_source": {
            "attachment": {"content": content},
            "filename": "edital_selecao.pdf",
            root: {"resumo": resumo} if resumo else {},
        },
    }


# ---------------------------------------------------------------------------
# enrich_summary
# ---------------------------------------------------------------------------


async def test_enrich_summary_retorna_resumo(svc, mock_es, mock_llm):
    mock_es.get.return_value = _doc(SHORT_TEXT)

    result = await svc.enrich_summary("artefatos", "doc-123", "artefato")

    assert result == "Resumo gerado pelo LLM."
    mock_llm.generate_summary.assert_called_once_with(SHORT_TEXT)
    mock_es.update.assert_called_once()


async def test_enrich_summary_salva_resumo_at_no_es(svc, mock_es):
    mock_es.get.return_value = _doc(SHORT_TEXT)

    await svc.enrich_summary("artefatos", "doc-123", "artefato")

    call_body = mock_es.update.call_args.kwargs["body"]
    assert "resumo" in call_body["artefato"]
    assert "resumo_at" in call_body["artefato"]


async def test_enrich_summary_levanta_validation_error_se_content_vazio(svc, mock_es):
    mock_es.get.return_value = _doc("")

    with pytest.raises(ValidationError, match="attachment.content"):
        await svc.enrich_summary("artefatos", "doc-123", "artefato")


# ---------------------------------------------------------------------------
# enrich_vector
# ---------------------------------------------------------------------------


async def test_enrich_vector_usa_resumo_existente(svc, mock_es, mock_llm):
    mock_es.get.return_value = _doc(SHORT_TEXT, resumo="Resumo já existente.")

    vector = await svc.enrich_vector("artefatos", "doc-123", "artefato")

    assert len(vector) == 768
    mock_llm.generate_summary.assert_not_called()
    mock_llm.generate_embedding.assert_called_once_with("Resumo já existente.")


async def test_enrich_vector_gera_resumo_quando_ausente(svc, mock_es, mock_llm):
    mock_es.get.return_value = _doc(SHORT_TEXT)  # sem resumo

    vector = await svc.enrich_vector("artefatos", "doc-123", "artefato")

    assert len(vector) == 768
    mock_llm.generate_summary.assert_called_once()
    mock_llm.generate_embedding.assert_called_once_with("Resumo gerado pelo LLM.")


# ---------------------------------------------------------------------------
# enrich_entities
# ---------------------------------------------------------------------------


async def test_enrich_entities_retorna_lista(svc, mock_es, mock_llm):
    mock_es.get.return_value = _doc(SHORT_TEXT)

    entities = await svc.enrich_entities("artefatos", "doc-123", "artefato")

    assert len(entities) == 1
    assert entities[0]["texto"] == "IFAL"
    assert entities[0]["categoria"] == "ORGANIZACAO"
    mock_es.update.assert_called_once()


# ---------------------------------------------------------------------------
# enrich_keywords
# ---------------------------------------------------------------------------


async def test_enrich_keywords_retorna_lista_de_strings(svc, mock_es):
    mock_es.get.return_value = _doc(SHORT_TEXT)

    keywords = await svc.enrich_keywords("artefatos", "doc-123", "artefato")

    assert keywords == ["edital", "seleção", "IFAL"]
    mock_es.update.assert_called_once()


# ---------------------------------------------------------------------------
# enrich_chunks
# ---------------------------------------------------------------------------


async def test_enrich_chunks_retorna_zero_para_doc_curto(svc, mock_es, mock_llm):
    mock_es.get.return_value = _doc(SHORT_TEXT)

    result = await svc.enrich_chunks("artefatos", "artefatos_chunks", "doc-123", "artefato")

    assert result == 0
    mock_llm.generate_embedding.assert_not_called()
    mock_es.bulk_index.assert_not_called()


async def test_enrich_chunks_cria_chunks_para_doc_longo(svc, mock_es, mock_llm):
    mock_es.get.return_value = _doc(LONG_TEXT)

    result = await svc.enrich_chunks(
        "artefatos", "artefatos_chunks", "doc-123", "artefato",
        chunk_size=5_000, overlap=500,
    )

    assert result > 0
    mock_es.delete_by_query.assert_called_once()
    mock_es.bulk_index.assert_called_once()
    assert mock_llm.generate_embedding.call_count == result


async def test_enrich_chunks_levanta_validation_error_para_chunk_size_pequeno(svc, mock_es):
    mock_es.get.return_value = _doc(LONG_TEXT)

    with pytest.raises(ValidationError, match="3000"):
        await svc.enrich_chunks(
            "artefatos", "artefatos_chunks", "doc-123", "artefato", chunk_size=100
        )


# ---------------------------------------------------------------------------
# get_enrichment_status
# ---------------------------------------------------------------------------


async def test_get_enrichment_status_retorna_campos_corretos(svc, mock_es):
    mock_es.get.return_value = {
        "_id": "doc-123",
        "_source": {
            "artefato": {
                "resumo_at": "2026-06-01T10:00:00+00:00",
                "entidades_at": None,
                "keywords_at": "2026-06-02T08:30:00+00:00",
                "embedding_vector_at": None,
                "chunking_at": None,
                "total_chunks": 0,
            }
        },
    }

    status = await svc.get_enrichment_status("artefatos", "doc-123", "artefato")

    assert status["resumo_at"] == "2026-06-01T10:00:00+00:00"
    assert status["keywords_at"] == "2026-06-02T08:30:00+00:00"
    assert status["entidades_at"] is None
    assert status["total_chunks"] == 0


# ---------------------------------------------------------------------------
# _split_text (pure function)
# ---------------------------------------------------------------------------


def test_split_text_divide_em_chunks_do_tamanho_correto():
    text = "a" * 10_000
    chunks = EnrichmentService._split_text(text, chunk_size=3_000, overlap=500)

    assert len(chunks) > 1
    assert all(len(c) <= 3_000 for c in chunks)


def test_split_text_overlap_compartilha_conteudo():
    text = "b" * 6_000
    chunks = EnrichmentService._split_text(text, chunk_size=5_000, overlap=1_000)

    assert len(chunks) == 2
    assert chunks[0][-1_000:] == chunks[1][:1_000]


def test_split_text_texto_menor_que_chunk_retorna_um_chunk():
    text = "pequeno"
    chunks = EnrichmentService._split_text(text, chunk_size=3_000, overlap=500)

    assert len(chunks) == 1
    assert chunks[0] == "pequeno"
