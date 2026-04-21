import json
import logging
import sys
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter for 12-Factor Factor XI compliance."""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "message": record.getMessage(),
            "module": record.module,
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        extra_fields = getattr(record, "extra_fields", None)
        if extra_fields and isinstance(extra_fields, dict):
            log_entry.update(extra_fields)
        return json.dumps(log_entry)


def get_logger(service_name: str, level: str = "INFO") -> logging.Logger:
    """Create a structured JSON logger that writes to stdout (12-Factor Factor XI)."""
    logger = logging.getLogger(service_name)
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter(service_name))
    logger.addHandler(handler)
    logger.propagate = False
    return logger
