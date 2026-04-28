from qdrant_client.models import FieldCondition, Filter, MatchValue

from conftest import embed


def test_project_docs_search_returns_results(
    qdrant_client,
    embedding_client,
    docs_collection,
    test_project_id,
):
    vector = embed(
        embedding_client,
        "architecture FastAPI React PostgreSQL Redis Docker",
    )

    results = qdrant_client.search(
        collection_name=docs_collection,
        query_vector=vector,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="project_id",
                    match=MatchValue(value=test_project_id),
                )
            ]
        ),
        limit=5,
        with_payload=True,
    )

    assert results

    payload = results[0].payload
    assert payload["project_id"] == test_project_id
    assert "source_path" in payload
    assert "content" in payload


def test_project_code_search_returns_results(
    qdrant_client,
    embedding_client,
    code_collection,
    test_project_id,
):
    vector = embed(
        embedding_client,
        "backend FastAPI router service application initialization",
    )

    results = qdrant_client.search(
        collection_name=code_collection,
        query_vector=vector,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="project_id",
                    match=MatchValue(value=test_project_id),
                )
            ]
        ),
        limit=5,
        with_payload=True,
    )

    assert results

    payload = results[0].payload
    assert payload["project_id"] == test_project_id
    assert "source_path" in payload
    assert "content" in payload


def test_code_search_backend_python_filter(
    qdrant_client,
    embedding_client,
    code_collection,
    test_project_id,
):
    vector = embed(
        embedding_client,
        "FastAPI backend python router service",
    )

    results = qdrant_client.search(
        collection_name=code_collection,
        query_vector=vector,
        query_filter=Filter(
            must=[
                FieldCondition(key="project_id", match=MatchValue(value=test_project_id)),
                FieldCondition(key="language", match=MatchValue(value="python")),
                FieldCondition(key="module", match=MatchValue(value="backend")),
            ]
        ),
        limit=5,
        with_payload=True,
    )

    assert results

    for item in results:
        assert item.payload["project_id"] == test_project_id
        assert item.payload["language"] == "python"
        assert item.payload["module"] == "backend"
