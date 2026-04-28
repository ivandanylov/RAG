#!/usr/bin/env bash
set -euo pipefail

echo "This will delete local Qdrant data."
read -r -p "Type DELETE to continue: " CONFIRM

if [[ "$CONFIRM" != "DELETE" ]]; then
  echo "Cancelled."
  exit 1
fi

docker compose down
rm -rf data/qdrant
docker compose up -d
uv run python -m local_dev_rag.qdrant_admin

echo "All Qdrant data deleted and collections recreated."
