import logging
import os

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from src.config import settings

logger = logging.getLogger(__name__)


def get_llm() -> BaseChatModel:
    """
    Factory function to return the configured LLM provider.
    """
    if settings.llm_provider == "vertexai":
        if not settings.gemini_api_key:
            logger.warning("No gemini_api_key detected. The open Gemini API is required for this provider.")
        else:
            os.environ["GOOGLE_API_KEY"] = settings.gemini_api_key

        return ChatGoogleGenerativeAI(
            model=settings.llm_model_name,
            temperature=0.0
        )
    elif settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is missing.")
        return ChatOpenAI(
            model=settings.llm_model_name,
            api_key=settings.openai_api_key, # type: ignore
            temperature=0.0,
        ) # type: ignore
    elif settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("Anthropic API key is missing.")
        return ChatAnthropic(
            model_name=settings.llm_model_name,
            api_key=settings.anthropic_api_key, # type: ignore
            temperature=0.0,
        ) # type: ignore
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
