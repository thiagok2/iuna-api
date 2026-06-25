"""
Unit tests for LLM providers and factory.
No real API calls — only local logic (parsing, factory wiring, error contracts).
"""

import pytest
from unittest.mock import patch

from app.core.exceptions import ServiceUnavailableError
from app.providers.gemini import GeminiProvider
from app.providers.claude import ClaudeProvider


# ---------------------------------------------------------------------------
# _parse_json_list  (mesma lógica em Gemini e Claude)
# ---------------------------------------------------------------------------


class TestParseJsonList:
    """Testa o helper de parsing de listas JSON retornadas pelo LLM."""

    def test_json_valido(self):
        raw = '[{"texto": "IFAL", "categoria": "ORGANIZACAO", "confianca": 0.95}]'
        result = GeminiProvider._parse_json_list(raw, default=[])
        assert result == [{"texto": "IFAL", "categoria": "ORGANIZACAO", "confianca": 0.95}]

    def test_json_com_markdown_fenced(self):
        raw = '```json\n["edital", "seleção", "IFAL"]\n```'
        result = GeminiProvider._parse_json_list(raw, default=[])
        assert result == ["edital", "seleção", "IFAL"]

    def test_json_embutido_em_texto(self):
        raw = 'Aqui estão as keywords: ["edital", "seleção"] fim do texto.'
        result = GeminiProvider._parse_json_list(raw, default=[])
        assert result == ["edital", "seleção"]

    def test_json_invalido_retorna_default(self):
        result = GeminiProvider._parse_json_list("isso não é JSON de jeito nenhum", default=[])
        assert result == []

    def test_lista_de_dicts(self):
        raw = '[{"texto": "João Silva", "categoria": "PESSOA"}, {"texto": "IFAL", "categoria": "ORGANIZACAO"}]'
        result = GeminiProvider._parse_json_list(raw, default=[])
        assert len(result) == 2
        assert result[1]["texto"] == "IFAL"

    def test_lista_vazia(self):
        result = GeminiProvider._parse_json_list("[]", default=["fallback"])
        assert result == []

    def test_objeto_em_vez_de_lista_retorna_default(self):
        # LLM às vezes retorna um objeto em vez de lista
        result = GeminiProvider._parse_json_list('{"texto": "IFAL"}', default=[])
        assert result == []


# ---------------------------------------------------------------------------
# ClaudeProvider — generate_embedding deve levantar ServiceUnavailableError
# ---------------------------------------------------------------------------


async def test_claude_generate_embedding_levanta_service_unavailable():
    provider = ClaudeProvider(api_key="fake-key-para-teste")
    with pytest.raises(ServiceUnavailableError, match="não suporta"):
        await provider.generate_embedding("qualquer texto")


# ---------------------------------------------------------------------------
# Factory — retorna o provider correto conforme ACTIVE_LLM_PROVIDER
# ---------------------------------------------------------------------------


def test_factory_retorna_gemini_provider():
    with patch("app.providers.factory.settings") as s:
        s.ACTIVE_LLM_PROVIDER = "gemini"
        s.GEMINI_API_KEY = "fake-gemini-key"
        s.GEMINI_TEXT_MODEL = "gemini-2.0-flash"
        s.GEMINI_EMBED_MODEL = "gemini-embedding-001"

        from app.providers.factory import get_llm_provider
        provider = get_llm_provider()

    assert isinstance(provider, GeminiProvider)
    assert provider._text_model == "gemini-2.0-flash"
    assert provider._embed_model == "gemini-embedding-001"


def test_factory_retorna_claude_provider():
    with patch("app.providers.factory.settings") as s:
        s.ACTIVE_LLM_PROVIDER = "claude"
        s.CLAUDE_API_KEY = "fake-claude-key"
        s.CLAUDE_MODEL = "claude-haiku-4-5"

        from app.providers.factory import get_llm_provider
        provider = get_llm_provider()

    assert isinstance(provider, ClaudeProvider)
    assert provider._model == "claude-haiku-4-5"


def test_factory_levanta_value_error_para_provider_desconhecido():
    with patch("app.providers.factory.settings") as s:
        s.ACTIVE_LLM_PROVIDER = "provider-que-nao-existe"

        from app.providers.factory import get_llm_provider
        with pytest.raises(ValueError, match="Provider desconhecido"):
            get_llm_provider()


def test_factory_claude_usa_modelo_customizado():
    with patch("app.providers.factory.settings") as s:
        s.ACTIVE_LLM_PROVIDER = "claude"
        s.CLAUDE_API_KEY = "fake-key"
        s.CLAUDE_MODEL = "claude-sonnet-4-6"

        from app.providers.factory import get_llm_provider
        provider = get_llm_provider()

    assert provider._model == "claude-sonnet-4-6"
