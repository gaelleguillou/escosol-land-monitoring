# Use Python 3.11 slim as base
FROM python:3.13-slim

RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*
# Install uv (the fast Python package installer)
# uv is installed via pip for this Dockerfile, but in production you might use the official uv image
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files first for better Docker layer caching
COPY pyproject.toml .
COPY uv.lock .

# Create a virtual environment and install dependencies with uv
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
RUN uv sync

# Copy the application code
COPY . .

# Create non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run with Gunicorn for production (or python manage.py runserver for dev)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "ae_labeling.wsgi:application"]
