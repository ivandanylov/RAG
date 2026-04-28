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
