#!/bin/bash
set -e

# Idempotent: CREATE DATABASE has no "IF NOT EXISTS" in Postgres, so guard each
# one with a catalog check. The official entrypoint runs this script only while
# initializing an empty data directory. An existing volume does not re-run it.
DATABASES=(temporal sonarqube jenkins gitea inngest zitadel concourse hasura litellm)

for db in "${DATABASES[@]}"; do
    exists=$(psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" -tAc \
        "SELECT 1 FROM pg_database WHERE datname = '${db}'")
    if [[ "$exists" == "1" ]]; then
        echo "  postgres-init: database '${db}' already exists, skipping"
    else
        echo "  postgres-init: creating database '${db}'"
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" \
            -c "CREATE DATABASE ${db};"
    fi
done
