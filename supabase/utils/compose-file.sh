# shellcheck shell=sh
#
# COMPOSE_FILE helpers for run.sh (`run.sh config ...`).
# Sourced by run.sh after it changes into supabase/; not meant to run on its own.
#

# Normalize an override argument:
#   pg17                       -> docker-compose.pg17.yml
#   docker-compose.pg17.yml    -> docker-compose.pg17.yml
#   ./docker-compose.pg17.yml  -> docker-compose.pg17.yml
#   docker-compose.yml         -> error (base file, always implicit)
normalize_override() {
  arg="${1#./}"
  case "$arg" in
    docker-compose.yml)
      echo "ERROR: docker-compose.yml is the base file, always included" >&2
      return 1
      ;;
    docker-compose.*.yml)
      echo "$arg"
      ;;
    *)
      echo "docker-compose.${arg}.yml"
      ;;
  esac
}

# Read COMPOSE_FILE from .env (stripping quotes and CR).
read_compose_file() {
  [ -f .env ] || return 0
  grep '^COMPOSE_FILE=' .env | head -n1 | cut -d= -f2- | tr -d "\r\"'"
}

# Pretty-print the effective compose file list.
print_config() {
  val="$1"
  [ -z "$val" ] && val="docker-compose.yml"
  echo "COMPOSE_FILE=$val"
  echo "compose files:"
  OLD_IFS=$IFS
  IFS=:
  for f in $val; do
    echo "  $f"
  done
  IFS=$OLD_IFS
  echo ""
}

# Update or append COMPOSE_FILE in .env.
write_compose_file() {
  new_value="$1"
  if [ ! -f .env ]; then
    echo "ERROR: .env not found in $(pwd)" >&2
    exit 1
  fi
  new_line="COMPOSE_FILE=$new_value"
  if grep -q '^COMPOSE_FILE=' .env; then
    sed -i.old -e "s|^COMPOSE_FILE=.*$|$new_line|" .env
    rm -f .env.old
  else
    cat >>.env <<EOF

############
# Docker compose override files to layer on top of docker-compose.yml.
# Colon-separated list. Manage with: sh run.sh config add|remove <name>.
#
# Examples:
#   COMPOSE_FILE=docker-compose.yml
#   COMPOSE_FILE=docker-compose.yml:docker-compose.pg17.yml
############
$new_line
EOF
  fi
}
