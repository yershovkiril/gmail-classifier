from unittest.mock import MagicMock, patch

from src.main import process_emails


@patch("src.main.GmailClient")
@patch("src.main.EmailClassifier")
def test_process_emails_success(mock_classifier_cls: MagicMock, mock_gmail_cls: MagicMock) -> None:
    mock_gmail = MagicMock()
    mock_classifier = MagicMock()

    mock_gmail_cls.return_value = mock_gmail
    mock_classifier_cls.return_value = mock_classifier

    mock_gmail.get_user_labels.return_value = ["Ads", "Other"]

    # Mock data
    mock_gmail.get_emails_to_process.return_value = [
        {"id": "1", "subject": "Test 1"},
        {"id": "2", "subject": "Test 2"}
    ]
    mock_classifier.classify_email.side_effect = ["Ads", "Other"]

    process_emails()

    # Assert get emails called
    mock_gmail.get_emails_to_process.assert_called_once()

    # Assert classification and labeling occurred for both items
    assert mock_classifier.classify_email.call_count == 2

    # Check that labels were applied properly
    mock_gmail.apply_category_and_mark_processed.assert_any_call("1", "Ads")
    mock_gmail.apply_category_and_mark_processed.assert_any_call("2", "Other")
    assert mock_gmail.apply_category_and_mark_processed.call_count == 2


@patch("src.main.GmailClient")
@patch("src.main.EmailClassifier")
def test_process_emails_empty(mock_classifier_cls: MagicMock, mock_gmail_cls: MagicMock) -> None:
    mock_gmail = MagicMock()
    mock_classifier = MagicMock()

    mock_gmail_cls.return_value = mock_gmail
    mock_classifier_cls.return_value = mock_classifier

    mock_gmail.get_user_labels.return_value = ["Ads"]

    # Return empty list
    mock_gmail.get_emails_to_process.return_value = []
    process_emails()

    mock_gmail.get_emails_to_process.assert_called_once()
    assert mock_classifier.classify_email.call_count == 0
    assert mock_gmail.apply_category_and_mark_processed.call_count == 0


@patch("src.main.GmailClient")
@patch("src.main.EmailClassifier")
def test_process_emails_initialization_error(mock_classifier_cls: MagicMock, mock_gmail_cls: MagicMock) -> None:
    # If a service fails to connect, process gracefully shuts down
    mock_gmail_cls.side_effect = ValueError("OAuth Error")

    # Should not raise exception
    process_emails()
