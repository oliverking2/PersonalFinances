FROM python:3.11-slim

WORKDIR /app

COPY ./src/dagster/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src/gocardless /app/src/gocardless
COPY ./src/mysql /app/src/mysql
COPY ./src/dagster /app/src/dagster

COPY src/dagster/workspace.yaml /app/workspace.yaml

ENV DAGSTER_HOME=/opt/dagster/dagster_home
RUN mkdir -p $DAGSTER_HOME
COPY src/dagster/dagster.yaml $DAGSTER_HOME/dagster.yaml

EXPOSE 3000
