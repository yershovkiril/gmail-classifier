import base64
from unittest.mock import MagicMock, patch

import pytest

from src.config import settings
from src.services.gmail import GmailClient


import typing

@pytest.fixture
def mock_creds() -> typing.Any:
    with patch("src.services.gmail.Credentials"):
        # Mocking credentials returning from static method or mock object
        mock = MagicMock()
        mock.valid = True
        yield mock

@patch("src.services.gmail.build")
@patch("src.services.gmail.os.path.exists")
@patch("src.services.gmail.Credentials.from_authorized_user_file")
def test_gmail_client_initialization_success(mock_from_file: MagicMock, mock_exists: MagicMock, mock_build: MagicMock, mock_creds: MagicMock) -> None:
    mock_exists.return_value = True
    mock_from_file.return_value = mock_creds

    # Mocking the discovery build return
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Mocking label fetching
    mock_labels_execute = MagicMock()
    mock_labels_execute.return_value = {"labels": [{"name": "INBOX", "id": "Label_1"}]}
    mock_service.users().labels().list().execute = mock_labels_execute

    client = GmailClient()

    assert client.service is not None
    assert "INBOX" in client._label_cache

@patch("src.services.gmail.build")
@patch.object(GmailClient, "_authenticate")
def test_gmail_client_auth_failure(mock_auth: MagicMock, mock_build: MagicMock) -> None:
    mock_auth.return_value = None

    with pytest.raises(ValueError, match="Failed to authenticate"):
        GmailClient()

@patch("src.services.gmail.build")
@patch.object(GmailClient, "_authenticate")
def test_get_emails_to_process(mock_auth: MagicMock, mock_build: MagicMock) -> None:
    mock_creds = MagicMock()
    mock_auth.return_value = mock_creds

    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Setup list messages return
    mock_messages_list = MagicMock()
    mock_messages_list.execute.return_value = {
        "messages": [{"id": "msg1"}, {"id": "msg2"}]
    }
    mock_service.users().messages().list.return_value = mock_messages_list

    # Setup get message return
    mock_get_message = MagicMock()

    # Simulate first message body
    encoded_body = base64.urlsafe_b64encode(b"Test Body").decode("utf-8")
    mock_get_message.execute.side_effect = [
        # Msg 1
        {
            "id": "msg1",
            "snippet": "Test snippet",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "test@example.com"}
                ],
                "body": {"data": encoded_body}
            }
        },
        # Msg 2 (Multipart)
        {
            "id": "msg2",
            "snippet": "Test snippet 2",
            "payload": {
                "headers": [],
                "parts": [
                    {"mimeType": "text/html", "body": {"data": "ignore"}},
                    {"mimeType": "text/plain", "body": {"data": encoded_body}}
                ]
            }
        }
    ]
    mock_service.users().messages().get.return_value = mock_get_message

    # We also have to mock _initialize_labels called during init
    with patch.object(GmailClient, "_initialize_labels"):
        client = GmailClient()
        client.service = mock_service

        emails = client.get_emails_to_process()
        assert len(emails) == 2
        assert emails[0]["id"] == "msg1"
        assert emails[0]["subject"] == "Test Subject"
        assert emails[0]["body"] == "Test Body"

        assert emails[1]["id"] == "msg2"
        assert emails[1]["body"] == "Test Body"

@patch.object(GmailClient, "_authenticate")
def test_apply_category_and_mark_processed(mock_auth: MagicMock) -> None:
    mock_auth.return_value = MagicMock()

    with patch.object(GmailClient, "_initialize_labels"):
        client = GmailClient()
        client.service = MagicMock()

        client._label_cache = {
            "Ads": "label_ads",
            settings.processed_label_name: "label_proc"
        }

        mock_modify = MagicMock()
        client.service.users().messages().modify.return_value = mock_modify

        client.apply_category_and_mark_processed("msg123", "Ads")

        mock_modify.execute.assert_called_once()
