"""
Integration tests for enrichment endpoints.
ES e LLM são mockados — sem dependências externas reais.
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def _mock_svc(
    summary="Resumo do edital de seleção do IFAL.",
    entities=None,
    keywords=None,
    vector=None,
    chunks=4,
    status=None,
):
    """Cria um EnrichmentService mockado com respostas realistas."""
    svc = MagicMock()
    svc.llm = MagicMock()
    svc.llm.generate_summary = AsyncMock(return_value=summary)
    svc.llm.extract_entities = AsyncMock(
        return_value=entities
        or [
            {"texto": "IFAL", "categoria": "ORGANIZACAO", "confianca": 0.97},
            {"texto": "Alagoas", "categoria": "LOCAL", "confianca": 0.92},
        ]
    )
    svc.llm.extract_keywords = AsyncMock(
        return_value=keywords or ["edital", "seleção", "IFAL", "vagas", "inscrição"]
    )
    svc.enrich_summary = AsyncMock(return_value=summary)
    svc.enrich_vector = AsyncMock(return_value=vector or [0.1] * 768)
    svc.enrich_entities = AsyncMock(
        return_value=entities
        or [
            {"texto": "IFAL", "categoria": "ORGANIZACAO", "confianca": 0.97},
            {"texto": "Alagoas", "categoria": "LOCAL", "confianca": 0.92},
        ]
    )
    svc.enrich_keywords = AsyncMock(
        return_value=keywords or ["edital", "seleção", "IFAL", "vagas", "inscrição"]
    )
    svc.enrich_chunks = AsyncMock(return_value=chunks)
    svc.get_enrichment_status = AsyncMock(
        return_value=status
        or {
            "resumo_at": "2026-06-20T14:00:00+00:00",
            "entidades_at": "2026-06-20T14:01:00+00:00",
            "keywords_at": "2026-06-20T14:01:30+00:00",
            "embedding_vector_at": None,
            "chunking_at": None,
            "total_chunks": 0,
        }
    )
    return svc


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_enrich_sem_token_retorna_401(client):
    response = client.post(f"{BASE}/artefatos/summary/generate", json={"text": "teste"})
    if settings.API_SECRET_TOKEN:
        assert response.status_code == 401
    else:
        pytest.skip("API_SECRET_TOKEN não configurado — auth desativada")


def test_enrich_token_invalido_retorna_401(client):
    if not settings.API_SECRET_TOKEN:
        pytest.skip("API_SECRET_TOKEN não configurado — auth desativada")
    response = client.post(
        f"{BASE}/artefatos/summary/generate",
        json={"text": "teste"},
        headers={"Authorization": "Bearer token-invalido-xpto"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Artefatos — summary (modo texto direto)
# ---------------------------------------------------------------------------


def test_artefato_summary_com_texto_retorna_200(client):
    with patch("app.api.routers.enrichment._svc", return_value=_mock_svc()):
        response = client.post(
            f"{BASE}/artefatos/summary/generate",
            json={"text": "O IFAL oferece cursos técnicos e superiores em todo o estado de Alagoas."},
            headers=AUTH,
        )
    assert response.status_code == 200
    data = response.json()
    assert "resumo" in data["data"]
    assert len(data["data"]["resumo"]) > 0


def test_artefato_summary_com_document_id_retorna_200(client):
    with patch("app.api.routers.enrichment._svc", return_value=_mock_svc()):
        response = client.post(
            f"{BASE}/artefatos/summary/generate",
            json={"document_id": ARTEFATO_ID},
            headers=AUTH,
        )
    assert response.status_code == 200
    assert response.json()["data"]["resumo"] == "Resumo do edital de seleção do IFAL."


# ---------------------------------------------------------------------------
# Artefatos — entities
# ---------------------------------------------------------------------------


def test_artefato_entities_com_texto_retorna_lista(client):
    with patch("app.api.routers.enrichment._svc", return_value=_mock_svc()):
        response = client.post(
            f"{BASE}/artefatos/entities/extract",
            json={"text": "O Instituto Federal de Alagoas publicou edital em Maceió."},
            headers=AUTH,
        )
    assert response.status_code == 200
    entidades = response.json()["data"]["entidades"]
    assert isinstance(entidades, list)
    assert len(entidades) >= 1
    assert "texto" in entidades[0]
    assert "categoria" in entidades[0]


# ---------------------------------------------------------------------------
# Artefatos — keywords
# ---------------------------------------------------------------------------


def test_artefato_keywords_com_texto_retorna_lista(client):
    with patch("app.api.routers.enrichment._svc", return_value=_mock_svc()):
        response = client.post(
            f"{BASE}/artefatos/keywords/extract",
            json={"text": "Edital de seleção para vagas de técnico no IFAL 2026."},
            headers=AUTH,
        )
    assert response.status_code == 200
    keywords = response.json()["data"]["keywords"]
    assert isinstance(keywords, list)
    assert "edital" in keywords


# ---------------------------------------------------------------------------
# Artefatos — vectorization
# ---------------------------------------------------------------------------


def test_artefato_vectorization_com_document_id_retorna_dims(client):
    with patch("app.api.routers.enrichment._svc", return_value=_mock_svc()):
        response = client.post(
            f"{BASE}/artefatos/vectorization/generate",
            json={"document_id": ARTEFATO_ID},
            headers=AUTH,
        )
    assert response.status_code == 200
    assert response.json()["data"]["dims"] == 768


# ---------------------------------------------------------------------------
# Artefatos — chunking
# ---------------------------------------------------------------------------


def test_artefato_chunking_retorna_total_chunks(client):
    with patch("app.api.routers.enrichment._svc", return_value=_mock_svc(chunks=4)):
        response = client.post(
            f"{BASE}/artefatos/chunking/generate",
            json={"document_id": ARTEFATO_ID},
            headers=AUTH,
        )
    assert response.status_code == 200
    assert response.json()["data"]["total_chunks"] == 4
    assert response.json()["data"]["skipped"] is False


def test_artefato_chunking_chunk_size_menor_que_3000_retorna_422(client):
    response = client.post(
        f"{BASE}/artefatos/chunking/generate",
        json={"document_id": ARTEFATO_ID, "chunk_size": 500},
        headers=AUTH,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Artefatos — pipeline completo /enrich
# ---------------------------------------------------------------------------


def test_artefato_enrich_completo_retorna_resultado(client):
    with patch("app.api.routers.enrichment._svc", return_value=_mock_svc()):
        response = client.post(
            f"{BASE}/artefatos/{ARTEFATO_ID}/enrich",
            json={},
            headers=AUTH,
        )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "entities_count" in data
    assert "summary_length" in data
    assert "vector_dims" in data
    assert "total_chunks" in data


def test_artefato_enrich_operacoes_selecionadas(client):
    with patch("app.api.routers.enrichment._svc", return_value=_mock_svc()):
        response = client.post(
            f"{BASE}/artefatos/{ARTEFATO_ID}/enrich",
            json={"operations": ["summary", "entities"]},
            headers=AUTH,
        )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "summary_length" in data
    assert "entities_count" in data
    assert "vector_dims" not in data  # não foi solicitado


# ---------------------------------------------------------------------------
# Artefatos — enrichment-status
# ---------------------------------------------------------------------------


def test_artefato_enrichment_status_retorna_campos(client):
    with patch("app.api.routers.enrichment._svc", return_value=_mock_svc()):
        response = client.get(
            f"{BASE}/artefatos/{ARTEFATO_ID}/enrichment-status",
            headers=AUTH,
        )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "resumo_at" in data
    assert "entidades_at" in data
    assert "total_chunks" in data


# ---------------------------------------------------------------------------
# Documentos — mesmos contratos, root diferente
# ---------------------------------------------------------------------------


def test_documento_summary_com_texto_retorna_200(client):
    with patch("app.api.routers.enrichment._svc", return_value=_mock_svc()):
        response = client.post(
            f"{BASE}/documentos/summary/generate",
            json={"text": "Edital nº 73/2019 para contratação de técnico administrativo."},
            headers=AUTH,
        )
    assert response.status_code == 200
    assert "resumo" in response.json()["data"]


def test_documento_enrich_completo(client):
    with patch("app.api.routers.enrichment._svc", return_value=_mock_svc()):
        response = client.post(
            f"{BASE}/documentos/{DOCUMENTO_ID}/enrich",
            json={},
            headers=AUTH,
        )
    assert response.status_code == 200
    assert "summary_length" in response.json()["data"]
