from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from anyio.to_thread import run_sync
from fastapi import APIRouter, Depends, FastAPI, HTTPException

from bt_service.jira_client import JiraApiError, JiraClient, JiraConfigError
from bt_service.models import (
    HciFilterRequest,
    JiraIssueUpdateRequest,
    JiraIssueUpdateResponse,
    ToolExecutionRequest,
    ToolExecutionResponse,
)
from bt_service.process_runner import (
    ExecutableNotFoundError,
    ProcessRunner,
    UnsafeExecutablePathError,
)
from bt_service.settings import Settings, get_settings


def _apply_proxy_environment() -> None:
    settings = get_settings()
    proxy_env = settings.proxy_env()
    for key, value in proxy_env.items():
        os.environ[key] = value


def configure_logging(level: str) -> None:
    import logging

    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def _try_parse_json(text: str) -> Any | None:
    content = text.strip()
    if not content:
        raise ValueError("Tool stdout is empty. JSON output is required.")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise ValueError("Tool stdout must be valid JSON.")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    _apply_proxy_environment()
    settings.resolved_tool_bin_dir.mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
        version="0.1.0",
    )

    api = APIRouter(prefix=settings.api_prefix)

    @api.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        current = get_settings()
        return {"status": "ok", "app": current.app_name, "env": current.app_env}

    @api.get("/tools/bin", tags=["tools"])
    async def list_binaries(
        current: Settings = Depends(get_settings),
    ) -> dict[str, str | list[str]]:
        runner = ProcessRunner(current)
        runner.ensure_bin_dir()
        binaries = sorted(path.name for path in runner.bin_dir.iterdir() if path.is_file())
        return {"bin_dir": str(runner.bin_dir), "files": binaries}

    @api.post("/tools/run", tags=["tools"], response_model=ToolExecutionResponse)
    async def run_tool(
        payload: ToolExecutionRequest,
        current: Settings = Depends(get_settings),
    ) -> ToolExecutionResponse:
        runner = ProcessRunner(current)
        runner.ensure_bin_dir()

        try:
            result = await run_sync(
                runner.run,
                payload.executable,
                payload.args,
                payload.timeout_seconds,
                payload.working_dir,
            )
        except ExecutableNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except UnsafeExecutablePathError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            output = _try_parse_json(result.stdout)
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return ToolExecutionResponse(
            executable=payload.executable,
            command=result.command,
            exit_code=result.exit_code,
            output=output,
            stderr=result.stderr,
            duration_ms=result.duration_ms,
        )

    @api.post("/tools/hci/filter", tags=["tools"], response_model=ToolExecutionResponse)
    async def hci_filter(
        payload: HciFilterRequest,
        current: Settings = Depends(get_settings),
    ) -> ToolExecutionResponse:
        runner = ProcessRunner(current)
        runner.ensure_bin_dir()

        args = ["hci", "filter", "--mode", "json", "-o", "stdout"]
        if payload.ogf:
            args.extend(["--ogf", payload.ogf])
        if payload.ocf:
            args.extend(["--ocf", payload.ocf])
        if payload.opcode:
            args.extend(["--opcode", payload.opcode])
        if payload.eventcode:
            args.extend(["--eventcode", payload.eventcode])
        if payload.le_subevent:
            args.extend(["--le-subevent", payload.le_subevent])
        if payload.vendor_eventcode:
            args.extend(["--vendor-eventcode", payload.vendor_eventcode])

        args.append(payload.input_path)

        try:
            result = await run_sync(
                runner.run,
                current.tool_hci_filter_executable,
                args,
                payload.timeout_seconds,
                current.tool_hci_filter_working_dir,
            )
        except ExecutableNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except UnsafeExecutablePathError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            output = _try_parse_json(result.stdout)
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return ToolExecutionResponse(
            executable=current.tool_hci_filter_executable,
            command=result.command,
            exit_code=result.exit_code,
            output=output,
            stderr=result.stderr,
            duration_ms=result.duration_ms,
        )

    @api.post("/jira/issues/update", tags=["jira"], response_model=JiraIssueUpdateResponse)
    async def update_issue(
        payload: JiraIssueUpdateRequest,
        current: Settings = Depends(get_settings),
    ) -> JiraIssueUpdateResponse:
        client = JiraClient(current)

        try:
            result = await client.update_issue(
                issue_key=payload.issue_key,
                fields=payload.fields,
                comment=payload.comment,
            )
        except JiraConfigError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except JiraApiError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return JiraIssueUpdateResponse(**result)

    app.include_router(api)

    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "bt_service.main:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
