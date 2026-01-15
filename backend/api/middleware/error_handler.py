"""
Global error handling middleware.
Provides consistent error responses and logging.
"""

from datetime import datetime
from typing import Callable, Union

from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.exceptions import (
    GitHubAPIError,
    PathwayError,
    RAGError,
    RateLimitError,
)
from backend.core.logger import get_logger

logger = get_logger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for catching and handling all errors.
    Converts exceptions to JSON responses with proper status codes.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """
        Process request with error handling.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            Response or error response
        """
        try:
            response = await call_next(request)
            return response

        except ValidationError as e:
            return await handle_validation_error(request, e)

        except GitHubAPIError as e:
            return await handle_github_error(request, e)

        except RateLimitError as e:
            return await handle_rate_limit_error(request, e)

        except RAGError as e:
            return await handle_rag_error(request, e)

        except PathwayError as e:
            return await handle_pathway_error(request, e)

        except Exception as e:
            return await handle_generic_error(request, e)


async def handle_validation_error(
    request: Request, error: ValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.warning(
        "Validation error",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "errors": error.errors(),
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Request validation failed",
            "details": error.errors(),
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


async def handle_github_error(request: Request, error: GitHubAPIError) -> JSONResponse:
    """Handle GitHub API errors."""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.warning(
        "GitHub API error",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "error": str(error),
        },
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "GitHubAPIError",
            "message": "GitHub API is currently unavailable or rate limited",
            "details": str(error),
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


async def handle_rate_limit_error(
    request: Request, error: RateLimitError
) -> JSONResponse:
    """Handle rate limit errors."""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.warning(
        "Rate limit exceeded",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "error": str(error),
        },
    )

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "RateLimitError",
            "message": "API rate limit exceeded. Please try again later.",
            "details": str(error),
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "retry_after": 60,  # Suggest retry after 60 seconds
        },
    )


async def handle_rag_error(request: Request, error: RAGError) -> JSONResponse:
    """Handle RAG system errors."""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        "RAG system error",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "error": str(error),
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "RAGError",
            "message": "RAG system is currently unavailable",
            "details": "The question-answering system encountered an error. Please try again.",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


async def handle_pathway_error(request: Request, error: PathwayError) -> JSONResponse:
    """Handle Pathway pipeline errors."""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        "Pathway pipeline error",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "error": str(error),
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "PathwayError",
            "message": "Data pipeline is currently unavailable",
            "details": "The system is experiencing issues processing real-time data.",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


async def handle_generic_error(request: Request, error: Exception) -> JSONResponse:
    """Handle all other unhandled exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        "Unhandled exception",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "error_type": type(error).__name__,
            "error": str(error),
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "details": "Please contact support if this problem persists.",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


def create_error_response(
    error_type: str,
    message: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    details: Union[str, dict, None] = None,
    request_id: str = "unknown",
) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        error_type: Type of error
        message: Human-readable error message
        status_code: HTTP status code
        details: Additional error details
        request_id: Request tracking ID

    Returns:
        JSON error response
    """
    content = {
        "error": error_type,
        "message": message,
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if details:
        content["details"] = details

    return JSONResponse(status_code=status_code, content=content)