FROM python:3.12-slim

WORKDIR /opt/dagster/dagster_home

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DAGSTER_HOME=/opt/dagster_home \
    POETRY_VIRTUALENVS_CREATE=false

# Basic build deps (only needed if you install packages with C extensions)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:${PATH}"

# Copy Poetry files first for caching
COPY pyproject.toml poetry.lock ./

# Install dependencies (no venv because POETRY_VIRTUALENVS_CREATE=false)
RUN poetry install --no-interaction --no-ansi --with dagster

# Copy Dagster config
COPY setup/dagster/dagster.yaml /opt/dagster/dagster_home/dagster.yaml
COPY setup/dagster/workspace.yaml /opt/dagster/dagster_home/workspace.yaml

# Copy your code
COPY src ./src
COPY dbt ./dbt

RUN poetry run dbt parse --project-dir ./dbt --profiles-dir ./dbt
