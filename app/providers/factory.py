from app.config import settings
from app.providers.base import BaseLLMProvider


def _build_provider(name: str) -> BaseLLMProvider:
    match name:
        case "gemini":
            from app.providers.gemini import GeminiProvider
            return GeminiProvider(
                api_key=settings.GEMINI_API_KEY,
                text_model=settings.GEMINI_TEXT_MODEL,
                embed_model=settings.GEMINI_EMBED_MODEL,
                embed_dims=settings.GEMINI_EMBED_DIMS,
            )
        case "claude":
            from app.providers.claude import ClaudeProvider
            return ClaudeProvider(api_key=settings.CLAUDE_API_KEY, model=settings.CLAUDE_MODEL)
        case "ollama":
            from app.providers.ollama import OllamaProvider
            return OllamaProvider(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)
        case _:
            raise ValueError(f"Provider desconhecido: {name}")


def get_llm_provider() -> BaseLLMProvider:
    return _build_provider(settings.ACTIVE_LLM_PROVIDER)


def get_embedding_provider() -> BaseLLMProvider:
    return _build_provider(settings.ACTIVE_EMBEDDING_PROVIDER)
