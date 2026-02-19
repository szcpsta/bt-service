# bt-service

`uv` + `FastAPI` based template for:
1. Running external executables and returning results
2. Updating Jira issues via API

This template is built with path-safe defaults so it keeps working even when run from different current directories.

## Quick Start

```bash
uv venv --python 3.14
uv sync
cp .env.example .env
uv run bt-service
```

Server default URL: `http://127.0.0.1:8000`  
Swagger UI: `http://127.0.0.1:8000/docs`

## Project Layout

```text
.
├── pyproject.toml
├── .env.example
├── src/
│   └── bt_service/
│       ├── main.py
│       ├── settings.py
│       ├── paths.py
│       ├── models.py
│       ├── process_runner.py
│       └── jira_client.py
├── tools/
│   └── bin/              # put external executables here
└── tests/
```

## External Executable Rules

- Default executable directory: `tools/bin`
- Path traversal is blocked (`../` etc.)

## Proxy Handling

Use these environment variables in `.env`:
- `BT_PROXY_HTTP`
- `BT_PROXY_HTTPS`
- `BT_PROXY_NO_PROXY`
- `BT_PROXY_APPLY_TO_PROCESS`

When set, they are applied to:
- Jira HTTP client
- Child process environment (external executable calls)

## Jira Configuration

Set values in `.env`:
- `BT_JIRA_BASE_URL` (ex: `https://your-domain.atlassian.net`)
- `BT_JIRA_USER_EMAIL`
- `BT_JIRA_API_TOKEN`

## Main Endpoints

- `GET /api/v1/health`
- `GET /api/v1/tools/bin`
- `POST /api/v1/tools/run`
- `POST /api/v1/jira/issues/update`

### Tool Run Request Example

```json
{
  "executable": "my_program",
  "args": ["--mode", "check"],
  "timeout_seconds": 30
}
```

### Jira Update Request Example

```json
{
  "issue_key": "PROJ-123",
  "fields": {
    "summary": "Updated from bt-service"
  },
  "comment": "Automated update from bt-service"
}
```

## Notes

- If your launch location is unusual, you can force project root:
  - `BT_PROJECT_ROOT=/absolute/path/to/bt-service`
- Run basic syntax checks:

```bash
python3 -m compileall src
```
