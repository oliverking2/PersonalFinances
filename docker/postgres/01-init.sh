#!/bin/bash
# PostgreSQL initialization script
# Runs on first container start only
#
# The main database and user are created by POSTGRES_USER/POSTGRES_DB env vars.
# This script creates additional databases needed by the application.

set -e

echo "Creating additional databases..."

# Create Dagster database for pipeline metadata
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE dagster;
    GRANT ALL PRIVILEGES ON DATABASE dagster TO $POSTGRES_USER;
EOSQL

echo "Database initialization complete."
