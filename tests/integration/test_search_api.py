"""
T-15, T-16, T-17, T-18, T-19 — Integration tests para os endpoints de busca, scoring e listagem.
Endpoints retornam 501 agora — testes marcados xfail, viram PASS após implementação.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings

ARTEFATO_ID = "13e17202-2843-4827-be0d-1e8b62e7d4a9"
DOCUMENTO_ID = "ejcC7psBL-x_8ArHVaKJ"
TOKEN = settings.API_SECRET_TOKEN or "dev"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
BASE = "/api/v1"

NOT_IMPL = pytest.mark.xfail(strict=False, reason="Bloco 4 não implementado — endpoint retorna 501")


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


_SEARCH_RESULT = {
    "results": [
        {"id": DOCUMENTO_ID, "score": 1.8, "source": {"filename": "edital.pdf", "ato": {}}, "highlights": {}},
    ],
    "total": 2,
}

_FACETS_RESULT = {
    "aggregations": {"tipo_doc": {"buckets": [{"key": "edital", "doc_count": 3}]}},
    "total": 5,
}


def _mock_search_svc():
    svc = MagicMock()
    svc.search_fulltext = AsyncMock(return_value=_SEARCH_RESULT)
    svc.search_facets = AsyncMock(return_value=_FACETS_RESULT)
    svc.search_similar = AsyncMock(return_value=_SEARCH_RESULT)
    svc.search_by_entity = AsyncMock(return_value=_SEARCH_RESULT)
    svc.search_by_keyword = AsyncMock(return_value=_SEARCH_RESULT)
    svc.suggest = AsyncMock(return_value=["edital", "edital 2024"])
    svc.search = AsyncMock(return_value=_SEARCH_RESULT)
    return svc


# ---------------------------------------------------------------------------
# Rotas existem (não 404) — passam agora
# ---------------------------------------------------------------------------


def test_search_documentos_rota_existe(client):
    with patch("app.api.routers.search_documentos._svc", return_value=_mock_search_svc()):
        response = client.get(f"{BASE}/documentos/search/?q=edital", headers=AUTH)
    assert response.status_code != 404


def test_search_artefatos_rota_existe(client):
    with patch("app.api.routers.search_artefatos._svc", return_value=_mock_search_svc()):
        response = client.get(f"{BASE}/artefatos/search/?q=edital", headers=AUTH)
    assert response.status_code != 404


def test_search_documentos_chunks_rota_existe(client):
    with patch("app.api.routers.search_documentos._chunks_svc", return_value=_mock_search_svc()):
        response = client.get(f"{BASE}/documentos/search/chunks?q=prazo", headers=AUTH)
    assert response.status_code != 404


def test_entities_documentos_rota_existe(client):
    with patch("app.api.routers.entities_listing._svc", return_value=MagicMock(
        list_entities=AsyncMock(return_value=[])
    )):
        response = client.get(f"{BASE}/documentos/entities", headers=AUTH)
    assert response.status_code != 404


def test_entities_artefatos_rota_existe(client):
    with patch("app.api.routers.entities_listing._svc", return_value=MagicMock(
        list_entities=AsyncMock(return_value=[])
    )):
        response = client.get(f"{BASE}/artefatos/entities", headers=AUTH)
    assert response.status_code != 404


def test_scoring_documentos_rota_existe(client):
    with patch("app.api.routers.scoring._svc", return_value=MagicMock(
        increment_score=AsyncMock(return_value=1.0)
    )):
        response = client.post(
            f"{BASE}/documentos/{DOCUMENTO_ID}/score",
            json={"action": "click"},
            headers=AUTH,
        )
    assert response.status_code != 404


# ---------------------------------------------------------------------------
# T-15 — Busca full-text em documentos (xfail até implementação)
# ---------------------------------------------------------------------------


@NOT_IMPL
def test_search_documentos_retorna_200(client):
    with patch("app.api.routers.search_documentos._svc", return_value=_mock_search_svc()):
        response = client.get(f"{BASE}/documentos/search/?q=edital", headers=AUTH)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("data"), list)


@NOT_IMPL
def test_search_documentos_com_filtros(client):
    with patch("app.api.routers.search_documentos._svc", return_value=_mock_search_svc()):
        response = client.get(
            f"{BASE}/documentos/search/?q=edital&tipo_doc=edital&ano=2024",
            headers=AUTH,
        )
    assert response.status_code == 200


@NOT_IMPL
def test_search_documentos_facets(client):
    with patch("app.api.routers.search_documentos._svc", return_value=_mock_search_svc()):
        response = client.get(f"{BASE}/documentos/search/facets?q=edital", headers=AUTH)
    assert response.status_code == 200
    data = response.json()
    assert "aggregations" in data.get("data", {}) or "facets" in data.get("data", {})


@NOT_IMPL
def test_search_documentos_similar(client):
    with patch("app.api.routers.search_documentos._svc", return_value=_mock_search_svc()):
        response = client.get(
            f"{BASE}/documentos/search/similar/{DOCUMENTO_ID}", headers=AUTH
        )
    assert response.status_code == 200


@NOT_IMPL
def test_search_documentos_by_entity(client):
    with patch("app.api.routers.search_documentos._svc", return_value=_mock_search_svc()):
        response = client.get(
            f"{BASE}/documentos/search/by-entity?entity=IFAL", headers=AUTH
        )
    assert response.status_code == 200


@NOT_IMPL
def test_search_documentos_by_keyword(client):
    with patch("app.api.routers.search_documentos._svc", return_value=_mock_search_svc()):
        response = client.get(
            f"{BASE}/documentos/search/by-keyword?keyword=edital", headers=AUTH
        )
    assert response.status_code == 200


@NOT_IMPL
def test_search_documentos_suggest(client):
    with patch("app.api.routers.search_documentos._svc", return_value=_mock_search_svc()):
        response = client.get(
            f"{BASE}/documentos/search/suggest?q=edi", headers=AUTH
        )
    assert response.status_code == 200
    assert isinstance(response.json().get("data"), list)


# ---------------------------------------------------------------------------
# T-16 — Busca em artefatos (xfail)
# ---------------------------------------------------------------------------


@NOT_IMPL
def test_search_artefatos_retorna_200(client):
    with patch("app.api.routers.search_artefatos._svc", return_value=_mock_search_svc()):
        response = client.get(f"{BASE}/artefatos/search/?q=programação", headers=AUTH)
    assert response.status_code == 200


@NOT_IMPL
def test_search_artefatos_similar(client):
    with patch("app.api.routers.search_artefatos._svc", return_value=_mock_search_svc()):
        response = client.get(
            f"{BASE}/artefatos/search/similar/{ARTEFATO_ID}", headers=AUTH
        )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# T-17 — Busca em chunks (xfail)
# ---------------------------------------------------------------------------


@NOT_IMPL
def test_search_documentos_chunks_retorna_200(client):
    with patch("app.api.routers.search_documentos._svc", return_value=_mock_search_svc()):
        response = client.get(
            f"{BASE}/documentos/search/chunks?q=prazo+de+inscrição", headers=AUTH
        )
    assert response.status_code == 200


@NOT_IMPL
def test_search_chunks_filtrado_por_document_id(client):
    with patch("app.api.routers.search_documentos._svc", return_value=_mock_search_svc()):
        response = client.get(
            f"{BASE}/documentos/search/chunks?q=prazo&document_id={DOCUMENTO_ID}",
            headers=AUTH,
        )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# T-18 — Scoring (xfail)
# ---------------------------------------------------------------------------


@NOT_IMPL
def test_score_documento_click(client):
    with patch("app.api.routers.scoring._svc", return_value=MagicMock(
        increment_score=AsyncMock(return_value=6.0)
    )):
        response = client.post(
            f"{BASE}/documentos/{DOCUMENTO_ID}/score",
            json={"action": "click"},
            headers=AUTH,
        )
    assert response.status_code == 200


@NOT_IMPL
def test_score_acao_invalida_retorna_422(client):
    response = client.post(
        f"{BASE}/documentos/{DOCUMENTO_ID}/score",
        json={"action": "acao-invalida"},
        headers=AUTH,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# T-19 — Listagem de entidades e keywords (xfail)
# ---------------------------------------------------------------------------


@NOT_IMPL
def test_list_documentos_entities(client):
    with patch("app.api.routers.entities_listing._svc", return_value=MagicMock(
        list_entities=AsyncMock(return_value=[{"texto": "IFAL", "count": 12}])
    )):
        response = client.get(f"{BASE}/documentos/entities", headers=AUTH)
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


@NOT_IMPL
def test_list_artefatos_keywords(client):
    with patch("app.api.routers.entities_listing._svc", return_value=MagicMock(
        list_keywords=AsyncMock(return_value=[{"keyword": "edital", "count": 8}])
    )):
        response = client.get(f"{BASE}/artefatos/keywords", headers=AUTH)
    assert response.status_code == 200


@NOT_IMPL
def test_list_entities_filtrado_por_tipo(client):
    with patch("app.api.routers.entities_listing._svc", return_value=MagicMock(
        list_entities=AsyncMock(return_value=[])
    )):
        response = client.get(
            f"{BASE}/documentos/entities?entity_type=ORGANIZACAO", headers=AUTH
        )
    assert response.status_code == 200
