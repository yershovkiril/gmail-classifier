import logging
from typing import Any
from googleapiclient.errors import HttpError

from src.config import settings
from src.services.gmail import GmailClient

logger = logging.getLogger(__name__)

def run_cleanup() -> None:
    """
    Finds unread emails older than `keep_unread_days` and marks them as read.
    """
    logger.info(f"Starting cleanup task for emails older than {settings.keep_unread_days} days...")
    
    try:
        gmail_client = GmailClient()
    except Exception as e:
        logger.critical(f"Failed to initialize Gmail Client for cleanup: {e}")
        return

    # Gmail query syntax for age
    query = f"is:unread older_than:{settings.keep_unread_days}d"
    
    try:
        total_cleaned = 0
        while True:
            # We can paginate through all results for cleanup, no strict max_results needed
            results = gmail_client.service.users().messages().list(userId="me", q=query, maxResults=500).execute()
            messages = results.get("messages", [])
            
            if not messages:
                if total_cleaned == 0:
                    logger.info("No old unread emails found to clean up.")
                else:
                    logger.info(f"Cleanup complete. Successfully marked {total_cleaned} old emails as read overall.")
                return

            logger.info(f"Found {len(messages)} old unread emails in this sweep. Stripping UNREAD label...")
            
            # We can use batch modify API for efficiency
            message_ids = [msg["id"] for msg in messages]
            
            # Process in chunks of 500 (Gmail API batch limit is typically 1000, but 500 is safe)
            body = {
                "ids": message_ids,
                "removeLabelIds": ["UNREAD"],
            }
            
            gmail_client.service.users().messages().batchModify(userId="me", body=body).execute()
            
            total_cleaned += len(message_ids)
            logger.info(f"Successfully marked {len(message_ids)} emails as read. (Total: {total_cleaned})")

    except HttpError as error:
        logger.error(f"An error occurred during cleanup: {error}")
