"""
All custom exceptions for the project.
"""


class BaseAppException(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationError(BaseAppException):
    """Raised when configuration is invalid or missing."""

    pass


class GitHubAPIError(BaseAppException):
    """Raised when GitHub API request fails."""

    pass


class RateLimitError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded."""

    pass


class ConnectionError(BaseAppException):
    """Raised when network connection fails."""

    pass


class PathwayError(BaseAppException):
    """Raised when Pathway engine encounters an error."""

    pass


class RAGError(BaseAppException):
    """Raised when RAG operations fail."""

    pass


class EmbeddingError(RAGError):
    """Raised when embedding generation fails."""

    pass


class RetrievalError(RAGError):
    """Raised when vector retrieval fails."""

    pass


class LLMError(RAGError):
    """Raised when LLM query fails."""

    pass


class APIError(BaseAppException):
    """Raised when API operations fail."""

    pass


class ValidationError(APIError):
    """Raised when input validation fails."""

    pass
