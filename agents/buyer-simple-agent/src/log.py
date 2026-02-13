"""Structured colored logging for agent output.

Provides a custom formatter that outputs:
    HH:MM:SS | COMPONENT  | ACTION     | details

Colors by semantics (ANSI escape codes, no dependencies):
- Cyan: component labels
- Green: success/completed
- Yellow: payment interactions
- Red: errors
- Magenta: incoming messages
- Blue: outgoing messages
- Dim: timestamps
"""

import asyncio
import logging
import sys
from datetime import datetime

# ANSI escape codes
RESET = "\033[0m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"

# Map action keywords to colors
ACTION_COLORS = {
    "RECEIVED": MAGENTA,
    "REGISTERED": GREEN,
    "FETCHING": BLUE,
    "VERIFY": YELLOW,
    "VERIFIED": YELLOW,
    "SETTLE": YELLOW,
    "TOKEN": YELLOW,
    "COMPLETED": GREEN,
    "SUCCESS": GREEN,
    "STARTUP": GREEN,
    "SENT": BLUE,
    "SENDING": BLUE,
    "RESPONSE": BLUE,
    "ERROR": RED,
    "FAILED": RED,
    "TOOL_USE": CYAN,
    "CONNECT": BLUE,
    "EVENT": DIM,
    "CHECK": CYAN,
    "RESULT": GREEN,
    "FOUND": GREEN,
    "LIST_SELLERS": CYAN,
    "DISCOVER": CYAN,
    "PURCHASE": YELLOW,
    "BALANCE": CYAN,
}


_web_log_queue: asyncio.Queue | None = None


class WebLogHandler(logging.Handler):
    """Push structured log dicts to an asyncio.Queue for SSE streaming."""

    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self._queue = queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = {
                "timestamp": datetime.fromtimestamp(record.created).strftime("%H:%M:%S"),
                "component": getattr(record, "component", "AGENT"),
                "action": getattr(record, "action", "INFO"),
                "message": record.getMessage(),
            }
            self._queue.put_nowait(entry)
        except Exception:
            pass


def enable_web_logging(queue: asyncio.Queue) -> None:
    """Enable web log streaming by attaching WebLogHandler to all buyer loggers."""
    global _web_log_queue
    _web_log_queue = queue
    handler = WebLogHandler(queue)
    # Retroactively attach to all existing buyer.* loggers
    for name, logger in logging.Logger.manager.loggerDict.items():
        if isinstance(logger, logging.Logger) and name.startswith("buyer."):
            # Avoid duplicate handlers
            if not any(isinstance(h, WebLogHandler) for h in logger.handlers):
                logger.addHandler(handler)


class AgentFormatter(logging.Formatter):
    """Format log records as structured, colored table rows."""

    def format(self, record: logging.LogRecord) -> str:
        component = getattr(record, "component", "AGENT")
        action = getattr(record, "action", "INFO")
        message = record.getMessage()

        # Timestamp
        ts = self.formatTime(record, "%H:%M:%S")

        # Color the action based on keyword
        action_color = ACTION_COLORS.get(action, RESET)

        return (
            f"{DIM}{ts}{RESET} "
            f"| {CYAN}{component:<11}{RESET} "
            f"| {action_color}{action:<11}{RESET} "
            f"| {message}"
        )


def get_logger(name: str) -> logging.Logger:
    """Create a logger with the AgentFormatter on stderr.

    Only attaches the handler once per logger name.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(AgentFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        # Attach web handler if enabled
        if _web_log_queue is not None:
            web_handler = WebLogHandler(_web_log_queue)
            logger.addHandler(web_handler)
    return logger


def log(
    logger: logging.Logger,
    component: str,
    action: str,
    message: str,
    level: int = logging.INFO,
) -> None:
    """Log a structured message with component and action metadata."""
    logger.log(level, message, extra={"component": component, "action": action})
