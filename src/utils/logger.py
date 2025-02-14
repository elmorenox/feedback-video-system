# src/utils/logger.py
import logging
from ..settings import Settings


def setup_logger():
    settings = Settings()

    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)
