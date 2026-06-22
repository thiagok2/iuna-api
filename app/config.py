from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "IUNA API"
    API_V1_STR: str = "/api/v1"

    # Auth — Bearer token simples
    API_SECRET_TOKEN: Optional[str] = None

    # Elasticsearch
    ELASTICSEARCH_HOSTS: Optional[str] = None
    ELASTICSEARCH_USER: Optional[str] = None
    ELASTICSEARCH_PASSWORD: Optional[str] = None
    ES_INDEX_SUFFIX: str = ""

    # LLM provider selection — valores aceitos: gemini | claude | ollama
    ACTIVE_LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    CLAUDE_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # Rasa NLU
    RASA_API_URL: str = "http://rasa:5005"

    # Chat
    CHAT_SESSION_TTL_HOURS: int = 24
    CHAT_HISTORY_MAX_MESSAGES: int = 10

    # Batch processing
    BATCH_DEFAULT_CONCURRENCY: int = 3

    # Allows loading from .env file
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # --- Index names (computed properties) ---

    @property
    def index_documentos_ifal_v2(self) -> str:
        return f"documentos_ifal_v2{self.ES_INDEX_SUFFIX}"

    @property
    def index_documentos_ifal_v2_chunks(self) -> str:
        return f"documentos_ifal_v2_chunks{self.ES_INDEX_SUFFIX}"

    @property
    def index_artefatos(self) -> str:
        return f"artefatos{self.ES_INDEX_SUFFIX}"

    @property
    def index_artefatos_chunks(self) -> str:
        return f"artefatos_chunks{self.ES_INDEX_SUFFIX}"

    @property
    def index_chat_sessions(self) -> str:
        return f"chat_sessions{self.ES_INDEX_SUFFIX}"


settings = Settings()
