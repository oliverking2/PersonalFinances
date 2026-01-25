FROM python:3.12-slim

WORKDIR /opt/dagster/dagster_home

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DAGSTER_HOME=/opt/dagster/dagster_home \
    POETRY_VIRTUALENVS_CREATE=false

# Basic build deps (only needed if you install packages with C extensions)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:${PATH}"

# Copy Poetry files first for caching
COPY backend/pyproject.toml backend/poetry.lock ./

# Install dependencies only (not the project itself)
RUN poetry install --no-interaction --no-ansi --no-root

# Copy Dagster config
COPY backend/setup/dagster/dagster.yaml ./dagster.yaml
COPY backend/setup/dagster/workspace.yaml ./workspace.yaml

# Copy your code
COPY backend/src ./src
COPY backend/scripts ./scripts
COPY backend/dbt ./dbt

# Install the project itself now that source exists
RUN poetry install --no-interaction --no-ansi --only-root

# Parse dbt project to generate manifest.json (required by dagster-dbt)
RUN poetry run dbt parse --project-dir ./dbt --profiles-dir ./dbt
