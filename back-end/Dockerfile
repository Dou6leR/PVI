FROM python:3.13-slim

WORKDIR /app

# Install system build dependencies (build-essential provides gcc, make, libc6-dev with standard C headers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official pre-built image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency specifications
COPY pyproject.toml ./

# Ensure README.md exists
RUN touch README.md

# Install project dependencies into system Python using uv
ENV UV_SYSTEM_PYTHON=1
RUN uv pip install --no-cache -r pyproject.toml

# Copy application source code
COPY app/ ./app/

# Ensure internal packages (core, api) are resolvable from /app/app
ENV PYTHONPATH=/app/app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--app-dir", "app", "--host", "0.0.0.0", "--port", "8000"]
