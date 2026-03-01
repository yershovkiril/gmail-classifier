# Use the official Python image.
FROM python:3.11-slim

# Set environment variables:
# 1. Force Python stdout and stderr streams to be unbuffered.
ENV PYTHONUNBUFFERED=1
# 2. Prevent uv from using its cache to keep the image small
ENV UV_NO_CACHE=1
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

# Install system dependencies if required (e.g., certificates)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv globally
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create a directory for our application
WORKDIR /app

# Copy dependency files first
COPY pyproject.toml uv.lock ./

# Install the application dependencies into the virtual environment
RUN uv sync --frozen --no-dev --no-install-project

# Copy the rest of the application code
COPY src ./src

# Make sure the virtualenv represents the bin folder explicitly
ENV PATH="/opt/venv/bin:$PATH"

# Run the main script
CMD ["python", "-m", "src.main"]
