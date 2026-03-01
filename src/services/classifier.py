import logging
from typing import Any

from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from src.services.llm_factory import get_llm

logger = logging.getLogger(__name__)


class EmailClassificationResult(BaseModel):
    category: str = Field(description="The chosen or newly created category for the email.")
    is_new: bool = Field(description="True if this is a newly created category, False if it matches an existing one.")


class EmailClassifier:
    def __init__(self, existing_labels: list[str] | None = None) -> None:
        self.llm = get_llm()
        self.existing_labels = existing_labels or []

        # We will no longer strictly bind to Literal. The LLM can return any string.
        self.structured_llm = self.llm.with_structured_output(EmailClassificationResult)

        self.prompt = PromptTemplate.from_template(
            """You are an intelligent email categorizer. Your task is to analyze an incoming email and assign it to a category.

### EXISTING CATEGORIES:
{categories_text}

### OPERATIONAL GUIDELINES:
1. Re-use: If the email strongly fits one of the EXISTING CATEGORIES, you MUST use it exactly as written.
2. Creation Limit: If it does not fit, you MAY create a concise, short (1-3 words) new category.
3. Formatting: Categories should be title-cased. e.g "Travel" or "Invoices / Bills".
4. Context Clues: Look at the sender's domain and the subject line as primary indicators before analyzing the body text.

### EMAIL TO ANALYZE:
Sender: {sender}
Subject: {subject}
Body snippet: {snippet}
Body text: {body}

Choose the BEST category for this email."""
        ).partial(categories_text="\n".join(f"- {c}" for c in self.existing_labels) if self.existing_labels else "None")

    def classify_email(self, email_data: dict[str, Any]) -> str:
        """
        Takes raw email dictionary and returns the Category string.
        """
        try:
            chain = self.prompt | self.structured_llm
            result: EmailClassificationResult = chain.invoke(
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
