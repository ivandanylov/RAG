def test_qdrant_available(qdrant_client):
    collections = qdrant_client.get_collections()
    assert collections is not None


def test_required_collections_exist(qdrant_client, docs_collection, code_collection):
    collections = qdrant_client.get_collections()
    names = {collection.name for collection in collections.collections}

    assert docs_collection in names
    assert code_collection in names


def test_collections_not_empty(qdrant_client, docs_collection, code_collection):
    docs = qdrant_client.get_collection(docs_collection)
    code = qdrant_client.get_collection(code_collection)

    assert docs.points_count > 0
    assert code.points_count > 0
