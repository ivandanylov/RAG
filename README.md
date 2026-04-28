# local-dev-rag

Reusable local multi-project RAG stack for development agents.

This project provides one local RAG subsystem for multiple software projects. It uses:

- **Qdrant** as a local vector database
- **LM Studio** as a local OpenAI-compatible embeddings endpoint
- **FastMCP** as an MCP server for Cursor / VS Code / Roo Code
- **uv** for Python dependency and environment management
- **watchfiles** for real-time reindexing during development

The goal is to let AI agents search project documentation, architecture decisions, API specs, database migrations, and source code before making changes.

---

## 1. Architecture

```text
Cursor / VS Code + Roo Code / Continue
        |
        | MCP tools
        v
local-dev-rag MCP server
        |
        | semantic search
        v
Qdrant
  - rag_docs_knowledge
  - rag_code_knowledge
        ^
        |
Indexer / Watcher
        ^
        |
Project files
  - docs
  - ADR
  - OpenAPI specs
  - source code
  - migrations
```

Collections:

```text
rag_docs_knowledge  -> documentation, ADR, architecture, design system, OpenAPI specs
rag_code_knowledge  -> source code, migrations, tests, frontend/backend implementation
```

Each indexed chunk contains metadata:

```text
project_id
project_name
workspace_path
knowledge_type
reusable_scope
source_path
language
module
content_hash
content
```

---

## 2. What must be running

For full RAG operation, the following must be running:

```text
1. Docker
2. Qdrant container
3. LM Studio Local Server
4. Embedding model loaded in LM Studio
5. Optional: watcher process
6. Optional: MCP server started by Cursor/Roo
```

Minimum for indexing:

```text
Docker + Qdrant + LM Studio embeddings endpoint
```

Minimum for MCP search from Cursor/Roo:

```text
Qdrant + LM Studio embeddings endpoint + MCP server
```

---

## 3. Initial setup

### 3.1 Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
uv --version
```

### 3.2 Install dependencies

From the root of this project:

```bash
uv sync
```

If dependencies are missing:

```bash
uv add fastmcp qdrant-client openai python-dotenv pydantic pyyaml watchfiles
uv add --dev pytest
```

### 3.3 Create `.env`

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

Example:

```env
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=replace-with-local-secret

DOCS_COLLECTION=rag_docs_knowledge
CODE_COLLECTION=rag_code_knowledge

EMBEDDING_BASE_URL=http://localhost:1234/v1
EMBEDDING_API_KEY=lm-studio
EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5

PROJECTS_CONFIG=./config/projects.yaml
```

Generate a local Qdrant key:

```bash
openssl rand -hex 32
```

Use the same key in `.env` and `docker-compose.yml`.

---

## 4. Configure projects

Projects are defined in:

```text
config/projects.yaml
```

Example:

```yaml
projects:
  - project_id: customui
    project_name: CustomUI
    workspace_path: /absolute/path/to/customui
    tags:
      - fastapi
      - react
      - typescript
      - postgresql
      - redis
      - docker
    docs:
      include:
        - docs/**/*.md
        - docs/**/*.json
        - infra/**/*.md
        - ops/**/*.md
        - apps/**/openapi*.json
      exclude:
        - "**/.env*"
        - "**/secrets/**"
        - "**/node_modules/**"
        - "**/.git/**"
    code:
      include:
        - apps/**/*.py
        - apps/**/*.ts
        - apps/**/*.tsx
        - apps/**/*.sql
        - apps/**/*.css
        - apps/**/*.scss
      exclude:
        - "**/.env*"
        - "**/node_modules/**"
        - "**/.venv/**"
        - "**/__pycache__/**"
        - "**/dist/**"
        - "**/build/**"
        - "**/.git/**"

  - project_id: _global
    project_name: Global Engineering Knowledge
    workspace_path: /absolute/path/to/global-knowledge
    tags:
      - architecture
      - fastapi
      - react
      - docker
      - testing
    docs:
      include:
        - "**/*.md"
      exclude:
        - "**/.env*"
        - "**/secrets/**"
    code:
      include: []
      exclude: []
```

Use `_global` for reusable engineering knowledge, not for project-specific domain logic.

---

## 5. Start sequence

Recommended clean start:

```bash
./scripts/rag-up.sh
```

Manual sequence:

```bash
# 1. Start Qdrant
docker compose up -d

# 2. Start LM Studio Local Server manually
# LM Studio -> Developer / Local Server -> Start Server
# Load embedding model: text-embedding-nomic-embed-text-v1.5

