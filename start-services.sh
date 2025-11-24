#!/bin/bash

set -e

SERVICES=(
  "traefik"
  "postgres"
  "mysql8"
  "mongodb"
  "redis"
  "rabbitmq"
  "memcached"
  "mailpit"
  "redisinsight"
  "minio"
  "gitea"
  "sonarqube"
  "jenkins"
  "concourse"
  "act_runner"
  "adminer"
)

COMMAND="${1:-up}"
SERVICE="${2}"
OPTIONS="${3:--d}"

print_header() {
  echo ""
  echo "╔════════════════════════════════════════════════════════════════╗"
  echo "║                 Docker Shared Services Manager                 ║"
  echo "╚════════════════════════════════════════════════════════════════╝"
  echo ""
}

print_usage() {
  echo "Usage: ./start-services.sh [command] [service] [options]"
  echo ""
  echo "Commands:"
  echo "  up        Start services (all by default)"
  echo "  down      Stop services"
  echo "  restart   Restart services"
  echo "  ps        Show status of services"
  echo "  logs      View logs from services"
  echo "  pull      Pull latest images"
  echo ""
  echo "Services (omit to run all):"
  for s in "${SERVICES[@]}"; do
    echo "  $s"
  done
  echo ""
  echo "Examples:"
  echo "  ./start-services.sh up                      # Start all services in background"
  echo "  ./start-services.sh up postgres             # Start only PostgreSQL"
  echo "  ./start-services.sh up postgres ''          # Start PostgreSQL in foreground"
  echo "  ./start-services.sh down redis              # Stop only Redis"
  echo "  ./start-services.sh logs postgres -f        # Follow PostgreSQL logs"
  echo "  ./start-services.sh ps                      # Show status of all services"
  echo ""
}

is_valid_service() {
  local service=$1
  for s in "${SERVICES[@]}"; do
    if [ "$s" = "$service" ]; then
      return 0
    fi
  done
  return 1
}

validate_services() {
  echo "Validating service configurations..."
  for service in "${SERVICES[@]}"; do
    if [ ! -f "$service/docker-compose.yml" ]; then
      echo "❌ Error: $service/docker-compose.yml not found"
      exit 1
    fi
    if [ ! -f "$service/.env.example" ]; then
      echo "⚠️  Warning: $service/.env.example not found"
    fi
  done
  echo "✅ All service configurations are valid"
}

build_compose_command() {
  local cmd="docker compose"
  cmd="$cmd -f docker-compose.shared.yml"
  
  local services_to_use=("${SERVICES[@]}")
  if [ -n "$1" ] && is_valid_service "$1"; then
    services_to_use=("$1")
  fi
  
  for service in "${services_to_use[@]}"; do
    cmd="$cmd -f $service/docker-compose.yml"
  done
  
  echo "$cmd"
}

main() {
  print_header
  
  local service_desc=""
  if [ -n "$SERVICE" ] && is_valid_service "$SERVICE"; then
    service_desc=" ($SERVICE)"
  fi
  
  case "$COMMAND" in
    up)
      validate_services
      echo ""
      echo "Starting services${service_desc}..."
      COMPOSE_CMD=$(build_compose_command "$SERVICE")
      $COMPOSE_CMD up $OPTIONS
      
      if [ "$OPTIONS" = "-d" ]; then
        echo ""
        echo "✅ Services started successfully!"
        echo ""
        echo "Service Status:"
        $COMPOSE_CMD ps
      fi
      ;;
      
    down)
      echo "Stopping services${service_desc}..."
      COMPOSE_CMD=$(build_compose_command "$SERVICE")
      $COMPOSE_CMD down
      echo "✅ Services stopped"
      ;;
      
    restart)
      echo "Restarting services${service_desc}..."
      COMPOSE_CMD=$(build_compose_command "$SERVICE")
      $COMPOSE_CMD restart
      echo "✅ Services restarted"
      ;;
      
    ps)
      validate_services
      COMPOSE_CMD=$(build_compose_command "$SERVICE")
      echo ""
      echo "Current service status${service_desc}:"
      echo ""
      $COMPOSE_CMD ps
      ;;
      
    logs)
      COMPOSE_CMD=$(build_compose_command "$SERVICE")
      $COMPOSE_CMD logs ${OPTIONS:--f}
      ;;
      
    pull)
      echo "Pulling latest images${service_desc}..."
      COMPOSE_CMD=$(build_compose_command "$SERVICE")
      $COMPOSE_CMD pull
      echo "✅ Images pulled successfully"
      ;;
      
    help|--help|-h)
      print_usage
      ;;
      
    *)
      echo "❌ Unknown command: $COMMAND"
      echo ""
      print_usage
      exit 1
      ;;
  esac
}

main "$@"
