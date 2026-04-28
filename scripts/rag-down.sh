#!/usr/bin/env bash
set -euo pipefail

docker compose down

echo "Qdrant container stopped. Persistent data is kept in data/qdrant/."
