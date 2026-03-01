import logging
from typing import Any

from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from src.config import settings
from src.services.llm_factory import get_llm

logger = logging.getLogger(__name__)


class EmailClassificationResult(BaseModel):
    category: str = Field(description="The chosen category from the allowed taxonomy.")


class EmailClassifier:
    def __init__(self) -> None:
        self.llm = get_llm()

        self.structured_llm = self.llm.with_structured_output(EmailClassificationResult)

        allowed_categories = "\n".join(f"- {k}: {v}" for k, v in settings.categories.items())

        self.prompt = PromptTemplate.from_template(
            """You are an intelligent email categorizer. Your task is to analyze an incoming email and strictly assign it to one category from the taxonomy below.

### STRICT TAXONOMY:
{categories_text}
- Other: "Any emails that do not clearly fit the above descriptions."

### OPERATIONAL GUIDELINES:
1. Strict Selection: You MUST choose EXACTLY ONE category from the STRICT TAXONOMY list (or "Other"). Do not invent new categories.
2. Description Following: Follow the exact description rules of each category.
3. Context Clues: Look at the sender's domain and the subject line as primary indicators before analyzing the body text.

### EMAIL TO ANALYZE:
Sender: {sender}
Subject: {subject}
Body snippet: {snippet}
Body text: {body}

Choose the BEST category for this email."""
        ).partial(categories_text=allowed_categories)

    def classify_email(self, email_data: dict[str, Any]) -> str:
        """
        Takes raw email dictionary and returns the Category string.
        """
        try:
            chain = self.prompt | self.structured_llm
            result: EmailClassificationResult = chain.invoke(  # type: ignore
                {
                    "sender": email_data.get("sender", ""),
                    "subject": email_data.get("subject", ""),
                    "snippet": email_data.get("snippet", ""),
                    "body": email_data.get("body", "")[
                        :2000
                    ],  # Truncate body to fit context window reasonably
                }
            )
            return result.category
        except Exception as e:
            logger.error(f"Failed to classify email {email_data.get('id')}: {e}")
            return "Uncategorized Error"
