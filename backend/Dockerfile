FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VIRTUALENVS_CREATE=false

# Basic build deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:${PATH}"

# Copy Poetry files first for caching
COPY pyproject.toml poetry.lock ./

# Install dependencies only (not the project itself)
RUN poetry install --no-interaction --no-ansi --without dev --no-root

# Copy source code
COPY src ./src
COPY scripts ./scripts

# Install the project itself now that source exists
RUN poetry install --no-interaction --no-ansi --without dev --only-root
COPY alembic ./alembic
COPY alembic.ini ./

# Expose port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
