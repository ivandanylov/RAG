#!/usr/bin/env bash
set -euo pipefail

echo "Warming up FastEmbed reranker..."

uv run python - << 'EOF'
from local_dev_rag.server import get_reranker

get_reranker()

print("Reranker warmup OK")
EOF
