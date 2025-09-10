FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better caching
COPY pyproject.toml ./

# Install dependencies
RUN pip install -e .

# Copy rest of application code
COPY . .

ENV PYTHONPATH=/app

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 app \
    && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "health_ai_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]