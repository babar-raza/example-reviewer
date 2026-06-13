"""
Structured logging configuration for Example Reviewer Pipeline.

Provides JSON-structured logging with correlation IDs and run context,
using python-json-logger (already a project dependency).
"""

import logging
import sys
import uuid
from contextvars import ContextVar
from pythonjsonlogger import jsonlogger

_run_id: ContextVar[str] = ContextVar("run_id", default="")
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


class PipelineJsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that injects run_id and correlation_id into every record."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["run_id"] = _run_id.get("")
        log_record["correlation_id"] = _correlation_id.get("")
        log_record["logger"] = record.name
        log_record["level"] = record.levelname


def setup_structured_logging(level: int = logging.INFO) -> None:
    """Configure root logger with JSON-structured output to stderr."""
    handler = logging.StreamHandler(sys.stderr)
    formatter = PipelineJsonFormatter(
        fmt="%(asctime)s %(level)s %(logger)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def set_run_context(run_id: str, correlation_id: str | None = None) -> None:
    """Set the run context for structured log fields."""
    _run_id.set(run_id)
    _correlation_id.set(correlation_id or str(uuid.uuid4())[:8])
