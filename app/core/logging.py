import logging
import sys
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """Configures structured application logging."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Set external libraries to appropriate log levels
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured HTTP request/response access logging and latency tracking."""

    def __init__(self, app: Callable) -> None:
        super().__init__(app)
        self.logger = logging.getLogger("inventory_api.access")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        url_path = request.url.path

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            log_msg = (
                f"{client_ip} - \"{method} {url_path}\" "
                f"{response.status_code} ({duration_ms:.2f}ms)"
            )

            if response.status_code >= 500:
                self.logger.error(log_msg)
            elif response.status_code >= 400:
                self.logger.warning(log_msg)
            else:
                self.logger.info(log_msg)

            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            self.logger.exception(
                f"{client_ip} - \"{method} {url_path}\" "
                f"FAILED with exception: {exc} ({duration_ms:.2f}ms)"
            )
            raise
