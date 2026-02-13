#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
    CREATE DATABASE temporal;
    CREATE DATABASE sonarqube;
    CREATE DATABASE jenkins;
    CREATE DATABASE gitea;
    CREATE DATABASE keycloak;
    CREATE DATABASE concourse;
EOSQL
