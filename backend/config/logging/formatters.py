"""
Custom JSON formatter for structured logging in production.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs log records as JSON with standardized fields for
    log aggregation systems (ELK, Datadog, Splunk, etc.)
    """

    default_fields = [
        'timestamp', 'level', 'logger', 'message',
        'request_id', 'user_id', 'hospital_id',
        'path', 'method', 'status_code', 'duration_ms',
    ]

    def __init__(self, fields: Optional[list] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields = fields or self.default_fields

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {}

        # Standard fields
        log_data['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        log_data['level'] = record.levelname
        log_data['logger'] = record.name
        log_data['message'] = record.getMessage()

        # Request context fields (populated by middleware)
        for field in ['request_id', 'user_id', 'hospital_id', 'path', 'method', 'status_code', 'duration_ms']:
            value = getattr(record, field, None)
            if value is not None:
                log_data[field] = value

        # Exception info
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Extra fields from record.__dict__
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'message', 'pathname', 'process', 'processName', 'relativeCreated',
                'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info',
                'request_id', 'user_id', 'hospital_id', 'path', 'method',
                'status_code', 'duration_ms'
            }:
                # Only include JSON-serializable values
                try:
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)

        return json.dumps(log_data, ensure_ascii=False)


class RequestIdFilter(logging.Filter):
    """
    Filter to add request_id to log records from context.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Request ID is added by middleware
        return True


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)