# 3. Check LM Studio
curl http://localhost:1234/v1/models

# 4. Create Qdrant collections
uv run python -m local_dev_rag.qdrant_admin

# 5. Index all configured projects
uv run python -m local_dev_rag.indexer

# 6. Optional: start real-time watcher
uv run python -m local_dev_rag.watcher
```

---

## 6. Stop sequence

Stop watcher and MCP processes with `Ctrl+C`.

Stop Qdrant:

```bash
docker compose down
```

Script:

```bash
./scripts/rag-down.sh
```

This stops the container but keeps persistent Qdrant data in `data/qdrant/`.

---

## 7. Restart full stack

```bash
./scripts/rag-restart.sh
```

This does:

```text
docker compose down
docker compose up -d
qdrant_admin
```

It does not automatically reindex everything unless you add `--reindex`.

---

## 8. Indexing and reindexing

### 8.1 Full indexing

```bash
./scripts/rag-index-all.sh
```

Equivalent:

```bash
uv run python -m local_dev_rag.indexer
```

Use this when:

```text
- first setup
- new project added to projects.yaml
- many files changed
- watcher was not running
- after restoring Qdrant data
```

### 8.2 Reindex one project

```bash
./scripts/rag-index-project.sh customui
```

This calls the Python indexer for one project. If your current `indexer.py` does not yet expose a CLI argument, see section 16.

Use this when:

```text
- only one project changed
- you edited docs/code in one project
- you changed include/exclude rules for one project
```

### 8.3 Real-time reindexing

```bash
./scripts/rag-watch.sh
```

Equivalent:

```bash
uv run python -m local_dev_rag.watcher
```

Use this during active development.

The watcher:

```text
1. detects file changes
2. waits for debounce
3. computes content_hash
4. skips unchanged files
5. deletes old chunks for the changed file
6. inserts new chunks into Qdrant
```

### 8.4 When qdrant_admin must be rerun

Run:

```bash
uv run python -m local_dev_rag.qdrant_admin
```

Only when:

```text
- first setup
- collections were deleted
- embedding model changed and vector dimension changed
- collection schema/indexes changed
```

Do not rerun it just because source files changed.

---

## 9. Clearing RAG data

### 9.1 Clear all Qdrant data

Dangerous. This deletes all collections/data.

```bash
./scripts/rag-clear-all.sh
```

Use only when:

```text
- you changed embedding model dimension
- Qdrant data is corrupted
- you want a complete clean rebuild
```

After clearing:

```bash
./scripts/rag-up.sh
./scripts/rag-index-all.sh
```

### 9.2 Clear one project

```bash
./scripts/rag-clear-project.sh customui
```

This should delete points where:

```text
project_id = customui
```

from both:

```text
rag_docs_knowledge
rag_code_knowledge
```

Use when:

```text
- project path changed
- project was removed
- you want a clean project-specific reindex
```

---

## 10. Health checks

### 10.1 Check Qdrant

```bash
./scripts/rag-status.sh
```

Manual:

```bash
curl http://localhost:6333/collections \
  -H "api-key: $QDRANT_API_KEY"
```

Expected:

```text
rag_docs_knowledge
rag_code_knowledge
```

### 10.2 Check LM Studio

```bash
curl http://localhost:1234/v1/models
```

Expected:

```text
embedding model is listed
```

### 10.3 Check embedding dimension

```bash
uv run python -c "from local_dev_rag.embeddings import get_embedding_dimension; print(get_embedding_dimension())"
```

Expected example:

```text
768
```

### 10.4 Check collection point count

```bash
curl http://localhost:6333/collections/rag_code_knowledge \
  -H "api-key: $QDRANT_API_KEY"
```

Expected:

```text
points_count > 0
```

---

## 11. Running tests

Run tests only when these are true:

```text
1. Qdrant container is running
2. LM Studio Local Server is running
3. embedding model is loaded
4. collections exist
5. indexing has already been executed
```

Run:

```bash
./scripts/rag-test.sh
```

Equivalent:

```bash
TEST_PROJECT_ID=customui uv run pytest -v
```

Tests check:

```text
- Qdrant is available
- required collections exist
- collections are not empty
- embedding endpoint works
- embedding dimension matches Qdrant collection vector size
- docs-RAG returns results
- code-RAG returns results
- payload has required fields
- obvious secrets are not indexed
- MCP tool functions return results
```

If tests fail with connection errors:

```text
- check Docker/Qdrant
- check LM Studio Local Server
- check EMBEDDING_BASE_URL
- check EMBEDDING_MODEL
```

---

## 12. MCP server

Manual run:

```bash
uv run python -m local_dev_rag.server
```

In normal use, Cursor or Roo Code starts the MCP server using the configured command.

MCP tools:

```text
list_rag_projects
search_project_docs
search_project_code
get_rag_usage_policy
```

Recommended agent behavior:

```text
Before architecture/API/DB/deployment/UI design changes:
  call search_project_docs

