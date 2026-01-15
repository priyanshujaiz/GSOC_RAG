"""
Request logging middleware.
Provides structured logging for all API requests with context.
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.logger import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.
    Adds structured context to logs including timing, status codes, and request metadata.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            Response from downstream handlers
        """
        # Record start time
        start_time = time.time()

        # Get request ID (added by main.py middleware)
        request_id = getattr(request.state, "request_id", "unknown")

        # Extract request details
        client_host = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params) if request.query_params else {}

        # Log incoming request
        logger.info(
            "Incoming request",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "client_ip": client_host,
                "user_agent": request.headers.get("user-agent", "unknown"),
                "query_params": query_params,
            },
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Log successful response
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": round(process_time * 1000, 2),
                    "success": 200 <= response.status_code < 400,
                },
            )

            # Add custom headers
            response.headers["X-Process-Time"] = str(round(process_time, 3))

            return response

        except Exception as e:
            # Calculate processing time even for errors
            process_time = time.time() - start_time

            # Log error
            logger.error(
                "Request failed with exception",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "duration_ms": round(process_time * 1000, 2),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )

            # Re-raise to be handled by exception handlers
            raise


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding context to request state.
    Useful for tracking user sessions, authentication, etc.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add context information to request state.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            Response from downstream handlers
        """
        # Add timestamp to request
        request.state.start_time = time.time()

        # Add any additional context here
        # For example: user_id, session_id, etc.

        response = await call_next(request)

        return response


def get_request_context(request: Request) -> dict:
    """
    Extract structured context from request for logging.

    Args:
        request: FastAPI request object

    Returns:
        Dictionary with request context
    """
    return {
        "request_id": getattr(request.state, "request_id", "unknown"),
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
    }


def log_with_request_context(
    logger_instance,
    level: str,
    message: str,
    request: Request,
    **kwargs,
) -> None:
    """
    Log with automatic request context injection.

    Args:
        logger_instance: Logger instance
        level: Log level (info, warning, error, etc.)
        message: Log message
        request: FastAPI request object
        **kwargs: Additional log context
    """
    context = get_request_context(request)
    context.update(kwargs)

    log_method = getattr(logger_instance, level.lower())
    log_method(message, extra=context)