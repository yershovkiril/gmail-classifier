import logging
import sys
import time

from src.config import settings
from src.services.classifier import EmailClassifier
from src.services.gmail import GmailClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def process_emails() -> None:
    logger.info("Initializing Gmail Client and LLM Classifier...")
    try:
        gmail_client = GmailClient()

        user_labels = gmail_client.get_user_labels()
        logger.info(f"Retrieved {len(user_labels)} existing user labels from Gmail.")

        classifier = EmailClassifier(existing_labels=user_labels)
    except Exception as e:
        logger.critical(f"Failed to initialize services: {e}")
        return

    logger.info(f"Fetching up to {settings.max_emails_per_run} unread emails...")
    emails = gmail_client.get_emails_to_process(max_results=settings.max_emails_per_run)

    if not emails:
        logger.info("No new unread emails to process.")
        return

    logger.info(f"Found {len(emails)} emails. Starting categorization...")

    for count, email_data in enumerate(emails, start=1):
        message_id = email_data["id"]
        subject = email_data.get("subject", "No Subject")

        logger.info(f"Processing ({count}/{len(emails)}): {subject}")

        # Classify the email
        category = classifier.classify_email(email_data)

        # Enforce Boundary conditions for custom category generation
        if category not in user_labels:
            if len(user_labels) >= settings.max_dynamic_categories:
                logger.warning(f"Maximum dynamic categories ({settings.max_dynamic_categories}) reached. Falling back to 'Other'.")
                category = "Other"
            else:
                logger.info(f"Creating new category: {category}")
                user_labels.append(category)

        # Apply the label
        gmail_client.apply_category_and_mark_processed(message_id, category)

        # Small delay to avoid hitting rate limits too fast (optional but good practice)
        time.sleep(0.5)

    logger.info("Finished processing batch.")


if __name__ == "__main__":
    process_emails()
