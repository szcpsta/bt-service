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
- ANSI color output can be sanitized in API response (`BT_TOOL_STRIP_ANSI_OUTPUT`)
- Child process can be forced to no-color mode (`BT_TOOL_FORCE_NO_COLOR_ENV`)

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
- `POST /api/v1/tools/hci/filter` (fixed executable/working_dir/mode/output)
- `POST /api/v1/jira/issues/update`

`POST /api/v1/tools/run` requires the executed program to print valid JSON to `stdout`.
If `stdout` is not valid JSON, API returns `502`.

### Tool Run Request Example

```json
{
  "executable": "my_program",
  "args": ["--mode", "check"],
  "timeout_seconds": 30
}
```

### Tool Run With Shared Storage Path Example

```json
{
  "executable": "publish/BluetoothKit.Console",
  "args": ["/shared/logs/sample.log", "/shared/results/result.txt"],
  "timeout_seconds": 60
}
```

### Fixed HCI Filter Endpoint Example

`POST /api/v1/tools/hci/filter` uses fixed values from server settings:
- executable: `BT_TOOL_HCI_FILTER_EXECUTABLE`
- working directory: `BT_TOOL_HCI_FILTER_WORKING_DIR`
- fixed args: `hci filter --mode json -o stdout`

Request body example:

```json
{
  "input_path": "btsnoop_hci.log",
  "ogf": "0x01",
  "eventcode": "0x0E,0x0F",
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
