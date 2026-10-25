"""Content-free structured logs for the local agent runtime."""

import json
import logging
from datetime import UTC, datetime

FIELDS = (
    "run_id",
    "node",
    "tool",
    "round",
    "model",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "error_type",
)


class EventFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(
            {
                "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
                "level": record.levelname,
                "event": record.getMessage(),
                **{key: getattr(record, key) for key in FIELDS if hasattr(record, key)},
            }
        )


def configure_logging():
    logger = logging.getLogger("studio_copilot.agent")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(EventFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
