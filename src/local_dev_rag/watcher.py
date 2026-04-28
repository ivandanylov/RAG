from __future__ import annotations

import queue
import threading
from pathlib import Path

from watchfiles import Change, watch

from local_dev_rag.indexer import index_file, is_allowed
from local_dev_rag.settings import RagProject, load_projects


work_queue: queue.Queue[tuple[RagProject, Path, str]] = queue.Queue()
queued: set[tuple[str, str, str]] = set()
lock = threading.Lock()


def classify(project: RagProject, path: Path) -> str | None:
    if not path.exists():
        relative = str(path.relative_to(project.workspace_path.resolve()))
        return "unknown"

    relative = str(path.relative_to(project.workspace_path.resolve()))

    if is_allowed(relative, project.docs.include, project.docs.exclude):
        return "docs"

    if is_allowed(relative, project.code.include, project.code.exclude):
        return "code"

    return None


def enqueue(project: RagProject, path: Path, knowledge_type: str) -> None:
    key = (project.project_id, str(path), knowledge_type)

    with lock:
        if key in queued:
            return

        queued.add(key)
        work_queue.put((project, path, knowledge_type))


def worker() -> None:
    while True:
        project, path, knowledge_type = work_queue.get()

        try:
            with lock:
                queued.discard((project.project_id, str(path), knowledge_type))

            if knowledge_type == "unknown":
                # При удалении файла нельзя точно классифицировать по расширению, поэтому чистим обе коллекции через index_file.
                try:
                    index_file(project, path, "docs")
                except Exception:
                    pass
                try:
                    index_file(project, path, "code")
                except Exception:
                    pass
            else:
                index_file(project, path, knowledge_type)

        except Exception as exc:
            print(f"watch reindex error: {project.project_id}:{path}: {exc}")

        finally:
            work_queue.task_done()


def main() -> None:
    projects = load_projects()
    roots = [project.workspace_path.resolve() for project in projects if project.workspace_path.exists()]

    threading.Thread(target=worker, daemon=True).start()

    for root in roots:
        print(f"watching: {root}")

    for changes in watch(*roots, debounce=1500, step=300, recursive=True):
        for change_type, raw_path in changes:
            if change_type not in {Change.added, Change.modified, Change.deleted}:
                continue

            path = Path(raw_path).resolve()

            for project in projects:
                root = project.workspace_path.resolve()
                if root not in path.parents and path != root:
                    continue

                knowledge_type = classify(project, path)
                if knowledge_type:
                    enqueue(project, path, knowledge_type)


if __name__ == "__main__":
    main()
