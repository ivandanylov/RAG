from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, HnswConfigDiff, VectorParams

from local_dev_rag.embeddings import get_embedding_dimension
from local_dev_rag.settings import get_settings


def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
    )


def ensure_collections() -> None:
    settings = get_settings()
    client = get_qdrant_client()
    size = get_embedding_dimension()

    existing = {c.name for c in client.get_collections().collections}

    for collection_name in [settings.docs_collection, settings.code_collection]:
        if collection_name in existing:
            continue

        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=size,
                distance=Distance.COSINE,
            ),
            hnsw_config=HnswConfigDiff(
                payload_m=16,
            ),
        )

        for field in [
            "project_id",
            "workspace_path",
            "knowledge_type",
            "reusable_scope",
            "language",
            "module",
            "source_path",
        ]:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema="keyword",
            )


if __name__ == "__main__":
    ensure_collections()
