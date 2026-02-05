#!/bin/bash

set -euo pipefail

PYTHON_MANAGER="python3 bin/service_manager.py"

log_header() { 
  echo ""
  echo "╔════════════════════════════════════════════════════════════════╗"
  echo "║                 Docker Shared Services Manager                 ║"
  echo "╚════════════════════════════════════════════════════════════════╝"
  echo ""
}

log_error() { echo "❌ Error: $*" >&2; }
log_info() { echo "ℹ️  $*"; }

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

main() {
  log_header
  
  SERVICE="${1:-}"
  ACTION="${2:-}"

  # Get services and actions list from python to keep sync
  mapfile -t SERVICES < <($PYTHON_MANAGER --list-services)
  mapfile -t ACTIONS < <($PYTHON_MANAGER --list-actions)

  if [ -z "$SERVICE" ]; then
    log_info "Select a service:"
    echo ""
    local idx=$(show_menu "${SERVICES[@]}")
    SERVICE="${SERVICES[$idx]}"
    echo ""
  fi

  if [ -z "$ACTION" ]; then
    log_info "Select an action for '$SERVICE':"
    echo ""
    local idx=$(show_menu "${ACTIONS[@]}")
    ACTION="${ACTIONS[$idx]}"
    echo ""
  fi

  $PYTHON_MANAGER "$SERVICE" "$ACTION"
}

main "$@"
