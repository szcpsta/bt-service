from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from bt_service.paths import is_within, resolve_from_root
from bt_service.settings import Settings


class ExecutableNotFoundError(FileNotFoundError):
    pass


class UnsafeExecutablePathError(ValueError):
    pass


@dataclass(slots=True)
class ProcessResult:
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


class ProcessRunner:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._bin_dir = settings.resolved_tool_bin_dir

    @property
    def bin_dir(self) -> Path:
        return self._bin_dir

    def ensure_bin_dir(self) -> None:
        self._bin_dir.mkdir(parents=True, exist_ok=True)

    def resolve_executable(self, executable: str) -> Path:
        raw_target = Path(executable)
        candidate = raw_target if raw_target.is_absolute() else self._bin_dir / raw_target
        resolved = candidate.expanduser().resolve()

        if not is_within(self._bin_dir, resolved):
            raise UnsafeExecutablePathError(
                f"Executable must be inside the configured bin directory: {self._bin_dir}"
            )
        if not resolved.exists() or not resolved.is_file():
            raise ExecutableNotFoundError(f"Executable not found: {resolved}")
        return resolved

    def run(
        self,
        executable: str,
        args: list[str],
        timeout_seconds: int | None = None,
        working_dir: str | None = None,
    ) -> ProcessResult:
        target = self.resolve_executable(executable)
        timeout = timeout_seconds or self._settings.tool_default_timeout_seconds

        cwd = resolve_from_root(working_dir) if working_dir else self._settings.project_root
        if not cwd.exists() or not cwd.is_dir():
            raise ValueError(f"Invalid working directory: {cwd}")

        command = [str(target), *args]
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=self._build_env(),
            )
        except subprocess.TimeoutExpired as exc:
            elapsed = int((time.perf_counter() - started) * 1000)
            return ProcessResult(
                command=command,
                exit_code=124,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + f"\nProcess timed out after {timeout} seconds.",
                duration_ms=elapsed,
            )

        elapsed = int((time.perf_counter() - started) * 1000)
        return ProcessResult(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_ms=elapsed,
        )

    def _build_env(self) -> dict[str, str]:
        env = os.environ.copy()
        if self._settings.proxy_apply_to_process:
            env.update(self._settings.proxy_env())
        return env
