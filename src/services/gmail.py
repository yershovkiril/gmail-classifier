import base64
import logging
import os.path
from typing import Any

from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.config import settings

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify", "https://www.googleapis.com/auth/gmail.compose"]


class GmailClient:
    SYSTEM_LABELS = {
        "INBOX", "UNREAD", "SENT", "DRAFT", "SPAM", "TRASH", "STARRED", 
        "IMPORTANT", "CHAT", "CATEGORY_PERSONAL", "CATEGORY_SOCIAL", 
        "CATEGORY_PROMOTIONS", "CATEGORY_UPDATES", "CATEGORY_FORUMS"
    }

    def __init__(self) -> None:
        self.creds = self._authenticate()
        if not self.creds:
            raise ValueError("Failed to authenticate with Gmail API.")
        self.service = build("gmail", "v1", credentials=self.creds)
        self._label_cache: dict[str, str] = {}
        self._initialize_labels()

    def _authenticate(self) -> Credentials | None:
        creds = None
        if os.path.exists(settings.gmail_token_file):
            creds = Credentials.from_authorized_user_file(settings.gmail_token_file, SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.gmail_credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            try:
                with open(settings.gmail_token_file, "w") as token:
                    token.write(creds.to_json())
            except (OSError, PermissionError) as e:
                logger.warning(f"Could not save refreshed token to {settings.gmail_token_file} (likely read-only mounted secret): {e}")
        return creds # type: ignore

    def _initialize_labels(self) -> None:
        """
        Fetches all labels and caches their IDs.
        If essential labels (like PROCESSED_BY_AI) don't exist, it creates them.
        """
        try:
            results = self.service.users().labels().list(userId="me").execute()
            labels = results.get("labels", [])
            for label in labels:
                self._label_cache[label["name"]] = label["id"]

            self.get_or_create_label(settings.processed_label_name)
        except HttpError as error:
            logger.error(f"An error occurred fetching labels: {error}")

    def get_or_create_label(self, label_name: str) -> str:
        """Returns the ID of the label, creating it if necessary."""
        if label_name in self._label_cache:
            return self._label_cache[label_name]

        try:
            label_obj = {
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
            created_label = (
                self.service.users().labels().create(userId="me", body=label_obj).execute()
            )
            self._label_cache[label_name] = created_label["id"]
            logger.info(f"Created new label: {label_name}")
            return str(created_label["id"])
        except HttpError as error:
            logger.error(f"An error occurred creating label {label_name}: {error}")
            raise error

    def get_emails_to_process(self, max_results: int = 10) -> list[dict[str, Any]]:
        """
        Queries for UNREAD emails that DO NOT HAVE the PROCESSED_BY_AI label.
        """
        processed_label = settings.processed_label_name
        query = f"is:unread -label:{processed_label}"

        try:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
            messages = results.get("messages", [])

            email_data = []
            for msg in messages:
                full_msg = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=msg["id"], format="full")
                    .execute()
                )
                email_data.append(self._parse_message(full_msg))
            return email_data
        except HttpError as error:
            logger.error(f"An error occurred fetching messages: {error}")
            return []

    def _parse_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """Parses the raw Gmail message dictionary into a simpler format."""
        payload = message.get("payload", {})
        headers = payload.get("headers", [])

        subject = ""
        sender = ""
        for header in headers:
            if header["name"].lower() == "subject":
                subject = header["value"]
            if header["name"].lower() == "from":
                sender = header["value"]

        body = self._get_body(payload)

        return {
            "id": message["id"],
            "labelIds": message.get("labelIds", []),
            "subject": subject,
            "sender": sender,
            "body": body,
            "snippet": message.get("snippet", ""),
        }

    def _get_body(self, payload: dict[str, Any]) -> str:
        """Recursively extracts the plain text body from the payload."""
        if "data" in payload.get("body", {}):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                if part.get("mimeType") == "multipart/alternative":
                    return self._get_body(part)
        return ""

    def get_user_labels(self) -> list[str]:
        """Returns a list of label names representing user-created categories."""
        # Filter out built-in gmail system labels (which are usually UPPERCASE like INBOX, UNREAD, SENT)
        # and our own processed tracker.
        user_labels = []
        for name in self._label_cache.keys():
            if name not in self.SYSTEM_LABELS and name != settings.processed_label_name:
                user_labels.append(name)
        return user_labels

    def apply_category_and_mark_processed(self, message_id: str, category_name: str, existing_label_ids: list[str] = None) -> None:
        """
        Adds the category label and the PROCESSED_BY_AI label to the message.
        Also strips out previous custom tags.
        """
        try:
            category_label_id = self.get_or_create_label(category_name)
            processed_label_id = self.get_or_create_label(settings.processed_label_name)

            labels_to_remove = []
            
            # Remove any pre-existing custom user labels
            if existing_label_ids:
                user_label_ids = {l_id for name, l_id in self._label_cache.items() if name not in self.SYSTEM_LABELS}
                for l_id in existing_label_ids:
                    if l_id in user_label_ids and l_id not in (category_label_id, processed_label_id):
                        labels_to_remove.append(l_id)

            body = {
                "addLabelIds": [category_label_id, processed_label_id],
                "removeLabelIds": labels_to_remove,
            }

            self.service.users().messages().modify(userId="me", id=message_id, body=body).execute()
            logger.info(
                f"Successfully processed message {message_id} with category {category_name}."
            )

        except HttpError as error:
            logger.error(f"An error occurred modifying message {message_id}: {error}")

    def get_recent_emails(self, hours: int = 24) -> list[dict[str, Any]]:
        """
        Queries for all emails received in the last N hours, regardless of label.
        """
        query = f"newer_than:{hours}h"

        try:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=500)
                .execute()
            )
            messages = results.get("messages", [])

            email_data = []
            for msg in messages:
                full_msg = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=msg["id"], format="full")
                    .execute()
                )
                email_data.append(self._parse_message(full_msg))
            return email_data
        except HttpError as error:
            logger.error(f"An error occurred fetching recent messages: {error}")
            return []

    def send_email(self, subject: str, html_body: str) -> None:
        """Sends an HTML email to the authenticated user's own address."""
        # Get the authenticated user's email address
        profile = self.service.users().getProfile(userId="me").execute()
        user_email = profile.get("emailAddress", "me")

        message = EmailMessage()
        message.set_content(html_body, subtype="html")
        message["To"] = user_email
        message["From"] = user_email
        message["Subject"] = subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": encoded_message}

        try:
            self.service.users().messages().send(userId="me", body=create_message).execute()
            logger.info(f"Successfully sent summary email to {user_email}")
        except HttpError as error:
            logger.error(f"Failed to send email: {error}")