Before source code edits:
  call search_project_code
  then open the actual source file
```

---

## 13. Cursor configuration

Create project-level MCP config in the target project:

```text
/path/to/customui/.cursor/mcp.json
```

Example:

```json
{
  "mcpServers": {
    "local-dev-rag": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/local-dev-rag",
        "python",
        "-m",
        "local_dev_rag.server"
      ],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_API_KEY": "replace-with-local-secret",
        "DOCS_COLLECTION": "rag_docs_knowledge",
        "CODE_COLLECTION": "rag_code_knowledge",
        "EMBEDDING_BASE_URL": "http://localhost:1234/v1",
        "EMBEDDING_API_KEY": "lm-studio",
        "EMBEDDING_MODEL": "text-embedding-nomic-embed-text-v1.5",
        "PROJECTS_CONFIG": "/absolute/path/to/local-dev-rag/config/projects.yaml"
      }
    }
  }
}
```

Cursor rule for a specific project:

```text
Project RAG project_id: customui.

Before architecture, API, database, deployment, UI design system or generated app logic changes:
- call search_project_docs with project_id="customui".

Before source code edits:
- call search_project_code with project_id="customui".
- open the actual source file before editing.
- if retrieved chunks conflict with the opened file, trust the opened file.

Use global knowledge only as reusable engineering guidance.
Do not copy domain logic from other projects unless explicitly requested.
Never index or expose secrets, .env files, tokens, private keys or production data.
```

Do not commit `.cursor/mcp.json` if it contains local paths or secrets.

---

## 14. VS Code + Roo Code configuration

In Roo Code:

```text
Roo Code sidebar
-> MCP Servers
-> Configure MCP Servers
```

Add:

```json
{
  "mcpServers": {
    "local-dev-rag": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/local-dev-rag",
        "python",
        "-m",
        "local_dev_rag.server"
      ],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_API_KEY": "replace-with-local-secret",
        "DOCS_COLLECTION": "rag_docs_knowledge",
        "CODE_COLLECTION": "rag_code_knowledge",
        "EMBEDDING_BASE_URL": "http://localhost:1234/v1",
        "EMBEDDING_API_KEY": "lm-studio",
        "EMBEDDING_MODEL": "text-embedding-nomic-embed-text-v1.5",
        "PROJECTS_CONFIG": "/absolute/path/to/local-dev-rag/config/projects.yaml"
      }
    }
  }
}
```

Use absolute paths.

Recommended Roo custom instruction:

```text
Use local-dev-rag before changing this project.

For this workspace use project_id="customui".

Before editing source code:
1. call search_project_code
2. inspect returned source_path and line range
3. open the actual file in VS Code
4. edit only after checking the real file

Before architecture/design/API/database/deployment decisions:
1. call search_project_docs
2. prefer project-specific knowledge over global reusable knowledge
```

---

## 15. VS Code Python interpreter

If imports are underlined in VS Code:

```text
Ctrl + Shift + P
-> Python: Select Interpreter
-> choose .venv/bin/python
```

Check:

```bash
uv run python -c "from local_dev_rag.settings import get_settings; print('OK')"
```

---

## 16. Optional CLI support for one-project indexing and clearing

If your `indexer.py` currently only indexes all projects, add CLI entry support:

```python
# add to src/local_dev_rag/indexer.py

import argparse

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--docs-only", action="store_true")
    parser.add_argument("--code-only", action="store_true")
    args = parser.parse_args()

    include_docs = not args.code_only
    include_code = not args.docs_only

    if args.project_id:
        index_project(args.project_id, include_docs=include_docs, include_code=include_code)
    else:
        for project in load_projects():
            index_project(project.project_id, include_docs=include_docs, include_code=include_code)

if __name__ == "__main__":
    main()
```

Add `clear_project.py`:

```python
# src/local_dev_rag/clear_project.py

from __future__ import annotations

import argparse

from qdrant_client.models import FieldCondition, Filter, MatchValue

from local_dev_rag.qdrant_admin import get_qdrant_client
from local_dev_rag.settings import get_settings


