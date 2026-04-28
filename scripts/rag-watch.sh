#!/usr/bin/env bash
set -euo pipefail

uv run python -m local_dev_rag.watcher
