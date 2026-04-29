# local-dev-rag

**A reusable local RAG (Retrieval-Augmented Generation) stack for AI development agents across multiple software projects.**

The system indexes project artifacts — documentation, architecture decision records (ADRs), OpenAPI specs, source code, and database migrations — into a local vector database. AI agents (Cursor, VS Code + Roo Code) query this index via MCP tools before making code or architecture changes, giving them accurate project-specific context rather than relying solely on general training knowledge.

---

## Technology Stack

| Component | Role |
|---|---|
| **Qdrant** | Local vector database. Stores and serves embedding vectors for semantic search. |
| **LM Studio** | Local OpenAI-compatible embeddings server. Generates text embeddings without cloud dependency. |
| **FastMCP** | MCP (Model Context Protocol) server. Exposes RAG search as tools consumable by Cursor/Roo Code. |
| **uv** | Python package and virtual environment manager. Replaces pip + venv. |
| **watchfiles** | File system watcher. Triggers incremental reindexing on file changes during development. |

---

## 1. Architecture

```
Cursor / VS Code + Roo Code / Continue
        |
        | MCP tool calls (search_project_docs, search_project_code)
        v
local-dev-rag MCP server
        |
        | semantic vector search
        v
Qdrant
  ├── rag_docs_knowledge    (documentation, ADRs, OpenAPI specs, architecture)
  └── rag_code_knowledge    (source code, migrations, tests)
        ^
        |
Indexer / Watcher           (reads project files, generates embeddings, upserts to Qdrant)
        ^
        |
Project files
  ├── docs/
  ├── ADR/
  ├── OpenAPI specs
  ├── source code
  └── migrations
```

### Qdrant Collections

| Collection | Content |
|---|---|
| `rag_docs_knowledge` | Markdown docs, ADRs, architecture files, design system docs, OpenAPI specs |
| `rag_code_knowledge` | Source code files, SQL migrations, tests, frontend/backend implementation |

### Chunk Metadata Schema

Every indexed chunk is stored with the following metadata payload in Qdrant:

| Field | Description |
|---|---|
| `project_id` | Unique identifier of the source project |
| `project_name` | Human-readable project name |
| `workspace_path` | Absolute path to the project root on disk |
| `knowledge_type` | `docs` or `code` |
| `reusable_scope` | Whether the chunk is project-specific or globally reusable |
| `source_path` | Relative path of the source file |
| `language` | Programming or markup language |
| `module` | Logical module or subsystem within the project |
| `content_hash` | SHA hash of the chunk content; used by the watcher for change detection |
| `content` | The actual text of the chunk |

---

## 2. Runtime Requirements

### Full RAG operation requires:

1. Docker (running)
2. Qdrant container (running inside Docker)
3. LM Studio Local Server (running)
4. An embedding model loaded in LM Studio
5. *(Optional)* Watcher process — for real-time reindexing
6. *(Optional)* MCP server — started automatically by Cursor/Roo on demand

### Minimum for indexing only:
```
Docker + Qdrant + LM Studio embeddings endpoint
```

### Minimum for MCP search from Cursor/Roo:
```
Qdrant + LM Studio embeddings endpoint + MCP server
```

---

## 3. Initial Setup

### 3.1 Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
uv --version
```

### 3.2 Install Python dependencies

From the project root:

```bash
uv sync
```

If dependencies are missing, add them explicitly:

```bash
uv add fastmcp qdrant-client openai python-dotenv pydantic pyyaml watchfiles
uv add --dev pytest
```

### 3.3 Create the `.env` file

Copy the example file:

```bash
cp .env.example .env
```

Fill in the values:

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

Generate a random local API key for Qdrant:

```bash
openssl rand -hex 32
```

Use the same key in both `.env` and `docker-compose.yml`.

---

## 4. Project Configuration

Projects are declared in `config/projects.yaml`. Each entry defines what files to index for docs and code, using glob patterns.

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
    docs:
      include:
        - docs/**/*.md
        - apps/**/openapi*.json
      exclude:
        - "**/.env*"
        - "**/secrets/**"
        - "**/node_modules/**"
    code:
      include:
        - apps/**/*.py
        - apps/**/*.ts
        - apps/**/*.sql
      exclude:
        - "**/node_modules/**"
        - "**/.venv/**"
        - "**/dist/**"
        - "**/.git/**"

  - project_id: _global
    project_name: Global Engineering Knowledge
    workspace_path: /absolute/path/to/global-knowledge
    tags:
      - architecture
    docs:
      include:
        - "**/*.md"
      exclude:
        - "**/.env*"
    code:
      include: []
      exclude: []
```

> Use `_global` for reusable cross-project engineering knowledge (patterns, standards, conventions). Do not put project-specific domain logic there.

---

## 5. Lifecycle Scripts

All operational commands are wrapped in shell scripts under `scripts/`. Make them executable once:

```bash
chmod +x scripts/*.sh
```

