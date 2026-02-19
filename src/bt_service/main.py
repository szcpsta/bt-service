from __future__ import annotations

import os
from contextlib import asynccontextmanager

import uvicorn
from anyio.to_thread import run_sync
from fastapi import APIRouter, Depends, FastAPI, HTTPException

from bt_service.jira_client import JiraApiError, JiraClient, JiraConfigError
from bt_service.models import (
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

        return ToolExecutionResponse(
            executable=payload.executable,
            command=result.command,
            exit_code=result.exit_code,
            stdout=result.stdout,
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
