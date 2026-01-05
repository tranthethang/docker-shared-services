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
  "portainer"
  "redisinsight"
  "minio"
  "gitea"
  "sonarqube"
  "jenkins"
  "concourse"
  "act_runner"
  "adminer"
)

print_header() {
  echo ""
  echo "╔════════════════════════════════════════════════════════════════╗"
  echo "║             Docker Services Environment Setup                  ║"
  echo "╚════════════════════════════════════════════════════════════════╝"
  echo ""
}

check_env_files() {
  local services_to_check=("${SERVICES[@]}")
  if [ "$1" != "all" ] && [ -n "$1" ]; then
    services_to_check=("$1")
  fi
  
  echo "Checking .env files..."
  echo ""
  
  missing_count=0
  for service in "${services_to_check[@]}"; do
    if [ -f "$service/.env" ]; then
      echo "✅ $service/.env exists"
    elif [ -f "$service/.env.example" ]; then
      echo "⚠️  $service/.env missing (only .env.example exists)"
      ((missing_count++))
    else
      echo "❌ $service/.env.example not found"
    fi
  done
  
  echo ""
  if [ $missing_count -gt 0 ]; then
    echo "Found $missing_count services missing .env files"
    echo ""
    read -p "Do you want to create .env files from .env.example? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      create_env_files "$1"
    fi
  fi
}

create_env_files() {
  local services_to_create=("${SERVICES[@]}")
  if [ "$1" != "all" ] && [ -n "$1" ]; then
    services_to_create=("$1")
  fi
  
  echo ""
  echo "Creating .env files from .env.example..."
  echo ""
  
  for service in "${services_to_create[@]}"; do
    if [ -f "$service/.env.example" ] && [ ! -f "$service/.env" ]; then
      cp "$service/.env.example" "$service/.env"
      echo "✅ Created $service/.env"
    fi
  done
  
  echo ""
  echo "✅ .env files created successfully!"
  echo ""
  echo "⚠️  Remember to update password and sensitive values in .env files!"
}

validate_env_vars() {
  local services_to_validate=("${SERVICES[@]}")
  if [ "$1" != "all" ] && [ -n "$1" ]; then
    services_to_validate=("$1")
  fi
  
  echo ""
  echo "Validating environment variables..."
  echo ""
  
  errors=0
  
  for service in "${services_to_validate[@]}"; do
    if [ ! -f "$service/.env" ]; then
      continue
    fi
    
    case "$service" in
      postgres|mysql8|mongodb)
        if ! grep -q "PASSWORD" "$service/.env"; then
          echo "❌ $service: Missing PASSWORD variable"
          ((errors++))
        else
          echo "✅ $service: PASSWORD configured"
        fi
        ;;
      rabbitmq)
        if ! grep -q "RABBITMQ_PASSWORD" "$service/.env"; then
          echo "❌ $service: Missing RABBITMQ_PASSWORD variable"
          ((errors++))
        else
          echo "✅ $service: RABBITMQ_PASSWORD configured"
        fi
        ;;
      minio)
        if ! grep -q "MINIO_ROOT_PASSWORD" "$service/.env"; then
          echo "❌ $service: Missing MINIO_ROOT_PASSWORD variable"
          ((errors++))
        else
          echo "✅ $service: MINIO_ROOT_PASSWORD configured"
        fi
        ;;
    esac
  done
  
  if [ $errors -gt 0 ]; then
    echo ""
    echo "❌ Found $errors validation errors"
    return 1
  else
    echo ""
    echo "✅ All environment variables validated!"
    return 0
  fi
}

generate_strong_passwords() {
  echo ""
  echo "Generating strong passwords..."
  echo ""
  
  if command -v openssl &> /dev/null; then
    echo "Generated strong passwords (save these):"
    echo ""
    echo "PASSWORD_102: $(openssl rand -base64 32)"
    echo ""
    echo "You can update .env files with these passwords"
  else
    echo "⚠️  openssl not found. Generate passwords manually."
    echo "Example: openssl rand -base64 32"
  fi
}

show_services_summary() {
  local services_to_show=("${SERVICES[@]}")
  if [ "$1" != "all" ] && [ -n "$1" ]; then
    services_to_show=("$1")
  fi
  
  echo ""
  echo "╔════════════════════════════════════════════════════════════════╗"
  echo "║                   Services Configuration                       ║"
  echo "╚════════════════════════════════════════════════════════════════╝"
  echo ""
  
  for service in "${services_to_show[@]}"; do
    if [ -f "$service/.env" ]; then
      echo "Service: $service"
      
      case "$service" in
        postgres)
          grep "POSTGRES_PORT\|POSTGRES_DB" "$service/.env" | sed 's/^/  /' || echo "  (no ports configured)"
          ;;
        mysql8)
          grep "MYSQL_PORT\|MYSQL_DATABASE" "$service/.env" | sed 's/^/  /' || echo "  (no ports configured)"
          ;;
        mongodb)
          grep "MONGO_PORT" "$service/.env" | sed 's/^/  /' || echo "  (no ports configured)"
          ;;
        redis)
          grep "REDIS_PORT" "$service/.env" | sed 's/^/  /' || echo "  (no ports configured)"
          ;;
        traefik)
          echo "  Ports: 80, 443, 8080"
          ;;
        gitea)
          grep "GITEA_HTTP_PORT\|GITEA_SSH_PORT" "$service/.env" | sed 's/^/  /' || echo "  (no ports configured)"
          ;;
        sonarqube)
          grep "SONARQUBE_PORT" "$service/.env" | sed 's/^/  /' || echo "  (no ports configured)"
          ;;
        *)
          echo "  (configured)"
          ;;
      esac
      
      echo ""
    fi
  done
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

main() {
  print_header
  
  local command="${1:-all}"
  local service="${2}"
  
  case "$command" in
    all)
      check_env_files "all"
      validate_env_vars "all" || true
      show_services_summary "all"
      ;;
    check)
      check_env_files "$service"
      ;;
    validate)
      validate_env_vars "$service"
      ;;
    create)
      create_env_files "$service"
      ;;
    passwords)
      generate_strong_passwords
      ;;
    summary)
      show_services_summary "$service"
      ;;
    help|--help|-h)
      echo "Usage: ./setup-env.sh [command] [service]"
      echo ""
      echo "Commands:"
      echo "  all                    Run all checks and create missing .env files for all services"
      echo "  check [service]        Check .env files (if service specified, check only that service)"
      echo "  create [service]       Create .env files from .env.example"
      echo "  validate [service]     Validate environment variables"
      echo "  passwords              Generate strong passwords"
      echo "  summary [service]      Show services configuration summary"
      echo ""
      echo "Services:"
      for s in "${SERVICES[@]}"; do
        echo "  - $s"
      done
      echo ""
      echo "Examples:"
      echo "  ./setup-env.sh all                # Setup all services"
      echo "  ./setup-env.sh create postgres   # Create .env for PostgreSQL only"
      echo "  ./setup-env.sh validate redis    # Validate Redis .env"
      echo ""
      ;;
    *)
      if is_valid_service "$command"; then
        check_env_files "$command"
        validate_env_vars "$command" || true
        show_services_summary "$command"
      else
        echo "Unknown command: $command"
        echo "Use './setup-env.sh help' for usage information"
        exit 1
      fi
      ;;
  esac
}

main "$@"
