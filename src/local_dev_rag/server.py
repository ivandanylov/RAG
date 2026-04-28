from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from qdrant_client.models import FieldCondition, Filter, MatchValue

from local_dev_rag.embeddings import embed_text
from local_dev_rag.qdrant_admin import get_qdrant_client
from local_dev_rag.settings import get_settings, load_projects


mcp = FastMCP("local-dev-rag")


def project_filter(
    project_id: str,
    knowledge_type: str | None = None,
    include_global: bool = True,
    language: str | None = None,
    module: str | None = None,
) -> Filter:
    must = [
        FieldCondition(key="project_id", match=MatchValue(value=project_id))
    ]

    if knowledge_type:
        must.append(FieldCondition(key="knowledge_type", match=MatchValue(value=knowledge_type)))

    if language:
        must.append(FieldCondition(key="language", match=MatchValue(value=language)))

    if module:
        must.append(FieldCondition(key="module", match=MatchValue(value=module)))

    return Filter(must=must)


@mcp.tool
def list_rag_projects() -> list[dict[str, Any]]:
    """List projects registered in local-dev-rag."""
    return [
        {
            "project_id": project.project_id,
            "project_name": project.project_name,
            "workspace_path": str(project.workspace_path),
            "tags": project.tags,
        }
        for project in load_projects()
    ]


@mcp.tool
def search_project_docs(
    query: str,
    project_id: str,
    top_k: int = 8,
    include_global: bool = True,
) -> list[dict[str, Any]]:
    """Search documentation/ADR/architecture knowledge for a specific project."""
    settings = get_settings()
    client = get_qdrant_client()
    vector = embed_text(query)

    results = client.query_points(
        collection_name=settings.docs_collection,
        query=vector,
        query_filter=project_filter(
            project_id=project_id,
            knowledge_type="docs",
            include_global=include_global,
        ),
        limit=top_k,
        with_payload=True,
    ).points

    return [
        {
            "score": item.score,
            "project_id": item.payload.get("project_id"),
            "source_path": item.payload.get("source_path"),
            "language": item.payload.get("language"),
            "module": item.payload.get("module"),
            "content": item.payload.get("content"),
        }
        for item in results
    ]


@mcp.tool
def search_project_code(
    query: str,
    project_id: str,
    top_k: int = 8,
    include_global: bool = False,
    language: str | None = None,
    module: str | None = None,
) -> list[dict[str, Any]]:
    """Search source code for a specific project. Use this before editing code."""
    settings = get_settings()
    client = get_qdrant_client()
    vector = embed_text(query)

    results = client.query_points(
        collection_name=settings.code_collection,
        query=vector,
        query_filter=project_filter(
            project_id=project_id,
            knowledge_type="code",
            include_global=include_global,
            language=language,
            module=module,
        ),
        limit=top_k,
        with_payload=True,
    ).points

    return [
        {
            "score": item.score,
            "project_id": item.payload.get("project_id"),
            "source_path": item.payload.get("source_path"),
            "language": item.payload.get("language"),
            "module": item.payload.get("module"),
            "start_line": item.payload.get("start_line"),
            "end_line": item.payload.get("end_line"),
            "content": item.payload.get("content"),
        }
        for item in results
    ]


@mcp.tool
def get_rag_usage_policy(project_id: str) -> str:
    """Return usage policy for this reusable RAG MCP server."""
    return f"""
Use local-dev-rag for project_id={project_id}.

Rules:
1. Before architecture, API, DB, deployment or UI design changes, call search_project_docs.
2. Before editing source code, call search_project_code.
3. For code edits, after retrieval open the real file in the IDE before changing it.
4. Do not trust cross-project knowledge over current project files.
5. Global knowledge may guide patterns, but project_id-specific knowledge has priority.
6. Never index or expose .env, secrets, private keys, tokens, production dumps or user data.
"""


if __name__ == "__main__":
    mcp.run()
