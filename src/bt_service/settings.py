from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
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
    log_level: str = "AUTO"
    log_json: bool | None = None
    log_uvicorn_access: bool = True

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    api_prefix: str = "/api/v1"

    tool_bin_dir: str = "tools/bin"
    tool_default_timeout_seconds: int = Field(default=60, ge=1, le=3600)
    tool_strip_ansi_output: bool = True
    tool_force_no_color_env: bool = True
    tool_hci_filter_executable: str = "publish/BluetoothKit.Console"
    tool_hci_filter_working_dir: str = "tools/bin"

    proxy_http: str | None = None
    proxy_https: str | None = None
    proxy_no_proxy: str | None = None
    proxy_apply_to_process: bool = True

    jira_base_url: str | None = None
    jira_user_email: str | None = None
    jira_api_token: str | None = None
    jira_base_url_dev: str | None = None
    jira_base_url_staging: str | None = None
    jira_base_url_prod: str | None = None
    jira_user_email_dev: str | None = None
    jira_user_email_staging: str | None = None
    jira_user_email_prod: str | None = None
    jira_api_token_dev: str | None = None
    jira_api_token_staging: str | None = None
    jira_api_token_prod: str | None = None
    jira_timeout_seconds: float = Field(default=15.0, ge=1.0, le=120.0)
    jira_verify_ssl: bool = True

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"dev", "staging", "prod", "test"}
        if normalized not in allowed:
            raise ValueError(f"app_env must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.strip().upper()
        allowed = {"AUTO", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError(f"log_level must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @property
    def project_root(self) -> Path:
        return get_project_root()

    @property
    def resolved_tool_bin_dir(self) -> Path:
        return resolve_from_root(self.tool_bin_dir)

    @property
    def resolved_log_level(self) -> str:
        if self.log_level != "AUTO":
            return self.log_level
        default_by_env = {
            "dev": "DEBUG",
            "test": "INFO",
            "staging": "INFO",
            "prod": "WARNING",
        }
        return default_by_env.get(self.app_env, "INFO")

    @property
    def resolved_log_json(self) -> bool:
        if self.log_json is not None:
            return self.log_json
        return self.app_env in {"staging", "prod"}

    @property
    def resolved_api_reload(self) -> bool:
        if self.app_env == "prod":
            return False
        return self.api_reload

    @property
    def resolved_jira_base_url(self) -> str | None:
        value = self._select_env_value(
            dev=self.jira_base_url_dev,
            staging=self.jira_base_url_staging,
            prod=self.jira_base_url_prod,
        )
        return value or self.jira_base_url

    @property
    def resolved_jira_user_email(self) -> str | None:
        value = self._select_env_value(
            dev=self.jira_user_email_dev,
            staging=self.jira_user_email_staging,
            prod=self.jira_user_email_prod,
        )
        return value or self.jira_user_email

    @property
    def resolved_jira_api_token(self) -> str | None:
        value = self._select_env_value(
            dev=self.jira_api_token_dev,
            staging=self.jira_api_token_staging,
            prod=self.jira_api_token_prod,
        )
        return value or self.jira_api_token

    @property
    def jira_is_configured(self) -> bool:
        return bool(
            self.resolved_jira_base_url
            and self.resolved_jira_user_email
            and self.resolved_jira_api_token
        )

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

    def _select_env_value(
        self,
        *,
        dev: str | None,
        staging: str | None,
        prod: str | None,
    ) -> str | None:
        if self.app_env == "dev":
            return dev
        if self.app_env == "staging":
            return staging
        if self.app_env == "prod":
            return prod
        return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
