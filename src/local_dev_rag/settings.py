from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class ProjectPathRules(BaseModel):
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


class RagProject(BaseModel):
    project_id: str
    project_name: str
    workspace_path: Path
    tags: list[str] = Field(default_factory=list)
    docs: ProjectPathRules = Field(default_factory=ProjectPathRules)
    code: ProjectPathRules = Field(default_factory=ProjectPathRules)


class Settings(BaseModel):
    qdrant_url: str
    qdrant_api_key: str | None
    docs_collection: str
    code_collection: str
    embedding_base_url: str
    embedding_api_key: str
    embedding_model: str
    projects_config: Path


def get_settings() -> Settings:
    return Settings(
        qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        qdrant_api_key=os.getenv("QDRANT_API_KEY"),
        docs_collection=os.getenv("DOCS_COLLECTION", "rag_docs_knowledge"),
        code_collection=os.getenv("CODE_COLLECTION", "rag_code_knowledge"),
        embedding_base_url=os.getenv("EMBEDDING_BASE_URL", "http://localhost:1234/v1"),
        embedding_api_key=os.getenv("EMBEDDING_API_KEY", "lm-studio"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5"),
        projects_config=Path(os.getenv("PROJECTS_CONFIG", "./config/projects.yaml")),
    )


def load_projects() -> list[RagProject]:
    settings = get_settings()

    with settings.projects_config.open("r", encoding="utf-8") as file:
        raw: dict[str, Any] = yaml.safe_load(file)

    return [RagProject(**item) for item in raw.get("projects", [])]


def get_project(project_id: str) -> RagProject:
    for project in load_projects():
        if project.project_id == project_id:
            return project

    raise ValueError(f"Unknown project_id: {project_id}")
