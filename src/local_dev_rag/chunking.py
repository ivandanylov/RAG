from __future__ import annotations

from pathlib import Path


CODE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".css", ".scss"}
DOC_EXTENSIONS = {".md", ".json", ".yaml", ".yml", ".txt"}


def detect_language(path: Path) -> str:
    return {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".js": "javascript",
        ".jsx": "jsx",
        ".sql": "sql",
        ".css": "css",
        ".scss": "scss",
        ".md": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
    }.get(path.suffix.lower(), "text")


def module_from_path(path: Path) -> str:
    parts = set(path.parts)

    if "backend" in parts:
        return "backend"
    if "frontend" in parts:
        return "frontend"
    if "infra" in parts:
        return "infra"
    if "ops" in parts:
        return "ops"

    return "unknown"


def chunk_docs(text: str, max_chars: int = 2500, overlap: int = 300) -> list[dict]:
    chunks: list[dict] = []
    start = 0

    while start < len(text):
        end = min(start + max_chars, len(text))
        content = text[start:end].strip()

        if content:
            chunks.append(
                {
                    "content": content,
                    "start_line": None,
                    "end_line": None,
                }
            )

        if end == len(text):
            break

        start = max(0, end - overlap)

    return chunks


def chunk_code(text: str, max_lines: int = 80, overlap: int = 15) -> list[dict]:
    lines = text.splitlines()
    chunks: list[dict] = []
    start = 0

    while start < len(lines):
        end = min(start + max_lines, len(lines))
        content = "\n".join(lines[start:end]).strip()

        if content:
            chunks.append(
                {
                    "content": content,
                    "start_line": start + 1,
                    "end_line": end,
                }
            )

        if end == len(lines):
            break

        start = max(0, end - overlap)

    return chunks


def chunk_markdown_by_headings(text: str) -> list[dict]:
    lines = text.splitlines()
    chunks = []
    current_heading = []
    current_lines = []
    start_line = 1

    def flush(end_line: int):
        if not current_lines:
            return

        content = "\n".join(current_lines).strip()
        if not content:
            return

        chunks.append(
            {
                "content": content,
                "heading_path": " > ".join(current_heading),
                "chunk_type": "markdown_section",
                "start_line": start_line,
                "end_line": end_line,
            }
        )

    for index, line in enumerate(lines, start=1):
        if line.startswith("#"):
            flush(index - 1)

            level = len(line) - len(line.lstrip("#"))
            heading = line.lstrip("#").strip()

            current_heading[:] = current_heading[: level - 1]
            current_heading.append(heading)

            current_lines.clear()
            current_lines.append(line)
            start_line = index
        else:
            current_lines.append(line)

    flush(len(lines))
    return chunks