| Script | Action |
|---|---|
| `rag-up.sh` | Start Qdrant container + ensure collections exist |
| `rag-down.sh` | Stop Qdrant container (data is preserved) |
| `rag-restart.sh` | Full restart: down → up → ensure collections |
| `rag-index-all.sh` | Index all projects from `projects.yaml` |
| `rag-index-project.sh <id>` | Index a single project by `project_id` |
| `rag-watch.sh` | Start the real-time file watcher |
| `rag-test.sh [project_id]` | Run the test suite against live services |
| `rag-status.sh` | Print Qdrant collection info and LM Studio model list |
| `rag-clear-project.sh <id>` | Delete all Qdrant points for a specific project |
| `rag-clear-all.sh` | ⚠️ Destroy all Qdrant data and recreate collections |

### Recommended clean start

```bash
./scripts/rag-up.sh
# Then manually start LM Studio Local Server
```

### Manual start sequence

```bash
# 1. Start Qdrant
docker compose up -d

# 2. Start LM Studio → Developer / Local Server → Start Server
# Load model: text-embedding-nomic-embed-text-v1.5

# 3. Verify LM Studio is responding
curl http://localhost:1234/v1/models

# 4. Create Qdrant collections (idempotent)
uv run python -m local_dev_rag.qdrant_admin

# 5. Run full indexing
uv run python -m local_dev_rag.indexer

# 6. (Optional) Start real-time watcher
uv run python -m local_dev_rag.watcher
```

### Stop

```bash
./scripts/rag-down.sh
# or: docker compose down
```

Persistent Qdrant data is stored in `data/qdrant/` and survives container restarts.

---

## 6. Indexing

### Full indexing

Run when: first setup, new project added, many files changed, watcher was not running, or after restoring Qdrant data.

```bash
./scripts/rag-index-all.sh
```

### Single-project indexing

Run when: only one project changed, include/exclude rules updated for one project.

```bash
./scripts/rag-index-project.sh customui
```

### Real-time incremental indexing (watcher)

Run during active development to keep the index up to date automatically.

```bash
./scripts/rag-watch.sh
```

**Watcher behavior:**

1. Detects file system events
2. Applies a debounce delay to avoid redundant work
3. Computes `content_hash` for changed files
4. Skips files where the hash is unchanged
5. Deletes old Qdrant points for the modified file
6. Inserts new embedding chunks

### When to rerun `qdrant_admin`

Only rerun in these cases — not on every source file change:

- First setup
- Collections were deleted
- Embedding model changed and vector dimension changed
- Collection schema or index configuration changed

```bash
uv run python -m local_dev_rag.qdrant_admin
```

---

## 7. Clearing Data

### Clear a single project

Removes all Qdrant points with `project_id = <id>` from both collections. Use when a project path changed, project was removed, or a clean reindex is needed.

```bash
./scripts/rag-clear-project.sh customui
```

### Clear all data ⚠️

Destroys `data/qdrant/` and recreates empty collections. Use only when the embedding model dimension changed, data is corrupted, or a full rebuild is required.

```bash
./scripts/rag-clear-all.sh
# Then:
./scripts/rag-up.sh
./scripts/rag-index-all.sh
```

---

## 8. Health Checks

### Check Qdrant collections

```bash
./scripts/rag-status.sh
# or manually:
curl http://localhost:6333/collections -H "api-key: $QDRANT_API_KEY"
```

Expected: both `rag_docs_knowledge` and `rag_code_knowledge` are listed.

### Check LM Studio

```bash
curl http://localhost:1234/v1/models
```

Expected: the embedding model is listed in the response.

### Check embedding dimension

```bash
uv run python -c "from local_dev_rag.embeddings import get_embedding_dimension; print(get_embedding_dimension())"
```

Expected: a positive integer (e.g., `768`). Must match the vector size configured in Qdrant collections.

### Check collection point count

```bash
curl http://localhost:6333/collections/rag_code_knowledge -H "api-key: $QDRANT_API_KEY"
```

Expected: `points_count > 0` after indexing.

---

## 9. Running Tests

Tests validate the full live stack. Prerequisites before running:

1. Qdrant container is running
2. LM Studio Local Server is running
3. Embedding model is loaded
4. Collections exist
5. Indexing has been executed at least once

```bash
./scripts/rag-test.sh customui
# or:
TEST_PROJECT_ID=customui uv run pytest -v
```

**Test coverage includes:**

- Qdrant availability
- Required collections exist and are non-empty
- Embedding endpoint is reachable
- Embedding dimension matches Qdrant vector size
- `docs` and `code` RAG queries return results
- Payload contains all required metadata fields
- No secrets are present in indexed content
- MCP tool functions return valid results

---

## 10. MCP Server

The MCP server exposes RAG functionality as tools that Cursor/Roo Code can call. It is normally started automatically by the IDE, but can be run manually:

```bash
uv run python -m local_dev_rag.server
```

### Available MCP Tools

| Tool | Description |
|---|---|
| `list_rag_projects` | List all indexed projects |
| `search_project_docs` | Semantic search over documentation, ADRs, OpenAPI specs |
| `search_project_code` | Semantic search over source code and migrations |
| `get_rag_usage_policy` | Returns the recommended agent usage policy |

### Recommended agent behavior

