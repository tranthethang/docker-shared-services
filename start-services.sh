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
OPTIONS="${2:--d}"

print_header() {
  echo ""
  echo "╔════════════════════════════════════════════════════════════════╗"
  echo "║                 Docker Shared Services Manager                 ║"
  echo "╚════════════════════════════════════════════════════════════════╝"
  echo ""
}

print_usage() {
  echo "Usage: ./start-services.sh [command] [options]"
  echo ""
  echo "Commands:"
  echo "  up        Start all services (default)"
  echo "  down      Stop all services"
  echo "  restart   Restart all services"
  echo "  ps        Show status of all services"
  echo "  logs      View logs from all services"
  echo "  pull      Pull latest images"
  echo ""
  echo "Examples:"
  echo "  ./start-services.sh up          # Start all services in background"
  echo "  ./start-services.sh up ''       # Start all services in foreground"
  echo "  ./start-services.sh logs -f    # Follow logs"
  echo "  ./start-services.sh ps          # Show status"
  echo ""
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
  local cmd="docker-compose"
  cmd="$cmd -f docker-compose.shared.yml"
  
  for service in "${SERVICES[@]}"; do
    cmd="$cmd -f $service/docker-compose.yml"
  done
  
  echo "$cmd"
}

main() {
  print_header
  
  case "$COMMAND" in
    up)
      validate_services
      echo ""
      echo "Starting all services..."
      COMPOSE_CMD=$(build_compose_command)
      $COMPOSE_CMD up $OPTIONS
      
      if [ "$OPTIONS" = "-d" ]; then
        echo ""
        echo "✅ All services started successfully!"
        echo ""
        echo "Service Status:"
        $COMPOSE_CMD ps
      fi
      ;;
      
    down)
      echo "Stopping all services..."
      COMPOSE_CMD=$(build_compose_command)
      $COMPOSE_CMD down $OPTIONS
      echo "✅ All services stopped"
      ;;
      
    restart)
      echo "Restarting all services..."
      COMPOSE_CMD=$(build_compose_command)
      $COMPOSE_CMD restart
      echo "✅ All services restarted"
      ;;
      
    ps)
      validate_services
      COMPOSE_CMD=$(build_compose_command)
      echo ""
      echo "Current service status:"
      echo ""
      $COMPOSE_CMD ps
      ;;
      
    logs)
      COMPOSE_CMD=$(build_compose_command)
      $COMPOSE_CMD logs $OPTIONS
      ;;
      
    pull)
      echo "Pulling latest images..."
      COMPOSE_CMD=$(build_compose_command)
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
