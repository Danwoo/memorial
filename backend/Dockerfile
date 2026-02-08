# Backend Dockerfile
# Python 3.11 + FastAPI + uv package manager

FROM python:3.11-slim

WORKDIR /app

# Install uv for fast package management
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --no-dev --link-mode=copy

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Run uvicorn
CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
