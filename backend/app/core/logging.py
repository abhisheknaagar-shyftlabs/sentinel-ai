import logging
import sys
from contextvars import ContextVar

from pythonjsonlogger import json as jsonlogger

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        record.user_id = user_id_ctx.get()
        return True


class JsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        if not log_record.get("request_id"):
            log_record.pop("request_id", None)
        if not log_record.get("user_id"):
            log_record.pop("user_id", None)


def configure_logging(log_level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter(
            "%(timestamp)s %(level)s %(logger)s %(message)s %(request_id)s %(user_id)s",
            rename_fields={"timestamp": "timestamp"},
            timestamp=True,
        )
    )
    handler.addFilter(ContextFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level.upper())

    for noisy_logger in ("uvicorn.access",):
        logging.getLogger(noisy_logger).handlers = [handler]
        logging.getLogger(noisy_logger).propagate = False


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
