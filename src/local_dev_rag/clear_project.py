from __future__ import annotations

import argparse

from qdrant_client.models import FieldCondition, Filter, MatchValue

from local_dev_rag.qdrant_admin import get_qdrant_client
from local_dev_rag.settings import get_settings


def clear_project(project_id: str) -> None:
    settings = get_settings()
    client = get_qdrant_client()

    project_filter = Filter(
        must=[
            FieldCondition(
                key="project_id",
                match=MatchValue(value=project_id),
            )
        ]
    )

    for collection_name in [settings.docs_collection, settings.code_collection]:
        client.delete(
            collection_name=collection_name,
            points_selector=project_filter,
        )
        print(f"cleared project_id={project_id} from {collection_name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id")
    args = parser.parse_args()
    clear_project(args.project_id)


if __name__ == "__main__":
    main()
