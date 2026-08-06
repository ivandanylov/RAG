from __future__ import annotations

import atexit
import sys
import threading

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, HnswConfigDiff, VectorParams

from local_dev_rag.embeddings import get_embedding_dimension
from local_dev_rag.settings import get_settings


_qdrant_client: QdrantClient | None = None
_qdrant_client_lock = threading.Lock()


class EmbeddingServiceUnavailableError(RuntimeError):
    """Raised when embedding service is required but not reachable."""


def _close_qdrant_client() -> None:
    global _qdrant_client

    if _qdrant_client is None:
        return

    try:
        _qdrant_client.close()
    except Exception:
        pass

    _qdrant_client = None


atexit.register(_close_qdrant_client)


def get_qdrant_client() -> QdrantClient:
    global _qdrant_client

    if _qdrant_client is not None:
        return _qdrant_client

    settings = get_settings()

    with _qdrant_client_lock:
        if _qdrant_client is None:
            _qdrant_client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
            )

    return _qdrant_client


def ensure_collections() -> None:
    settings = get_settings()
    client = get_qdrant_client()

    existing = {c.name for c in client.get_collections().collections}
    missing_collections = [
        collection_name
        for collection_name in [settings.docs_collection, settings.code_collection]
        if collection_name not in existing
    ]

    if not missing_collections:
        return

    try:
        size = get_embedding_dimension()
    except Exception as exc:
        raise EmbeddingServiceUnavailableError(
            "LLM embedding service is not available. "
            "Start LM Studio Local Server and ensure an embedding model is loaded."
        ) from exc

    for collection_name in missing_collections:

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
    try:
        ensure_collections()
    except EmbeddingServiceUnavailableError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