- Before architecture, API, database, deployment, or UI design changes → call `search_project_docs`
- Before editing source code → call `search_project_code`, then open the actual source file

---

## 11. IDE Integration

### Cursor

Create `<project_root>/.cursor/mcp.json`:

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

> Do not commit `.cursor/mcp.json` if it contains local absolute paths or secrets.

### VS Code + Roo Code

Configure via: Roo Code sidebar → MCP Servers → Configure MCP Servers. Use the same JSON structure as above.

**Recommended Roo custom instruction:**

```
Use local-dev-rag before changing this project. Use project_id="customui".

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

## 12. Reranking Pipeline

The retrieval pipeline uses a **two-stage architecture** to improve result quality:

```
query
  → embedding
  → Qdrant vector search   (dense retrieval, top RETRIEVAL_TOP_K candidates)
  → cross-encoder reranker (re-scores candidates by semantic relevance)
  → threshold filtering    (drops results below RERANK_THRESHOLD)
  → final results          (top RERANK_TOP_K)
```

Reranking is especially beneficial for long documents, ambiguous queries, and overlapping chunks.

### Configuration

```env
ENABLE_RERANK=true
RETRIEVAL_TOP_K=50
RERANK_TOP_K=3
RERANK_THRESHOLD=0.5
```

| Variable | Description |
|---|---|
| `ENABLE_RERANK` | Enable or disable the reranking stage |
| `RETRIEVAL_TOP_K` | Number of candidates fetched from Qdrant for reranking |
| `RERANK_TOP_K` | Number of final results returned after reranking |
| `RERANK_THRESHOLD` | Minimum reranker score to include a result |

### Default reranking model

```
BAAI/bge-reranker-base
```

The model is downloaded automatically on first use (~100 MB – 1 GB depending on the model variant).

### Tradeoffs

| Mode | Precision | Latency |
|---|---|---|
| Reranking enabled | Higher, less noise | ~1–5 sec (CPU) |
| Reranking disabled | Lower, more noise | ~100–300 ms |

### Tuning

```env
# Increase recall (more candidates considered)
RETRIEVAL_TOP_K=80

# Increase precision (stricter threshold, fewer results)
RERANK_THRESHOLD=0.6
RERANK_TOP_K=2

# Disable reranking for faster responses
ENABLE_RERANK=false
```

**Notes:**
- The reranker score is independent of Qdrant's cosine similarity score.
- Threshold filtering is applied after reranking.
- If all results fall below the threshold, a fallback returns the top results without filtering.

---

## 13. Common Problems

### LM Studio: connection refused

**Cause:** LM Studio Local Server is not running.  
**Fix:** LM Studio → Developer / Local Server → Start Server.  
**Verify:** `curl http://localhost:1234/v1/models`

### Continue: Model is unloaded

**Cause:** The chat/completion model is not loaded in LM Studio.  
**Fix:** Load a chat model in LM Studio, start the Local Server, verify with `/v1/models`.

### Qdrant: API key with insecure connection

Acceptable for local development. For production or remote access, use HTTPS or a private network.

### Vector size mismatch

**Cause:** Embedding model was changed, producing vectors of a different dimension.  
**Fix:**
```bash
./scripts/rag-clear-all.sh
./scripts/rag-index-all.sh
```

### VS Code: import errors / underlined imports

**Fix:** `Ctrl+Shift+P` → Python: Select Interpreter → select `.venv/bin/python`, then run `uv sync`.

### Reranker not working

```bash
uv add fastembed
```

---

## 14. Optional: CLI Support for Single-Project Indexing

If `indexer.py` does not yet support the `--project-id` argument, add the following CLI entry point:

```python
# src/local_dev_rag/indexer.py

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
```

For per-project clearing, add `src/local_dev_rag/clear_project.py` using `qdrant_client.delete()` filtered by `project_id`.

---

## 15. VS Code Python Interpreter

If module imports are highlighted as errors in VS Code:

```
Ctrl+Shift+P → Python: Select Interpreter → .venv/bin/python
```

Verify:

```bash
uv run python -c "from local_dev_rag.settings import get_settings; print('OK')"
```

---

## 16. Version Control: What to Commit

### Commit

```
pyproject.toml
uv.lock
docker-compose.yml
src/
tests/
scripts/
config/projects.yaml   # only if it contains no secrets
.env.example
README.md
.gitignore
```

### Do NOT commit

```
.env                   # contains secrets and local paths
.venv/                 # Python virtual environment
data/qdrant/           # local vector database data
.cursor/               # IDE-specific config with local paths
*.code-workspace
secrets/
private keys
```

---

## 17. Recommended Daily Workflow

```bash
# 1. Start Qdrant and ensure collections
./scripts/rag-up.sh

# 2. Start LM Studio Local Server manually

# 3. Verify all services
./scripts/rag-status.sh

# 4. Index all projects (once, or after changes)
./scripts/rag-index-all.sh

# 5. During development: keep the watcher running
./scripts/rag-watch.sh

# 6. Run tests to validate the stack
./scripts/rag-test.sh customui

# 7. End of session: stop Qdrant
./scripts/rag-down.sh
```
