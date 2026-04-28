#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:?Usage: ./scripts/rag-clear-project.sh <project_id>}"

uv run python -m local_dev_rag.clear_project "$PROJECT_ID"
