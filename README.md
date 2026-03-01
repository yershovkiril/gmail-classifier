# AI Gmail Classifier

This is an AI Agent that reads UNREAD emails from your Gmail account, classifies them into specific categories using LLMs (defaulting to Google Vertex AI), and labels them accordingly without marking them as read.

## Features
- Fetches exclusively `UNREAD` emails that lack the `PROCESSED_BY_AI` label.
- Uses strict structured output conforming to precise user-defined categories.
- Leaves the email as `UNREAD` but adds `PROCESSED_BY_AI` to ensure it isn't processed repeatedly.
- Supports Vertex AI (Gemini), OpenAI, and Anthropic.

## Local Setup

### 1. Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management.
- A GCP Project with the **Gmail API** enabled, and an **OAuth 2.0 Client ID** (Desktop Application type).

### 2. Configuration & Authentication
1. **Manual Requirement:** The initial Google OAuth Consent setup cannot be easily automated via Terraform. Navigate to the GCP Console -> APIs & Services -> Credentials. Create an "OAuth 2.0 Client ID" (Desktop Application), download the file to the root directory, and name it `credentials.json`.
2. Bootstrap your environment and perform your first authentication flow (which generates `token.json`):
   ```bash
   make install
   make auth
   ```

### 3. Environment Variables (Optional)
Specify your `.env` file or export variables:
```env
LLM_PROVIDER="vertexai" # vertexai (default) | openai | anthropic
LLM_MODEL_NAME="gemini-1.5-pro" # Change if using a different provider

# Example configuration of run limits:
MAX_EMAILS_PER_RUN=50
```

## GCP Production Deployment (CI/CD)

The infrastructure for this project is entirely defined via Terraform and dynamically deployed via Cloud Build.

### 1. Requirements
Ensure your GCP project has the following APIs enabled:
- Cloud Run API
- Cloud Build API
- Artifact Registry API
- Cloud Scheduler API
- Secret Manager API
- Vertex AI API (If using Gemini)

### 2. Deploy infrastructure & Application
Deploying to production takes just a single command. The script will automatically parse your local `credentials.json` and `token.json`, upload them securely to **GCP Secret Manager**, provision the Cloud Run infrastructure, build your image, and trigger the deployment:

```bash
make deploy PROJECT_ID=your-gcp-project-id
```

### 3. Testing
To run the automated test suite locally:
```bash
make test
```
