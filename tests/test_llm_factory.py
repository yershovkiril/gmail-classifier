from unittest.mock import MagicMock, patch

import pytest

from src.services.llm_factory import get_llm


@patch("src.services.llm_factory.settings")
def test_get_llm_vertexai(mock_settings: MagicMock) -> None:
    mock_settings.llm_provider = "vertexai"
    mock_settings.llm_model_name = "gemini-1.5-pro"

    # Needs to be mocked to prevent real GCP auth calls during tests
    with patch("src.services.llm_factory.ChatVertexAI") as mock_vertex:
        get_llm()
        mock_vertex.assert_called_once_with(model_name="gemini-1.5-pro", temperature=0.0)

@patch("src.services.llm_factory.settings")
def test_get_llm_openai(mock_settings: MagicMock) -> None:
    mock_settings.llm_provider = "openai"
    mock_settings.llm_model_name = "gpt-4o"
    mock_settings.openai_api_key = "test-key"

    with patch("src.services.llm_factory.ChatOpenAI") as mock_openai:
        get_llm()
        mock_openai.assert_called_once_with(model="gpt-4o", api_key="test-key", temperature=0.0)

@patch("src.services.llm_factory.settings")
def test_get_llm_openai_missing_key(mock_settings: MagicMock) -> None:
    mock_settings.llm_provider = "openai"
    mock_settings.openai_api_key = None

    with pytest.raises(ValueError, match="OpenAI API key is missing"):
        get_llm()

@patch("src.services.llm_factory.settings")
def test_get_llm_unsupported(mock_settings: MagicMock) -> None:
    mock_settings.llm_provider = "invalid"
    with pytest.raises(ValueError, match="Unsupported LLM provider: invalid"):
        get_llm()
