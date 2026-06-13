from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "IUNA API"
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Elasticsearch
    ELASTICSEARCH_HOSTS: Optional[str] = None
    ELASTICSEARCH_USER: Optional[str] = None
    ELASTICSEARCH_PASSWORD: Optional[str] = None

    # LLM provider selection — default: gemini
    ACTIVE_LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    CLAUDE_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # Rasa
    RASA_API_URL: str = "http://rasa:5005"

    # Allows loading from .env file
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
