#!/usr/bin/env bash
set -euo pipefail

docker compose down
docker compose up -d
uv run python -m local_dev_rag.qdrant_admin

echo "RAG stack restarted."
