#!/bin/bash
set -e

# Run dbt build to create/update views in DuckDB
# Only run for webserver (first container to start) to avoid duplicate runs
if [[ "$1" == "dagster-webserver" ]]; then
    echo "=== Building dbt models ==="
    dbt build --project-dir ./dbt --profiles-dir ./dbt
    echo "=== dbt build complete ==="
fi

# Execute the original command
exec "$@"
