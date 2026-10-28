from contextvars import ContextVar
from logging import Filter, Formatter, StreamHandler, getLogger
import sys

from opengaterag.api.infrastructure.configuration import Settings

client_ip: ContextVar[str | None] = ContextVar("client_ip", default=None)


class ClientIPFilter(Filter):
    def filter(self, record):
        client_addr = client_ip.get()
        record.client_ip = client_addr if client_addr else "."
        return True


class ColoredFormatter(Formatter):
    """Custom formatter with colors for different log levels"""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def configure_logging(settings: Settings) -> None:
    logger = getLogger(name="opengaterag")
    logger.setLevel(level=settings.log_level)
    handler = StreamHandler(stream=sys.stdout)
    handler.setFormatter(ColoredFormatter(settings.log_format))
    handler.addFilter(ClientIPFilter())

    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False  # Prevent propagation to root logger
