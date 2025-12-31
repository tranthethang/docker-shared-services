#!/bin/bash

set -euo pipefail

readonly SERVICES=(
  "act_runner" "adminer" "concourse" "dockge" "gitea" "jenkins"
  "mailpit" "mariadb" "memcached" "minio" "mongodb" "mysql8"
  "portainer" "postgres" "rabbitmq" "redis" "redisinsight" "sonarqube" "traefik"
)
readonly ACTIONS=("up" "down" "restart" "logs")

SERVICE="${1:-}"
ACTION="${2:-}"

log_header() { 
  echo ""
  echo "╔════════════════════════════════════════════════════════════════╗"
  echo "║                 Docker Shared Services Manager                 ║"
  echo "╚════════════════════════════════════════════════════════════════╝"
  echo ""
}
log_error() { echo "❌ Error: $*" >&2; }
log_info() { echo "ℹ️  $*"; }
log_success() { echo "✅ $*"; }

is_valid_service() {
  local service=$1
  for s in "${SERVICES[@]}"; do
    [ "$s" = "$service" ] && return 0
  done
  return 1
}

is_valid_action() {
  local action=$1
  for a in "${ACTIONS[@]}"; do
    [ "$a" = "$action" ] && return 0
  done
  return 1
}

show_menu() {
  local items=("$@")
  local choice
  local max=${#items[@]}
  
  for i in "${!items[@]}"; do
    printf "  [%d] %s\n" $((i+1)) "${items[$i]}"
  done >&2
  
  echo "" >&2
  while true; do
    read -p "Select [1-$max] or [q]uit: " choice < /dev/tty
    
    case "$choice" in
      q|Q)
        exit 0
        ;;
      *)
        if [[ $choice =~ ^[0-9]+$ ]] && [ $choice -ge 1 ] && [ $choice -le $max ]; then
          echo $((choice-1))
          return 0
        else
          log_error "Invalid selection. Please enter 1-$max or 'q'" >&2
        fi
        ;;
    esac
  done
}

ensure_network() {
  if ! docker network inspect dev_tools >/dev/null 2>&1; then
    log_info "Creating network dev_tools..."
    docker network create dev_tools --subnet 10.0.0.0/16 --driver bridge
    log_success "Network dev_tools created"
  fi
}

build_compose_cmd() {
  local service=$1
  local cmd="docker compose -f docker-compose.shared.yml -f $service/docker-compose.yml"
  echo "$cmd"
}

execute_action() {
  local service=$1
  local action=$2
  local cmd=$(build_compose_cmd "$service")
  
  case "$action" in
    up)
      ensure_network
      log_success "Starting $service..."
      echo ""
      $cmd up -d
      echo ""
      log_success "$service started successfully"
      ;;
    down)
      log_info "Stopping $service..."
      $cmd down
      log_success "$service stopped"
      ;;
    restart)
      log_info "Restarting $service..."
      $cmd restart
      log_success "$service restarted"
      ;;
    logs)
      log_info "Displaying logs for $service (press Ctrl+C to exit)..."
      echo ""
      $cmd logs -f
      ;;
  esac
}

main() {
  log_header
  
  if [ -z "$SERVICE" ]; then
    log_info "Select a service:"
    echo ""
    local idx=$(show_menu "${SERVICES[@]}")
    SERVICE="${SERVICES[$idx]}"
    echo ""
  fi
  
  if ! is_valid_service "$SERVICE"; then
    log_error "Unknown service: $SERVICE"
    echo ""
    echo "Available services:"
    printf "  %s\n" "${SERVICES[@]}" | column -c 60
    exit 1
  fi
  
  if [ -z "$ACTION" ]; then
    log_info "Select an action for '$SERVICE':"
    echo ""
    local idx=$(show_menu "${ACTIONS[@]}")
    ACTION="${ACTIONS[$idx]}"
    echo ""
  fi
  
  if ! is_valid_action "$ACTION"; then
    log_error "Unknown action: $ACTION"
    echo "Available actions: ${ACTIONS[*]}"
    exit 1
  fi
  
  execute_action "$SERVICE" "$ACTION"
}

main "$@"
