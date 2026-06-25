import asyncio
import json
import logging
import random

from google import genai

from app.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_MAX_INPUT_CHARS = 30_000


class GeminiProvider(BaseLLMProvider):
    def __init__(
        self,
        api_key: str,
        text_model: str = "gemini-2.0-flash",
        embed_model: str = "gemini-embedding-001",
        embed_dims: int = 768,
    ):
        self._client = genai.Client(api_key=api_key)
        self._text_model = text_model
        self._embed_model = embed_model
        self._embed_dims = embed_dims

    async def generate_summary(self, text: str) -> str:
        prompt = (
            "Gere um resumo conciso e informativo do texto abaixo em português. "
            "O resumo deve ter entre 100 e 500 palavras, capturando os pontos principais.\n\n"
            f"Texto:\n{text[:_MAX_INPUT_CHARS]}\n\nResumo:"
        )
        return await self._generate(prompt)

    async def generate_embedding(self, text: str) -> list[float]:
        return await self._embed(text[:_MAX_INPUT_CHARS])

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
            response = await self._client.aio.models.generate_content(
                model=self._text_model, contents="ping"
            )
            return bool(response.text)
        except Exception:
            return False

    async def _generate(self, prompt: str, max_retries: int = 5) -> str:
        for attempt in range(max_retries):
            try:
                response = await self._client.aio.models.generate_content(
                    model=self._text_model, contents=prompt
                )
                return response.text or ""
            except Exception as exc:
                if attempt == max_retries - 1:
                    raise
                if _is_retryable(exc):
                    delay = 2.0 * (2**attempt) + random.uniform(0, 1)
                    logger.warning("Gemini indisponível, aguardando %.1fs (tentativa %d/%d)", delay, attempt + 1, max_retries)
                    await asyncio.sleep(delay)
                else:
                    raise
        return ""

    async def _embed(self, text: str, max_retries: int = 5) -> list[float]:
        for attempt in range(max_retries):
            try:
                result = await self._client.aio.models.embed_content(
                    model=self._embed_model,
                    contents=text,
                    config={"output_dimensionality": self._embed_dims},
                )
                return list(result.embeddings[0].values)
            except Exception as exc:
                if attempt == max_retries - 1:
                    raise
                if _is_retryable(exc):
                    delay = 2.0 * (2**attempt) + random.uniform(0, 1)
                    logger.warning("Gemini embed indisponível, aguardando %.1fs (tentativa %d/%d)", delay, attempt + 1, max_retries)
                    await asyncio.sleep(delay)
                else:
                    raise
        return []

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


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(kw in msg for kw in (
        "429", "rate", "quota", "resource exhausted",
        "503", "unavailable", "overloaded", "try again",
    ))
