import asyncio
import json
import logging

import anthropic

from app.core.exceptions import ServiceUnavailableError
from app.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_MAX_INPUT_CHARS = 30_000
_MAX_TOKENS = 2048


class ClaudeProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5"):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def generate_summary(self, text: str) -> str:
        prompt = (
            "Gere um resumo conciso e informativo do texto abaixo em português. "
            "O resumo deve ter entre 100 e 500 palavras, capturando os pontos principais.\n\n"
            f"Texto:\n{text[:_MAX_INPUT_CHARS]}\n\nResumo:"
        )
        return await self._generate(prompt)

    async def generate_embedding(self, text: str) -> list[float]:
        raise ServiceUnavailableError("ClaudeProvider não suporta geração de embeddings.")

    async def extract_entities(self, text: str) -> list[dict]:
        prompt = (
            "Extraia entidades nomeadas do texto abaixo.\n"
            "Retorne APENAS um JSON válido (sem markdown, sem explicações) com uma lista:\n"
            '[{"texto": "nome", "categoria": "CATEGORIA", "confianca": 0.95}]\n\n'
            "Categorias: PESSOA, ORGANIZACAO, LOCAL, DATA, DOCUMENTO, OUTRO\n\n"
            f"Texto:\n{text[:_MAX_INPUT_CHARS]}\n\nJSON:"
        )
        raw = await self._generate(prompt)
        return self._parse_json_list(raw, default=[])

    async def extract_keywords(self, text: str) -> list[str]:
        prompt = (
            "Extraia as principais palavras-chave e termos-chave do texto abaixo.\n"
            "Retorne APENAS um JSON válido (sem markdown) com uma lista de strings. Máximo 20.\n"
            'Exemplo: ["palavra1", "termo chave 2"]\n\n'
            f"Texto:\n{text[:_MAX_INPUT_CHARS]}\n\nJSON:"
        )
        raw = await self._generate(prompt)
        return self._parse_json_list(raw, default=[])

    async def generate_response(
        self, context: str, question: str, history: list[dict] | None = None
    ) -> str:
        history_text = ""
        if history:
            lines = [f"{m['role'].capitalize()}: {m['content']}" for m in history[-6:]]
            history_text = "\nHistórico:\n" + "\n".join(lines) + "\n"

        ctx = context[:20_000] if context else "(sem contexto específico)"
        prompt = (
            "Você é um assistente especializado em documentos institucionais. "
            "Com base no contexto abaixo, responda à pergunta do usuário em português "
            "de forma clara e precisa.\n\n"
            f"Contexto:\n{ctx}\n"
            f"{history_text}\n"
            f"Pergunta: {question}\n\nResposta:"
        )
        return await self._generate(prompt)

    async def health_check(self) -> bool:
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            return bool(response.content)
        except Exception:
            return False

    async def _generate(self, prompt: str, max_retries: int = 3) -> str:
        for attempt in range(max_retries):
            try:
                response = await self._client.messages.create(
                    model=self._model,
                    max_tokens=_MAX_TOKENS,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text if response.content else ""
            except anthropic.RateLimitError as exc:
                if attempt == max_retries - 1:
                    raise
                delay = 2.0 * (2**attempt)
                logger.warning("Claude rate limit, aguardando %.0fs (tentativa %d)", delay, attempt + 1)
                await asyncio.sleep(delay)
            except anthropic.APIError as exc:
                raise ServiceUnavailableError(f"Claude API error: {exc}") from exc
        return ""

    @staticmethod
    def _parse_json_list(raw: str, default: list) -> list:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = [l for l in cleaned.split("\n") if not l.startswith("```")]
            cleaned = "\n".join(lines).strip()
        try:
            result = json.loads(cleaned)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            start, end = cleaned.find("["), cleaned.rfind("]")
            if start != -1 and end != -1:
                try:
                    return json.loads(cleaned[start : end + 1])
                except json.JSONDecodeError:
                    pass
        logger.warning("Não foi possível parsear lista JSON do LLM: %.200s", raw)
        return default
