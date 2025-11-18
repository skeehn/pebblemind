"""Structured logging system with rich formatting and log rotation"""

import logging
import logging.handlers
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from rich.logging import RichHandler
from rich.console import Console


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data)


def setup_logging(
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
    enable_structured_logging: bool = False,
    max_file_size_mb: int = 10,
    backup_count: int = 5,
    rich_tracebacks: bool = True
) -> logging.Logger:
    """
    Setup comprehensive logging system

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        enable_file_logging: Enable logging to file
        enable_console_logging: Enable console logging
        enable_structured_logging: Use JSON structured logging for files
        max_file_size_mb: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        rich_tracebacks: Use rich formatting for tracebacks

    Returns:
        Configured root logger
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    root_logger.handlers = []

    # Console handler with rich formatting
    if enable_console_logging:
        console = Console()
        console_handler = RichHandler(
            console=console,
            rich_tracebacks=rich_tracebacks,
            markup=True,
            show_time=True,
            show_level=True,
            show_path=True
        )
        console_handler.setLevel(getattr(logging, log_level.upper()))
        root_logger.addHandler(console_handler)

    # File handler with rotation
    if enable_file_logging and log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Main log file
        log_file = log_dir / "pebblemind.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=backup_count
        )

        if enable_structured_logging:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )

        file_handler.setLevel(getattr(logging, log_level.upper()))
        root_logger.addHandler(file_handler)

        # Error log file (ERROR and above only)
        error_log_file = log_dir / "pebblemind_errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=backup_count
        )

        if enable_structured_logging:
            error_handler.setFormatter(StructuredFormatter())
        else:
            error_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n'
                    'Function: %(funcName)s (%(pathname)s:%(lineno)d)',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )

        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get logger instance with specified name"""
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding contextual information to logs"""

    def __init__(self, logger: logging.Logger, **context):
        """
        Initialize log context

        Args:
            logger: Logger instance
            **context: Context key-value pairs
        """
        self.logger = logger
        self.context = context
        self.old_filter = None

    def __enter__(self):
        """Add context filter to logger"""
        class ContextFilter(logging.Filter):
            def __init__(self, context):
                super().__init__()
                self.context = context

            def filter(self, record):
                if not hasattr(record, 'extra'):
                    record.extra = {}
                record.extra.update(self.context)
                return True

        self.old_filter = ContextFilter(self.context)
        self.logger.addFilter(self.old_filter)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Remove context filter"""
        if self.old_filter:
            self.logger.removeFilter(self.old_filter)
