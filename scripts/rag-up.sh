#!/usr/bin/env bash
set -euo pipefail

docker compose up -d
uv run python -m local_dev_rag.qdrant_admin

echo "Qdrant is up and collections are ensured."
echo "Make sure LM Studio Local Server is running before indexing/searching."
