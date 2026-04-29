#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:-customui}"

if [[ "${ENABLE_RERANK:-true}" == "true" ]]; then
  ./scripts/rag-warmup-reranker.sh
fi

TEST_PROJECT_ID="$PROJECT_ID" uv run pytest -v
