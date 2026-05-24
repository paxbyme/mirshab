"""Loglashni sozlash (loguru)."""

from __future__ import annotations

import inspect
import logging
import sys

from loguru import logger


class _InterceptHandler(logging.Handler):
    """Standart `logging` chaqiruvlarini loguru'ga yo'naltiradi (aiogram, sqlalchemy)."""

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D102
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        # Asl chaqiruvchi modulni topish uchun logging stack'ini o'tkazib yuboramiz
        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging(level: str = "INFO") -> None:
    """Konsol + fayl loggerini o'rnatadi."""
    logger.remove()
    fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    )
    logger.add(sys.stderr, level=level.upper(), format=fmt, colorize=True)
    logger.add(
        "logs/mirshab_{time:YYYY-MM-DD}.log",
        level=level.upper(),
        rotation="00:00",
        retention="14 days",
        compression="zip",
        encoding="utf-8",
        format=fmt,
    )

    # Standart logging'ni ushlab olish — faqat root'da bitta intercept handler.
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    # Nomlangan logger'lar o'z handler'lariga ega bo'lmasin va root'ga propagate qilsin
    # (aks holda har bir yozuv ikki marta chiqadi).
    for noisy in ("aiogram", "sqlalchemy.engine", "apscheduler"):
        lg = logging.getLogger(noisy)
        lg.handlers = []
        lg.propagate = True


__all__ = ["logger", "setup_logging"]
