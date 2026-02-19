from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


def discover_project_root(start: Path | None = None) -> Path:
    env_root = os.getenv("BT_PROJECT_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()

    current = (start or Path(__file__).resolve()).expanduser().resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate

    return Path.cwd().expanduser().resolve()


@lru_cache(maxsize=1)
def get_project_root() -> Path:
    return discover_project_root()


def resolve_from_root(path_value: str | Path) -> Path:
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (get_project_root() / path).resolve()


def is_within(parent: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(parent)
        return True
    except ValueError:
        return False

