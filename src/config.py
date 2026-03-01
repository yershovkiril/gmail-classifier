from typing import Literal

import yaml
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings configured via environment variables.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM Settings
    llm_provider: Literal["vertexai", "openai", "anthropic"] = "vertexai"
    llm_model_name: str = "gemini-2.5-flash"  # Default Vertex AI model
    project_id: str | None = None  # Crucial for routing Vertex AI API quotas

    # Optional API Keys (Vertex AI uses application default credentials typically)
    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # Gmail Settings (Can be overridden to point to /secrets/ in Cloud Run)
    gmail_credentials_file: str = "credentials.json"
    gmail_token_file: str = "token.json"

    max_emails_per_run: int = Field(default=500, ge=1, le=500)
    processed_label_name: str = "PROCESSED_BY_AI"
    keep_unread_days: int = Field(default=7, ge=0)
    summary_frequency_hours: int = Field(default=24, ge=1)

    # Categories Taxonomy
    categories_file: str = "categories.yaml"
    categories: dict[str, str] = {}

    @model_validator(mode="after")
    def load_categories_from_file(self) -> "Settings":
        try:
            with open(self.categories_file, "r", encoding="utf-8") as f:
                self.categories = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not load {self.categories_file}: {e}")
            self.categories = {}
        return self


settings = Settings()
