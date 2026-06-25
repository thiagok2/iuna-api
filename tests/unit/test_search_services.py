"""
T-15, T-16, T-17 — Unit tests para search services.
Ficam SKIPPED até os módulos serem criados.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# Fixtures comuns
# ---------------------------------------------------------------------------

_ES_HITS = {
    "hits": {
        "total": {"value": 2},
        "hits": [
            {
                "_id": "ejcC7psBL-x_8ArHVaKJ",
                "_score": 1.8,
                "_source": {"filename": "edital-representanteslocais-2022.pdf", "ato": {}},
                "highlight": {"attachment.content": ["prazo de <em>inscrição</em>"]},
            },
            {
                "_id": "bjf37ZsBL-x_8ArHVaB2",
                "_score": 1.2,
                "_source": {"filename": "edital-73-2019.pdf", "ato": {}},
                "highlight": {},
            },
        ],
    },
    "aggregations": {},
}

_ES_CHUNKS_HITS = {
    "hits": {
        "total": {"value": 3},
        "hits": [
            {
                "_id": "chunk-1",
                "_score": 1.5,
                "_source": {
                    "parent_document_id": "ejcC7psBL-x_8ArHVaKJ",
                    "chunk_index": 0,
                    "content": "prazo de inscrição é até 30/06/2026",
                },
            },
        ],
    }
}


@pytest.fixture
def mock_es():
    es = MagicMock()
    es.search = AsyncMock(return_value=_ES_HITS)
    return es


# ---------------------------------------------------------------------------
# T-15 — DocumentosSearchService
# ---------------------------------------------------------------------------

documentos_search = pytest.importorskip(
    "app.services.documentos_search",
    reason="T-15 não implementado: app/services/documentos_search.py não existe",
)
DocumentosSearchService = documentos_search.DocumentosSearchService


@pytest.fixture
def doc_svc(mock_es):
    return DocumentosSearchService(mock_es)


async def test_search_fulltext_retorna_hits(doc_svc, mock_es):
    result = await doc_svc.search_fulltext(
        index="documentos_ifal_v2", q="inscrição", page=1, page_size=20
    )
    assert "hits" in result or "results" in result
    mock_es.search.assert_called_once()


async def test_search_fulltext_com_filtro_tipo(doc_svc, mock_es):
    await doc_svc.search_fulltext(
        index="documentos_ifal_v2", q="edital", page=1, page_size=20,
        filters={"tipo_doc": "edital"},
    )
    call_body = mock_es.search.call_args.kwargs.get("body", {})
    assert call_body  # body foi enviado ao ES


async def test_search_facets_retorna_agregacoes(doc_svc, mock_es):
    mock_es.search.return_value = {"hits": {"total": {"value": 0}, "hits": []}, "aggregations": {"tipo_doc": {"buckets": []}}}
    result = await doc_svc.search_facets(index="documentos_ifal_v2", q="edital")
    assert "aggregations" in result or "facets" in result


async def test_search_similar_retorna_hits(doc_svc, mock_es):
    result = await doc_svc.search_similar(
        index="documentos_ifal_v2", doc_id="ejcC7psBL-x_8ArHVaKJ", page_size=10
    )
    assert result is not None


async def test_search_by_entity_retorna_hits(doc_svc, mock_es):
    result = await doc_svc.search_by_entity(
        index="documentos_ifal_v2", entity="IFAL", page=1, page_size=20
    )
    assert result is not None


async def test_search_by_keyword_retorna_hits(doc_svc, mock_es):
    result = await doc_svc.search_by_keyword(
        index="documentos_ifal_v2", keyword="edital", page=1, page_size=20
    )
    assert result is not None


async def test_suggest_retorna_lista(doc_svc, mock_es):
    mock_es.search.return_value = {"suggest": {"autocomplete": [{"options": [{"text": "edital"}]}]}}
    result = await doc_svc.suggest(index="documentos_ifal_v2", q="edi", size=5)
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# T-16 — ArtefatosSearchService
# ---------------------------------------------------------------------------

artefatos_search = pytest.importorskip(
    "app.services.artefatos_search",
    reason="T-16 não implementado: app/services/artefatos_search.py não existe",
)
ArtefatosSearchService = artefatos_search.ArtefatosSearchService


@pytest.fixture
def art_svc(mock_es):
    return ArtefatosSearchService(mock_es)


async def test_art_search_fulltext_retorna_hits(art_svc, mock_es):
    result = await art_svc.search_fulltext(
        index="artefatos", q="programação", page=1, page_size=20
    )
    assert result is not None
    mock_es.search.assert_called_once()


async def test_art_search_similar_retorna_hits(art_svc, mock_es):
    result = await art_svc.search_similar(
        index="artefatos", doc_id="13e17202-2843-4827-be0d-1e8b62e7d4a9", page_size=5
    )
    assert result is not None


async def test_art_search_by_entity(art_svc, mock_es):
    result = await art_svc.search_by_entity(
        index="artefatos", entity="IFAL", page=1, page_size=20
    )
    assert result is not None


# ---------------------------------------------------------------------------
# T-17 — ChunksSearch (documentos e artefatos)
# ---------------------------------------------------------------------------

chunks_search = pytest.importorskip(
    "app.services.chunks_search",
    reason="T-17 não implementado: app/services/chunks_search.py não existe",
)
ChunksSearchService = chunks_search.ChunksSearchService


@pytest.fixture
def chunk_svc(mock_es):
    mock_es.search.return_value = _ES_CHUNKS_HITS
    return ChunksSearchService(mock_es)


async def test_chunks_search_retorna_hits_com_parent_id(chunk_svc, mock_es):
    result = await chunk_svc.search(
        index="documentos_ifal_v2_chunks", q="prazo de inscrição", page=1, page_size=20
    )
    assert result is not None
    mock_es.search.assert_called_once()


async def test_chunks_search_filtrado_por_document_id(chunk_svc, mock_es):
    await chunk_svc.search(
        index="documentos_ifal_v2_chunks",
        q="prazo",
        page=1,
        page_size=20,
        document_id="ejcC7psBL-x_8ArHVaKJ",
    )
    call_body = mock_es.search.call_args.kwargs.get("body", {})
    assert "ejcC7psBL-x_8ArHVaKJ" in str(call_body)
