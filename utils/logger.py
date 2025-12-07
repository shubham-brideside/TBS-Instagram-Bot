import logging
import sys
from logging.handlers import RotatingFileHandler
import io
from config import LOG_LEVEL

def get_logger(name="app", log_file="app.log"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Console handler with UTF-8 encoding
        if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # Rotating file handler (UTF-8 safe)
        file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
        file_formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Set log level from config
        level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
        logger.setLevel(level)
        logger.propagate = False
    return logger

logger = get_logger()