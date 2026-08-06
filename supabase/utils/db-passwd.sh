#!/bin/sh
#
# Rotate Postgres role passwords to match a new POSTGRES_PASSWORD.
# Adapted for the minimal stack (no analytics / pooler schemas).
#

set -e

if ! docker compose version > /dev/null 2>&1; then
    echo "Docker Compose not found."
    exit 1
fi

if [ ! -f .env ]; then
    echo "Missing .env file. Exiting."
    exit 1
fi

new_passwd="$(openssl rand -hex 16)"

compose_output=$(docker compose ps \
  --format '{{.Image}}\t{{.Service}}\t{{.Status}}' 2>/dev/null | \
  grep -m1 '^supabase/postgres:' || true)

if [ -z "$compose_output" ]; then
    echo "Postgres container not found. Exiting."
    exit 1
fi

db_image=$(echo "$compose_output" | cut -f1)
db_srv_name=$(echo "$compose_output" | cut -f2)
db_srv_status=$(echo "$compose_output" | cut -f3)

case "$db_srv_status" in
    Up*) ;;
    *)
        echo "Postgres container status: $db_srv_status"
        echo "Exiting."
        exit 1
        ;;
esac

db_admin_user="supabase_admin"

echo ""
echo "*** Check configuration before updating database passwords ***"
echo "Service: $db_srv_name ($db_srv_status)"
echo "Image:   $db_image"
echo "Admin:   $db_admin_user"
echo ""

if ! test -t 0; then
    echo "Running non-interactively. Not updating passwords."
    exit 0
fi

echo "New database password: $new_passwd"
echo ""
printf "Update database passwords? (y/N) "
read -r REPLY
case "$REPLY" in
    [Yy]) ;;
    *)
        echo "Canceled."
        exit 0
        ;;
esac

echo "Updating passwords..."

docker compose exec -T "$db_srv_name" psql -U "$db_admin_user" -d "postgres" -v ON_ERROR_STOP=1 <<EOF
alter user anon with password '${new_passwd}';
alter user authenticated with password '${new_passwd}';
alter user authenticator with password '${new_passwd}';
alter user dashboard_user with password '${new_passwd}';
alter user pgbouncer with password '${new_passwd}';
alter user postgres with password '${new_passwd}';
alter user service_role with password '${new_passwd}';
alter user supabase_admin with password '${new_passwd}';
alter user supabase_auth_admin with password '${new_passwd}';
alter user supabase_functions_admin with password '${new_passwd}';
alter user supabase_replication_admin with password '${new_passwd}';
alter user supabase_storage_admin with password '${new_passwd}';
EOF

echo "Updating POSTGRES_PASSWORD in .env..."
sed -i.old "s|^POSTGRES_PASSWORD=.*$|POSTGRES_PASSWORD=$new_passwd|" .env

echo ""
echo "Success. Recreate containers:"
echo "  docker compose up -d --force-recreate"
echo ""
