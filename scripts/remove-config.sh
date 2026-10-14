#!/usr/bin/env bash
# Remove .env files that have a matching .env.example, after confirmation.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/remove-config.sh [ROOT_DIR]

List every .env next to a .env.example in ROOT_DIR (default: .) and its
immediate subdirectories, ask for confirmation, then delete them.
EOF
}

if [[ $# -gt 1 || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  [[ $# -gt 1 ]] && exit 2
  exit 0
fi

root=${1:-.}

echo "Searching for .env files with a matching .env.example..."
env_files=()
while IFS= read -r -d '' example; do
  env="$(dirname "$example")/.env"
  if [[ -f "$env" ]]; then
    env_files+=("$env")
  fi
done < <(find "$root" -maxdepth 2 -name '.env.example' -print0)

if [[ ${#env_files[@]} -eq 0 ]]; then
  echo "No .env files found."
  exit 0
fi

echo ""
echo "Found ${#env_files[@]} .env file(s):"
printf '  %s\n' "${env_files[@]}"
echo ""
REPLY=""
read -p "Remove these .env files? (y/n) " -n 1 -r || true
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  for f in "${env_files[@]}"; do
    rm -f "$f" && echo "  Removed $f"
  done
  echo ""
  echo "✅ Removed ${#env_files[@]} .env file(s). Run 'make setup' to recreate from .env.example."
else
  echo "Operation cancelled"
fi