def clear_project(project_id: str) -> None:
    settings = get_settings()
    client = get_qdrant_client()

    project_filter = Filter(
        must=[
            FieldCondition(
                key="project_id",
                match=MatchValue(value=project_id),
            )
        ]
    )

    for collection_name in [settings.docs_collection, settings.code_collection]:
        client.delete(
            collection_name=collection_name,
            points_selector=project_filter,
        )
        print(f"cleared project_id={project_id} from {collection_name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id")
    args = parser.parse_args()
    clear_project(args.project_id)


if __name__ == "__main__":
    main()
```

---

## 17. Scripts

Scripts are located in:

```text
scripts/
```

Make them executable:

```bash
chmod +x scripts/*.sh
```

### `scripts/rag-up.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

docker compose up -d
uv run python -m local_dev_rag.qdrant_admin

echo "Qdrant is up and collections are ensured."
echo "Make sure LM Studio Local Server is running before indexing/searching."
```

### `scripts/rag-down.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

docker compose down

echo "Qdrant container stopped. Persistent data is kept in data/qdrant/."
```

### `scripts/rag-restart.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

docker compose down
docker compose up -d
uv run python -m local_dev_rag.qdrant_admin

echo "RAG stack restarted."
```

### `scripts/rag-index-all.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

uv run python -m local_dev_rag.indexer
```

### `scripts/rag-index-project.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:?Usage: ./scripts/rag-index-project.sh <project_id>}"

uv run python -m local_dev_rag.indexer --project-id "$PROJECT_ID"
```

### `scripts/rag-watch.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

uv run python -m local_dev_rag.watcher
```

### `scripts/rag-test.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:-customui}"

TEST_PROJECT_ID="$PROJECT_ID" uv run pytest -v
```

### `scripts/rag-status.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

set -a
source .env
set +a

echo "Qdrant collections:"
curl -s "$QDRANT_URL/collections" \
  -H "api-key: $QDRANT_API_KEY"
echo
echo

echo "LM Studio models:"
curl -s "$EMBEDDING_BASE_URL/models" || true
echo
```

### `scripts/rag-clear-project.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:?Usage: ./scripts/rag-clear-project.sh <project_id>}"

uv run python -m local_dev_rag.clear_project "$PROJECT_ID"
```

### `scripts/rag-clear-all.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "This will delete local Qdrant data."
read -r -p "Type DELETE to continue: " CONFIRM

if [[ "$CONFIRM" != "DELETE" ]]; then
  echo "Cancelled."
  exit 1
fi

docker compose down
rm -rf data/qdrant
docker compose up -d
uv run python -m local_dev_rag.qdrant_admin

echo "All Qdrant data deleted and collections recreated."
```

---

## 18. Common problems

### LM Studio error: connection refused

Cause:

```text
LM Studio Local Server is not running
```

Fix:

```text
LM Studio -> Developer / Local Server -> Start Server
```

Check:

```bash
curl http://localhost:1234/v1/models
```

### Continue error: Model is unloaded

Cause:

```text
Continue uses a chat/code model that is not loaded in LM Studio
```

Fix:

```text
Load chat/code model in LM Studio
Start Local Server
Check model id in /v1/models
```

### Qdrant warning: API key is used with insecure connection

For local development this is acceptable.

For production or remote access, use HTTPS or private network.

### Vector size mismatch

Cause:

```text
embedding model changed
```

Fix:

```bash
./scripts/rag-clear-all.sh
./scripts/rag-index-all.sh
```

### VS Code import errors

Fix:

```text
Ctrl + Shift + P
-> Python: Select Interpreter
-> .venv/bin/python
```

Then:

```bash
uv sync
```

---

## 19. What to commit

Commit:

```text
pyproject.toml
uv.lock
docker-compose.yml
src/
tests/
scripts/
config/projects.yaml if it has no secrets
.env.example
README.md
.gitignore
```

Do not commit:

```text
.env
.venv/
data/qdrant/
.cursor/
*.code-workspace
secrets/
private keys
```

---

## 20. Recommended daily workflow

Start:

```bash
./scripts/rag-up.sh
```

Start LM Studio Local Server manually.

Check:

```bash
./scripts/rag-status.sh
```

Index once:

```bash
./scripts/rag-index-all.sh
```

During development:

```bash
./scripts/rag-watch.sh
```

Run tests:

```bash
./scripts/rag-test.sh customui
```

Stop:

```bash
./scripts/rag-down.sh
```
