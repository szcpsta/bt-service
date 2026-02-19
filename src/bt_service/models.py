from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class ToolExecutionRequest(BaseModel):
    executable: str = Field(min_length=1, max_length=255)
    args: list[str] = Field(default_factory=list)
    timeout_seconds: int | None = Field(default=None, ge=1, le=3600)
    working_dir: str | None = None


class ToolExecutionResponse(BaseModel):
    executable: str
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


class JiraIssueUpdateRequest(BaseModel):
    issue_key: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z][A-Za-z0-9]+-\d+$")
    fields: dict[str, Any] = Field(default_factory=dict)
    comment: str | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "JiraIssueUpdateRequest":
        if not self.fields and not self.comment:
            raise ValueError("At least one of fields or comment must be provided.")
        return self


class JiraIssueUpdateResponse(BaseModel):
    issue_key: str
    fields_updated: bool
    comment_added: bool

