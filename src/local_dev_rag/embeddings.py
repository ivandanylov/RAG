from __future__ import annotations

from openai import OpenAI

from local_dev_rag.settings import get_settings


def get_embedding_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(
        base_url=settings.embedding_base_url,
        api_key=settings.embedding_api_key,
    )


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
