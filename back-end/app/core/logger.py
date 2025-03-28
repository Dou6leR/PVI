import logging
from logging.handlers import RotatingFileHandler

from core import settings


class AppLogger:
    def __init__(self, name: str = "fastapi", log_file: str = "app.log"):
        # Create a logger instance
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)  # Set the base log level

        # Define log format matching FastAPI/Uvicorn style
        log_format = logging.Formatter(
            "%(levelname)-7s %(asctime)s - %(name)s - %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(log_format)

        # Rotating file handler
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(log_format)

        # Clear existing handlers to avoid duplicate logs
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # Add handlers to the logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def critical(self, message: str):
        self.logger.critical(message)


# Create a global logger instance
logger = AppLogger(
    name=settings.logger.name,
    log_file=settings.logger.log_file,
)
