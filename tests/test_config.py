import pytest

from src.config import Settings


def test_config_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL_NAME", "gpt-4o")
    monkeypatch.setenv("MAX_EMAILS_PER_RUN", "5")

    settings = Settings()
    assert settings.llm_provider == "openai"
    assert settings.llm_model_name == "gpt-4o"
    assert settings.max_emails_per_run == 5
