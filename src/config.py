from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings configured via environment variables.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM Settings
    llm_provider: Literal["vertexai", "openai", "anthropic"] = "vertexai"
    llm_model_name: str = "gemini-1.5-pro"  # Default Vertex AI model

    # Optional API Keys (Vertex AI uses application default credentials typically)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # Gmail Settings (Can be overridden to point to /secrets/ in Cloud Run)
    gmail_credentials_file: str = "credentials.json"
    gmail_token_file: str = "token.json"

    max_emails_per_run: int = 50
    process_batch_size: int = 10
    processed_label_name: str = "PROCESSED_BY_AI"

    # Dynamic Categories
    max_dynamic_categories: int = 10


settings = Settings()
