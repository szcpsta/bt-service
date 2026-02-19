from __future__ import annotations

from pathlib import Path

from bt_service.paths import discover_project_root, get_project_root, resolve_from_root


def test_project_root_discovery() -> None:
    root = discover_project_root()
    assert (root / "pyproject.toml").exists()


def test_resolve_from_root_relative_path() -> None:
    resolved = resolve_from_root(Path("tools/bin"))
    assert resolved == (get_project_root() / "tools/bin").resolve()
