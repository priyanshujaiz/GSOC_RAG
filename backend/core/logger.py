import sys
from pathlib import Path

from loguru import logger

from backend.core.config import Settings

settings = Settings()

def setup_logging() -> None:
    logger.remove()

    # Formatting of hte logger
    if settings.LOG_FORMAT == "json":
        log_format = (
            "{{"
            '"timestamp": "{time:YYYY-MM-DD HH:mm:ss.SSS}",'
            '"level": "{level: <8}",'
            '"message": "{message}",'
            '"module": "{name}",'
            '"line": "{line}",'
            '"function": "{function}",'
            "}}"
        )
    else:
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # console handler
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.LOG_LEVEL,
        colorize=(settings.LOG_FORMAT == "pretty"),
        backtrace=True,
        diagnose=True,
    )

    # file handler
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_dir / "app_{time:YYYY-MM-DD}.log",
        format=log_format,
        level=settings.LOG_LEVEL,
        rotation="00:00",  # Rotate at midnight
        retention="7 days",  # Keep logs for 7 days
        compression="zip",  # Compress old logs
        backtrace=True,
        diagnose=True,
    )

    logger.info(
        "Logging initialized",
        extra={
            "log_level": settings.LOG_LEVEL,
            "log_format": settings.LOG_FORMAT,
        },
    )


# We can use it to get a logger with the given name
def get_logger(name: str):
    """Get a logger with the given name."""
    return logger.bind(name=name)
