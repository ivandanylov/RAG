#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:-customui}"

TEST_PROJECT_ID="$PROJECT_ID" uv run pytest -v
