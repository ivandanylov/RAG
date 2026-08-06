#!/usr/bin/env bash
set -euo pipefail

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

EMBEDDING_BASE_URL="${EMBEDDING_BASE_URL:-http://localhost:1234/v1}"
EMBEDDING_API_KEY="${EMBEDDING_API_KEY:-${LM_API_TOKEN:-}}"

docker compose up -d
uv run python -m local_dev_rag.qdrant_admin

if [[ "${ENABLE_RERANK:-true}" == "true" ]]; then
  ./scripts/rag-warmup-reranker.sh
fi

echo "Qdrant is up and collections are ensured."

if [[ -n "$EMBEDDING_API_KEY" ]]; then
  if curl -fsS --max-time 2 "$EMBEDDING_BASE_URL/models" -H "Authorization: Bearer $EMBEDDING_API_KEY" >/dev/null; then
    echo "LM Studio Local Server is reachable."
  else
    echo "LM Studio Local Server is not reachable. Start it before indexing/searching."
  fi
else
  if curl -fsS --max-time 2 "$EMBEDDING_BASE_URL/models" >/dev/null; then
    echo "LM Studio Local Server is reachable."
  else
    echo "LM Studio Local Server is not reachable. Start it before indexing/searching."
  fi
fi
