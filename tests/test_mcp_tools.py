import pytest

from local_dev_rag.server import (
    list_rag_projects,
    search_project_code,
    search_project_docs,
)


def test_mcp_list_projects():
    projects = list_rag_projects()

    assert isinstance(projects, list)
    assert projects
    assert "project_id" in projects[0]


def test_mcp_docs_search(test_project_id):
    results = search_project_docs(
        query="architecture backend frontend database",
        project_id=test_project_id,
        top_k=3,
    )

    assert isinstance(results, list)
    assert results

    first = results[0]
    assert "score" in first
    assert "source_path" in first
    assert "content" in first


def test_rerank_returns_results(test_project_id):
    results = search_project_docs(
        query="refresh tokens authentication",
        project_id=test_project_id,
        top_k=5,
    )

    assert results
    assert all("content" in r for r in results)


def test_rerank_relevance(test_project_id):
    results = search_project_docs(
        query="refresh token cookie httponly",
        project_id=test_project_id,
        top_k=3,
    )

    texts = [r["content"].lower() for r in results]

    assert any("refresh token" in t for t in texts)


def test_rerank_configurable_threshold(test_project_id, monkeypatch):
    monkeypatch.setenv("ENABLE_RERANK", "true")
    monkeypatch.setenv("RERANK_THRESHOLD", "0.5")
    monkeypatch.setenv("RETRIEVAL_TOP_K", "50")
    monkeypatch.setenv("RERANK_TOP_K", "3")

    results = search_project_docs(
        query="refresh token httponly cookie",
        project_id=test_project_id,
        top_k=3,
    )

    assert isinstance(results, list)
    assert results
    assert any(
        "ADR-004-jwt-authentication.md" in r["source_path"]
        for r in results
    )


@pytest.mark.code
def test_mcp_code_search(test_project_id):
    results = search_project_code(
        query="FastAPI router backend service",
        project_id=test_project_id,
        top_k=3,
    )

    assert isinstance(results, list)
    assert results

    first = results[0]
    assert "score" in first
    assert "source_path" in first
    assert "content" in first
