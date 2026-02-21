from __future__ import annotations

import copy
import json
import logging
from datetime import UTC, datetime
from typing import Any

from uvicorn.config import LOGGING_CONFIG

from bt_service.settings import Settings


APP_LOGGER_NAME = "bt_service"


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def get_app_logger() -> logging.Logger:
    return logging.getLogger(APP_LOGGER_NAME)


def configure_logging(settings: Settings) -> None:
    level_name = settings.resolved_log_level
    level = getattr(logging, level_name, logging.INFO)

    if not settings.resolved_log_json:
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )
        root_logger.addHandler(stream_handler)
        logging.getLogger(APP_LOGGER_NAME).setLevel(level)
        logging.getLogger("uvicorn.access").disabled = not settings.log_uvicorn_access
        return

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(JsonLogFormatter())
    root_logger.addHandler(stream_handler)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
        uvicorn_logger.setLevel(level)

    logging.getLogger("uvicorn.access").disabled = not settings.log_uvicorn_access


def build_uvicorn_log_config(settings: Settings) -> dict[str, Any] | None:
    if settings.resolved_log_json:
        return None

    log_config: dict[str, Any] = copy.deepcopy(LOGGING_CONFIG)
    formatters = log_config.setdefault("formatters", {})
    default_formatter = formatters.get("default")
    if isinstance(default_formatter, dict):
        default_formatter["fmt"] = "%(asctime)s %(levelprefix)s %(message)s"
    access_formatter = formatters.get("access")
    if isinstance(access_formatter, dict):
        access_formatter["fmt"] = (
            "%(asctime)s %(levelprefix)s %(client_addr)s - "
            '"%(request_line)s" %(status_code)s'
        )

    loggers = log_config.setdefault("loggers", {})
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger_config = loggers.get(name)
        if isinstance(logger_config, dict):
            logger_config["level"] = settings.resolved_log_level

    loggers[APP_LOGGER_NAME] = {
        "handlers": ["default"],
        "level": settings.resolved_log_level,
        "propagate": False,
    }
    return log_config
