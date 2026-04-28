import os

import pytest
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient


@pytest.fixture(scope="session", autouse=True)
def load_env():
    load_dotenv(".env")


@pytest.fixture(scope="session")
def qdrant_client():
    return QdrantClient(
        url=os.environ["QDRANT_URL"],
        api_key=os.getenv("QDRANT_API_KEY"),
    )


@pytest.fixture(scope="session")
def embedding_client():
    return OpenAI(
        base_url=os.environ["EMBEDDING_BASE_URL"],
        api_key=os.getenv("EMBEDDING_API_KEY", "lm-studio"),
    )


@pytest.fixture(scope="session")
def docs_collection():
    return os.getenv("DOCS_COLLECTION", "rag_docs_knowledge")


@pytest.fixture(scope="session")
def code_collection():
    return os.getenv("CODE_COLLECTION", "rag_code_knowledge")


@pytest.fixture(scope="session")
def test_project_id():
    return os.getenv("TEST_PROJECT_ID", "customui")


def embed(client: OpenAI, text: str) -> list[float]:
    result = client.embeddings.create(
        model=os.environ["EMBEDDING_MODEL"],
        input=text,
    )
    return result.data[0].embedding


@pytest.fixture(autouse=True)
def skip_code_tests_if_empty(request, qdrant_client, code_collection):
    """
    Автоматически пропускает тесты, помеченные как 'code',
    если code collection пустая.
    """
    if "code" not in request.keywords:
        return

    info = qdrant_client.get_collection(code_collection)

    if info.points_count == 0:
        pytest.skip("Code collection is empty: no source code indexed yet")
