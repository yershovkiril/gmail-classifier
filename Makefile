.PHONY: install auth deploy test

PROJECT_ID ?= YOUR_PROJECT_ID

help:
	@echo "Available commands:"
	@echo "  make install  - Install project dependencies using uv"
	@echo "  make auth     - Run the application locally to easily trigger the Gmail OAuth flow"
	@echo "  make test     - Run the automated test suite with coverage reporting"
	@echo "  make deploy PROJECT_ID=<your-project> - Provision GCP architecture and trigger Cloud Build"

install:
	@echo "Installing dependencies..."
	uv sync

auth:
	@echo "Running local auth flow to generate token.json..."
	uv run python -m src.main

deploy:
	@if [ "$(PROJECT_ID)" = "YOUR_PROJECT_ID" ]; then \
		echo "Error: Please specify PROJECT_ID. Usage: make deploy PROJECT_ID=my-gcp-project"; \
		exit 1; \
	fi
	@echo "1. Provisioning base infrastructure (APIs and Artifact Registry) via Terraform..."
	cd terraform && terraform init && terraform apply -target="google_artifact_registry_repository.repo" -target="google_project_service.apis" -var="project_id=$(PROJECT_ID)" -auto-approve
	@echo "2. Building and pushing real container image via Cloud Build..."
	gcloud builds submit --config cloudbuild.yaml --substitutions=COMMIT_SHA=$$(git rev-parse --short HEAD) --project=$(PROJECT_ID) .
	@echo "3. Deploying Cloud Run Job and Cloud Scheduler with latest image..."
	cd terraform && terraform apply -var="project_id=$(PROJECT_ID)" -auto-approve

test:
	@echo "Running tests..."
	uv run pytest --cov=src --cov-report=term-missing
