from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from bt_service.paths import get_project_root, resolve_from_root


_PROJECT_ROOT = get_project_root()
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_prefix="BT_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "bt-service"
    app_env: str = "dev"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    api_prefix: str = "/api/v1"

    tool_bin_dir: str = "tools/bin"
    tool_default_timeout_seconds: int = Field(default=60, ge=1, le=3600)

    proxy_http: str | None = None
    proxy_https: str | None = None
    proxy_no_proxy: str | None = None
    proxy_apply_to_process: bool = True

    jira_base_url: str | None = None
    jira_user_email: str | None = None
    jira_api_token: str | None = None
    jira_timeout_seconds: float = Field(default=15.0, ge=1.0, le=120.0)
    jira_verify_ssl: bool = True

    @property
    def project_root(self) -> Path:
        return get_project_root()

    @property
    def resolved_tool_bin_dir(self) -> Path:
        return resolve_from_root(self.tool_bin_dir)

    @property
    def jira_is_configured(self) -> bool:
        return bool(self.jira_base_url and self.jira_user_email and self.jira_api_token)

    def proxy_env(self) -> dict[str, str]:
        proxy_env: dict[str, str] = {}
        if self.proxy_http:
            proxy_env["HTTP_PROXY"] = self.proxy_http
            proxy_env["http_proxy"] = self.proxy_http
        if self.proxy_https:
            proxy_env["HTTPS_PROXY"] = self.proxy_https
            proxy_env["https_proxy"] = self.proxy_https
        if self.proxy_no_proxy:
            proxy_env["NO_PROXY"] = self.proxy_no_proxy
            proxy_env["no_proxy"] = self.proxy_no_proxy
        return proxy_env


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
