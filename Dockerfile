# AI-Freelance-Hunter Autonomous Opportunity Hunter Dockerfile
FROM python:3.12-slim

# Prevent python from buffering stdout/stderr and writing .pyc
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create application folders
RUN mkdir -p /app/config /app/data/runs /app/logs

# Copy application source code
COPY config/ /app/config/
COPY src/ /app/src/

# Define persistent storage volumes
VOLUME ["/app/config", "/app/data", "/app/logs"]

# Healthcheck testing heartbeats and repository integrity
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python src/healthcheck.py

# Run autonomous daemon
CMD ["python", "-m", "src.main", "daemon"]
