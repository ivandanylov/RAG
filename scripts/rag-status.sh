#!/usr/bin/env bash
set -euo pipefail

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
EMBEDDING_BASE_URL="${EMBEDDING_BASE_URL:-http://localhost:1234/v1}"
QDRANT_API_KEY="${QDRANT_API_KEY:-}"

echo "Qdrant collections:"
if [[ -n "$QDRANT_API_KEY" ]]; then
  curl -s "$QDRANT_URL/collections" -H "api-key: $QDRANT_API_KEY"
else
  curl -s "$QDRANT_URL/collections"
fi
echo
echo

echo "LM Studio models:"
curl -s "$EMBEDDING_BASE_URL/models" || true
echo
