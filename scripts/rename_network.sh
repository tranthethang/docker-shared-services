#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

OLD_NAME="${1:-infra_shared}"
NEW_NAME="${2:-infra_shared}"

echo "Dry-run replace '${OLD_NAME}' -> '${NEW_NAME}'"
python3 "${ROOT_DIR}/scripts/rename_network.py" --root "${ROOT_DIR}" --old "${OLD_NAME}" --new "${NEW_NAME}"
echo

echo "Applying replace '${OLD_NAME}' -> '${NEW_NAME}'"
python3 "${ROOT_DIR}/scripts/rename_network.py" --root "${ROOT_DIR}" --old "${OLD_NAME}" --new "${NEW_NAME}" --apply
echo

echo "Verifying no remaining '${OLD_NAME}' occurrences..."
python3 "${ROOT_DIR}/scripts/rename_network.py" --root "${ROOT_DIR}" --old "${OLD_NAME}" --new "${NEW_NAME}"
