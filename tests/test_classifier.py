from unittest.mock import MagicMock, patch

from src.services.classifier import EmailClassifier


@patch("src.services.classifier.get_llm")
def test_classifier_initialization(mock_get_llm):
    # Mock LLM to prevent real calls
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm

    classifier = EmailClassifier(existing_labels=["Ads", "Invoices / Bills"])
    assert classifier.prompt is not None
    assert classifier.structured_llm is not None

    # Assert dynamic categories are built into the prompt
    formatted = classifier.prompt.format(sender="", subject="", snippet="", body="")
    assert "Ads" in formatted
    assert "Invoices / Bills" in formatted

@patch("src.services.classifier.get_llm")
def test_classify_email_success(mock_get_llm):
    # Setup mock LLM chain invocation
    mock_chain = MagicMock()

    class MockResult:
        category = "Invoices / Bills"

    mock_chain.invoke.return_value = MockResult()

    classifier = EmailClassifier()
    # Replace the actual chain with our mock for this specific test
    classifier.prompt = MagicMock()
    classifier.structured_llm = MagicMock()

    # The chain is combined via | operator so let's mock the whole thing during classify_email
    with patch.object(classifier, 'prompt'):
        # Hacky mock for the pipeline
        mock_pipeline = MagicMock()
        mock_pipeline.invoke.return_value = MockResult()
        classifier.prompt.__or__.return_value = mock_pipeline

        # Test data
        email_data = {
            "id": "123",
            "sender": "billing@example.com",
            "subject": "Your Invoice #445",
            "snippet": "Attached is your invoice...",
            "body": "Invoice detail..."
        }

        result = classifier.classify_email(email_data)
        assert result == "Invoices / Bills"

@patch("src.services.classifier.get_llm")
def test_classify_email_failure_fallback(mock_get_llm):
    classifier = EmailClassifier()

    # Mock chain to throw an exception
    with patch.object(classifier, 'prompt'):
        mock_pipeline = MagicMock()
        # Exception thrown during structured parsing or API call
        mock_pipeline.invoke.side_effect = Exception("API Timeout")
        classifier.prompt.__or__.return_value = mock_pipeline

        result = classifier.classify_email({"id": "err"})

        # Should fallback to the error string
        assert result == "Uncategorized Error"
