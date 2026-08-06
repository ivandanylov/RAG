from __future__ import annotations

import atexit
import threading

from openai import OpenAI

from local_dev_rag.settings import get_settings


_embedding_client: OpenAI | None = None
_embedding_client_lock = threading.Lock()


def _close_embedding_client() -> None:
    global _embedding_client

    if _embedding_client is None:
        return

    close_client = getattr(_embedding_client, "close", None)
    if callable(close_client):
        try:
            close_client()
        except Exception:
            pass

    _embedding_client = None


atexit.register(_close_embedding_client)


def get_embedding_client() -> OpenAI:
    global _embedding_client

    if _embedding_client is not None:
        return _embedding_client

    settings = get_settings()

    with _embedding_client_lock:
        if _embedding_client is None:
            _embedding_client = OpenAI(
                base_url=settings.embedding_base_url,
                api_key=settings.embedding_api_key,
            )

    return _embedding_client


def embed_text(text: str) -> list[float]:
    settings = get_settings()
    client = get_embedding_client()

    result = client.embeddings.create(
        model=settings.embedding_model,
        input=text,
    )

    return result.data[0].embedding


def get_embedding_dimension() -> int:
    return len(embed_text("dimension test"))
