"""
Centralized logging configuration for Junior Gold Intel
"""
import logging
import os
from datetime import datetime

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Create a configured logger instance.

    Args:
        name: Logger name (typically __name__ from calling module)
        level: Logging level (default INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Format: timestamp - module - level - message
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Optional file handler for debugging
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'logs')
    if os.path.exists(log_dir):
        file_handler = logging.FileHandler(
            os.path.join(log_dir, f'junior_gold_intel_{datetime.now().strftime("%Y%m%d")}.log')
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


class LogContext:
    """Context manager for logging operation timing"""

    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"Starting: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        if exc_type:
            self.logger.error(f"Failed: {self.operation} after {duration:.2f}s - {exc_val}")
        else:
            self.logger.info(f"Completed: {self.operation} in {duration:.2f}s")
        return False
