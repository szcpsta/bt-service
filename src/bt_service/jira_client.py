from __future__ import annotations

import base64
from typing import Any

import httpx

from bt_service.settings import Settings


class JiraConfigError(RuntimeError):
    pass


class JiraApiError(RuntimeError):
    def __init__(self, action: str, status_code: int, detail: str) -> None:
        super().__init__(f"Jira {action} failed ({status_code}): {detail}")
        self.action = action
        self.status_code = status_code
        self.detail = detail


class JiraClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def update_issue(
        self,
        issue_key: str,
        fields: dict[str, Any],
        comment: str | None,
    ) -> dict[str, Any]:
        base_url = self._settings.resolved_jira_base_url
        if not self._settings.jira_is_configured:
            raise JiraConfigError(
                "Jira is not configured. Set BT_JIRA_BASE_URL/BT_JIRA_*_<ENV>, "
                "BT_JIRA_USER_EMAIL/BT_JIRA_USER_EMAIL_<ENV>, "
                "BT_JIRA_API_TOKEN/BT_JIRA_API_TOKEN_<ENV>."
            )
        if not base_url:
            raise JiraConfigError("Jira base URL is empty after environment resolution.")

        timeout = httpx.Timeout(self._settings.jira_timeout_seconds)
        async with httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            verify=self._settings.jira_verify_ssl,
            trust_env=True,
        ) as client:
            headers = self._build_headers()
            fields_updated = False
            comment_added = False

            if fields:
                response = await client.put(
                    f"/rest/api/2/issue/{issue_key}",
                    json={"fields": fields},
                    headers=headers,
                )
                self._raise_for_status(response, "field update")
                fields_updated = True

            if comment:
                response = await client.post(
                    f"/rest/api/2/issue/{issue_key}/comment",
                    json={"body": comment},
                    headers=headers,
                )
                self._raise_for_status(response, "comment update")
                comment_added = True

        return {
            "issue_key": issue_key,
            "fields_updated": fields_updated,
            "comment_added": comment_added,
        }

    def _build_headers(self) -> dict[str, str]:
        user_email = self._settings.resolved_jira_user_email
        api_token = self._settings.resolved_jira_api_token
        if not user_email or not api_token:
            raise JiraConfigError("Jira credentials are empty after environment resolution.")
        credential_raw = f"{user_email}:{api_token}"
        basic_token = base64.b64encode(credential_raw.encode("utf-8")).decode("ascii")
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {basic_token}",
        }

    @staticmethod
    def _raise_for_status(response: httpx.Response, action: str) -> None:
        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise JiraApiError(action=action, status_code=response.status_code, detail=detail)
