import argparse
import logging
import sys
import time

from src.config import settings
from src.services.classifier import EmailClassifier
from src.services.gmail import GmailClient
from src.services.cleanup import run_cleanup
from src.services.summary import generate_daily_summary

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

        classifier = EmailClassifier()
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
        if category not in settings.categories and category != "Other":
            logger.warning(f"LLM hallucinated category '{category}'. Falling back to 'Other'.")
            category = "Other"

        # Apply the label
        gmail_client.apply_category_and_mark_processed(message_id, category, email_data.get("labelIds", []))

        # Small delay to avoid hitting rate limits too fast (optional but good practice)
        time.sleep(0.5)

    logger.info("Finished processing batch.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Gmail Agent")
    parser.add_argument(
        "--mode", 
        type=str, 
        choices=["classify", "cleanup", "summary"], 
        default="classify",
        help="Execution mode (classify new emails, cleanup old unread, or generate daily summary)."
    )
    args = parser.parse_args()

    if args.mode == "classify":
        process_emails()
    elif args.mode == "cleanup":
        run_cleanup()
    elif args.mode == "summary":
        generate_daily_summary()
