from __future__ import annotations

from typing import Any
from pathlib import Path

from fastmcp import FastMCP
from qdrant_client.models import FieldCondition, Filter, MatchValue

from local_dev_rag.embeddings import embed_text
from local_dev_rag.qdrant_admin import get_qdrant_client
from local_dev_rag.settings import get_settings, load_projects

from fastembed.rerank.cross_encoder import TextCrossEncoder


mcp = FastMCP("local-dev-rag")

_reranker = None


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


def get_reranker():
    global _reranker

    if _reranker is None:
        settings = get_settings()

        Path(settings.rerank_cache_dir).mkdir(
            parents=True,
            exist_ok=True,
        )

        _reranker = TextCrossEncoder(
            model_name="BAAI/bge-reranker-base",
            cache_dir=settings.rerank_cache_dir,
        )

    return _reranker


def rerank(query: str, results: list, final_k: int, threshold: float) -> list:
    if not results:
        return []

    documents = [item.payload.get("content", "") for item in results]
    
    reranker = get_reranker()
    
    scores = list(
        reranker.rerank(
            query=query,
            documents=documents,
        )
    )

    ranked = sorted(
        zip(results, scores),
        key=lambda item: item[1],
        reverse=True,
    )

    # Фильтр слабых результатов
    filtered = [item for item in ranked if item[1] > threshold]

    final = filtered[:final_k] if filtered else ranked[:final_k]

    return [item[0] for item in final]


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

    retrieval_k = max(settings.retrieval_top_k, top_k)
    rerank_k = min(settings.rerank_top_k, top_k)

    raw_results = client.query_points(
        collection_name=settings.docs_collection,
        query=vector,
        query_filter=project_filter(
            project_id=project_id,
            knowledge_type="docs",
            include_global=include_global,
        ),
        limit=retrieval_k,
        with_payload=True,
    ).points

    if settings.enable_rerank:
        results = rerank(
            query=query,
            results=raw_results,
            final_k=rerank_k,
            threshold=settings.rerank_threshold,
        )
    else:
        results = raw_results[:top_k]

    print(
        f"[RAG] rerank enabled={settings.enable_rerank}, "
        f"retrieval_k={retrieval_k}, "
        f"rerank_k={rerank_k}, "
        f"threshold={settings.rerank_threshold}"
    )

    return [
        {
            "score": item.score,
            "project_id": item.payload.get("project_id"),
            "source_path": item.payload.get("source_path"),
            "language": item.payload.get("language"),
            "module": item.payload.get("module"),
            "heading_path": item.payload.get("heading_path"),
            "chunk_type": item.payload.get("chunk_type"),
            "start_line": item.payload.get("start_line"),
            "end_line": item.payload.get("end_line"),
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
