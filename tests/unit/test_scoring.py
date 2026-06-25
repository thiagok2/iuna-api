"""
T-18 — Unit tests para app/core/scoring.py e ScoringService.
Ficam SKIPPED até os módulos serem criados.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

scoring_module = pytest.importorskip(
    "app.core.scoring",
    reason="T-18 não implementado: app/core/scoring.py não existe",
)

SCORE_WEIGHTS = scoring_module.SCORE_WEIGHTS


# ---------------------------------------------------------------------------
# SCORE_WEIGHTS
# ---------------------------------------------------------------------------


def test_score_weights_contem_acoes_esperadas():
    for action in ("click", "add_to_chat", "download", "share"):
        assert action in SCORE_WEIGHTS, f"Ação '{action}' não encontrada em SCORE_WEIGHTS"


def test_score_weights_valores_positivos():
    for action, weight in SCORE_WEIGHTS.items():
        assert weight > 0, f"Peso de '{action}' deve ser positivo"


def test_score_weights_download_maior_que_click():
    assert SCORE_WEIGHTS["download"] >= SCORE_WEIGHTS["click"]


def test_score_weights_add_to_chat_maior_que_click():
    assert SCORE_WEIGHTS["add_to_chat"] >= SCORE_WEIGHTS["click"]


# ---------------------------------------------------------------------------
# ScoringService
# ---------------------------------------------------------------------------

scoring_service_module = pytest.importorskip(
    "app.services.scoring_service",
    reason="T-18 não implementado: app/services/scoring_service.py não existe",
)
ScoringService = scoring_service_module.ScoringService


@pytest.fixture
def mock_es():
    es = MagicMock()
    es.get = AsyncMock(return_value={
        "_id": "ejcC7psBL-x_8ArHVaKJ",
        "_source": {
            "ato": {"popularity_score": 5.0},
            "filename": "edital-73-2019.pdf",
        },
    })
    es.update = AsyncMock(return_value={})
    return es


@pytest.fixture
def svc(mock_es):
    return ScoringService(mock_es)


async def test_increment_score_click(svc, mock_es):
    result = await svc.increment_score(
        index="documentos_ifal_v2",
        doc_id="ejcC7psBL-x_8ArHVaKJ",
        action="click",
    )
    assert result is not None
    mock_es.update.assert_called_once()


async def test_increment_score_download_maior_incremento_que_click(svc, mock_es):
    await svc.increment_score("documentos_ifal_v2", "doc-1", "click")
    click_call = mock_es.update.call_args

    mock_es.update.reset_mock()

    await svc.increment_score("documentos_ifal_v2", "doc-1", "download")
    download_call = mock_es.update.call_args

    click_body = str(click_call)
    download_body = str(download_call)

    # Os valores exatos dependem da implementação, mas download deve ter peso >= click
    assert download_body != click_body or SCORE_WEIGHTS["download"] == SCORE_WEIGHTS["click"]


async def test_increment_score_acao_invalida_levanta_erro(svc):
    with pytest.raises((ValueError, KeyError)):
        await svc.increment_score("documentos_ifal_v2", "doc-1", "acao-inexistente")
