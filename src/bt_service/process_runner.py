from __future__ import annotations

import os
import re
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


_ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


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
            stdout = self._to_text(exc.stdout)
            stderr = self._to_text(exc.stderr) + f"\nProcess timed out after {timeout} seconds."
            return ProcessResult(
                command=command,
                exit_code=124,
                stdout=self._sanitize_output(stdout),
                stderr=self._sanitize_output(stderr),
                duration_ms=elapsed,
            )

        elapsed = int((time.perf_counter() - started) * 1000)
        return ProcessResult(
            command=command,
            exit_code=completed.returncode,
            stdout=self._sanitize_output(completed.stdout),
            stderr=self._sanitize_output(completed.stderr),
            duration_ms=elapsed,
        )

    def _build_env(self) -> dict[str, str]:
        env = os.environ.copy()
        if self._settings.proxy_apply_to_process:
            env.update(self._settings.proxy_env())
        if self._settings.tool_force_no_color_env:
            env["NO_COLOR"] = "1"
            env["CLICOLOR"] = "0"
            env["CLICOLOR_FORCE"] = "0"
            env["TERM"] = "dumb"
        return env

    def _sanitize_output(self, value: str) -> str:
        if not self._settings.tool_strip_ansi_output:
            return value
        return _ANSI_ESCAPE_RE.sub("", value)

    @staticmethod
    def _to_text(value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value
