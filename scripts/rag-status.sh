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
EMBEDDING_API_KEY="${EMBEDDING_API_KEY:-${LM_API_TOKEN:-}}"

echo "Qdrant collections:"
if [[ -n "$QDRANT_API_KEY" ]]; then
  curl -s "$QDRANT_URL/collections" -H "api-key: $QDRANT_API_KEY"
else
  curl -s "$QDRANT_URL/collections"
fi
echo
echo

echo "LM Studio models:"
if [[ -n "$EMBEDDING_API_KEY" ]]; then
  curl -s "$EMBEDDING_BASE_URL/models" -H "Authorization: Bearer $EMBEDDING_API_KEY" || true
else
  curl -s "$EMBEDDING_BASE_URL/models" || true
fi
echo
