#!/bin/bash

set -e

# Path to the python manager
PYTHON_MANAGER="python3 bin/env_manager.py"

print_header() {
  echo ""
  echo "╔════════════════════════════════════════════════════════════════╗"
  echo "║             Docker Services Environment Setup                  ║"
  echo "╚════════════════════════════════════════════════════════════════╝"
  echo ""
}

main() {
  print_header
  
  local command="${1:-all}"
  local service="${2:-all}"
  
  case "$command" in
    all)
      $PYTHON_MANAGER check "all"
      # We handle the interactive part in bash as it's easier for simple Y/N
      echo ""
      read -p "Do you want to create missing .env files from .env.example? (y/n) " -n 1 -r
      echo
      if [[ $REPLY =~ ^[Yy]$ ]]; then
        $PYTHON_MANAGER create "all"
      fi
      $PYTHON_MANAGER validate "all" || true
      $PYTHON_MANAGER summary "all"
      ;;
    check)
      $PYTHON_MANAGER check "$service"
      ;;
    validate)
      $PYTHON_MANAGER validate "$service"
      ;;
    create)
      $PYTHON_MANAGER create "$service"
      ;;
    passwords)
      $PYTHON_MANAGER passwords
      ;;
    summary)
      $PYTHON_MANAGER summary "$service"
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
      echo "Example:"
      echo "  ./setup-env.sh all                # Setup all services"
      echo "  ./setup-env.sh create postgres   # Create .env for PostgreSQL only"
      echo ""
      ;;
    *)
      # Try to see if it's a service name
      $PYTHON_MANAGER check "$command"
      $PYTHON_MANAGER validate "$command" || true
      $PYTHON_MANAGER summary "$command"
      ;;
  esac
}

main "$@"
