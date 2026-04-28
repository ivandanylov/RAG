from conftest import embed


def test_embedding_endpoint_works(embedding_client):
    vector = embed(embedding_client, "CustomUI RAG smoke test")

    assert isinstance(vector, list)
    assert len(vector) > 0
    assert all(isinstance(value, float) for value in vector)


def test_embedding_dimension_matches_collections(
    qdrant_client,
    embedding_client,
    docs_collection,
    code_collection,
):
    vector = embed(embedding_client, "dimension check")
    dim = len(vector)

    docs_info = qdrant_client.get_collection(docs_collection)
    code_info = qdrant_client.get_collection(code_collection)

    assert docs_info.config.params.vectors.size == dim
    assert code_info.config.params.vectors.size == dim
