#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:?Usage: ./scripts/rag-index-project.sh <project_id>}"

uv run python -m local_dev_rag.indexer --project-id "$PROJECT_ID"
