from __future__ import annotations

import argparse
import fnmatch
import hashlib

from pathlib import Path
from pydoc import text
from uuid import uuid4

from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

from local_dev_rag.chunking import chunk_code, chunk_docs, chunk_markdown_by_headings, detect_language, module_from_path
from local_dev_rag.embeddings import embed_text
from local_dev_rag.qdrant_admin import get_qdrant_client
from local_dev_rag.settings import RagProject, get_project, get_settings, load_projects


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def matches_any(relative_path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(relative_path, pattern) for pattern in patterns)


def is_allowed(relative_path: str, include: list[str], exclude: list[str]) -> bool:
    if not matches_any(relative_path, include):
        return False

    if matches_any(relative_path, exclude):
        return False

    return True


def file_filter(project_id: str, source_path: str) -> Filter:
    return Filter(
        must=[
            FieldCondition(key="project_id", match=MatchValue(value=project_id)),
            FieldCondition(key="source_path", match=MatchValue(value=source_path)),
        ]
    )


def delete_file_chunks(collection_name: str, project_id: str, source_path: str) -> None:
    client = get_qdrant_client()
    client.delete(
        collection_name=collection_name,
        points_selector=file_filter(project_id, source_path),
    )


def existing_hash(collection_name: str, project_id: str, source_path: str) -> str | None:
    client = get_qdrant_client()
    records, _ = client.scroll(
        collection_name=collection_name,
        scroll_filter=file_filter(project_id, source_path),
        limit=1,
        with_payload=True,
    )

    if not records:
        return None

    return records[0].payload.get("content_hash")


def reusable_scope_for(project: RagProject, knowledge_type: str) -> str:
    if project.project_id == "_global":
        return "global"

    if knowledge_type == "docs":
        return "project"

    return "project"


def index_file(project: RagProject, path: Path, knowledge_type: str) -> None:
    settings = get_settings()
    collection_name = (
        settings.docs_collection if knowledge_type == "docs" else settings.code_collection
    )

    path = path.resolve()
    source_path = str(path.relative_to(project.workspace_path.resolve()))

    if not path.exists():
        delete_file_chunks(collection_name, project.project_id, source_path)
        print(f"deleted: {project.project_id}:{source_path}")
        return

    text = path.read_text(encoding="utf-8", errors="ignore")
    content_hash = sha256(text)

    if existing_hash(collection_name, project.project_id, source_path) == content_hash:
        print(f"skip unchanged: {project.project_id}:{source_path}")
        return

    delete_file_chunks(collection_name, project.project_id, source_path)

    if knowledge_type == "docs":
        chunks = chunk_markdown_by_headings(text)

    # fallback if file is not markdown or poorly parsed
    if not chunks:
        chunks = chunk_docs(text)
    else:
        chunks = chunk_code(text)
    client = get_qdrant_client()

    points = []
    for index, chunk in enumerate(chunks):
        content = chunk["content"]
        vector = embed_text(content)

        points.append(
            PointStruct(
                id=str(uuid4()),
                vector=vector,
                payload={
                    "project_id": project.project_id,
                    "project_name": project.project_name,
                    "workspace_path": str(project.workspace_path),
                    "knowledge_type": knowledge_type,
                    "reusable_scope": reusable_scope_for(project, knowledge_type),
                    "source_path": source_path,
                    "file_id": f"{project.project_id}:{source_path}",
                    "chunk_index": index,
                    "language": detect_language(path),
                    "module": module_from_path(path),
                    "start_line": chunk.get("start_line"),
                    "end_line": chunk.get("end_line"),
                    "heading_path": chunk.get("heading_path"),
                    "chunk_type": chunk.get("chunk_type"),
                    "content": content,
                    "content_hash": content_hash,
                    "tags": project.tags,
                },
            )
        )

    if points:
        client.upsert(collection_name=collection_name, points=points)

    print(f"indexed: {project.project_id}:{knowledge_type}:{source_path}, chunks={len(points)}")


def iter_project_files(project: RagProject, knowledge_type: str) -> list[Path]:
    rules = project.docs if knowledge_type == "docs" else project.code
    root = project.workspace_path.resolve()

    result: list[Path] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        relative_path = str(path.relative_to(root))
        if is_allowed(relative_path, rules.include, rules.exclude):
            result.append(path)

    return result


def index_project(project_id: str, include_docs: bool = True, include_code: bool = True) -> None:
    project = get_project(project_id)

    if include_docs:
        for path in iter_project_files(project, "docs"):
            index_file(project, path, "docs")

    if include_code:
        for path in iter_project_files(project, "code"):
            index_file(project, path, "code")


def index_all_projects() -> None:
    for project in load_projects():
        index_project(project.project_id)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--docs-only", action="store_true")
    parser.add_argument("--code-only", action="store_true")
    args = parser.parse_args()

    include_docs = not args.code_only
    include_code = not args.docs_only

    if args.project_id:
        index_project(args.project_id, include_docs=include_docs, include_code=include_code)
    else:
        for project in load_projects():
            index_project(project.project_id, include_docs=include_docs, include_code=include_code)


if __name__ == "__main__":
    main()
