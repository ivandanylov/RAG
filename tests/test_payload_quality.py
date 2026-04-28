import pytest


REQUIRED_FIELDS = {
    "project_id",
    "project_name",
    "workspace_path",
    "knowledge_type",
    "reusable_scope",
    "source_path",
    "file_id",
    "chunk_index",
    "language",
    "module",
    "content",
    "content_hash",
}


def test_docs_payload_required_fields(qdrant_client, docs_collection):
    records, _ = qdrant_client.scroll(
        collection_name=docs_collection,
        limit=20,
        with_payload=True,
    )

    assert records

    for record in records:
        missing = REQUIRED_FIELDS - set(record.payload.keys())
        assert not missing, f"Missing docs payload fields: {missing}"


@pytest.mark.code
def test_code_payload_required_fields(qdrant_client, code_collection):
    records, _ = qdrant_client.scroll(
        collection_name=code_collection,
        limit=20,
        with_payload=True,
    )

    assert records

    for record in records:
        missing = REQUIRED_FIELDS - set(record.payload.keys())
        assert not missing, f"Missing code payload fields: {missing}"


def test_no_obvious_secrets_indexed(qdrant_client, docs_collection, code_collection):
    forbidden = [
        ".env",
        "BEGIN RSA PRIVATE KEY",
        "BEGIN OPENSSH PRIVATE KEY",
        "password=",
        "secret=",
        "api_key=",
        "access_token=",
    ]

    for collection_name in [docs_collection, code_collection]:
        records, _ = qdrant_client.scroll(
            collection_name=collection_name,
            limit=100,
            with_payload=True,
        )

        for record in records:
            source_path = record.payload.get("source_path", "")
            content = record.payload.get("content", "")

            for fragment in forbidden:
                assert fragment.lower() not in source_path.lower()
                assert fragment.lower() not in content.lower()
