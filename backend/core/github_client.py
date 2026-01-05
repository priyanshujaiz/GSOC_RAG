"""
GitHub GraphQL API client.
Handles authentication, requests, rate limiting, and error handling.
"""

import httpx
from typing import Any, Optional
from datetime import datetime
import asyncio
from backend.core.config import Settings
from backend.core.exceptions import (
    GitHubAPIError,
    RateLimitError,
    ConnectionError as AppConnectionError,
)
from backend.core.logger import get_logger

logger = get_logger(__name__)

settings = Settings()

class GitHubClient:
    """
    Async GitHub GraphQL API client with rate limiting and error handling.

    Features:
    - Automatic authentication with PAT token
    - Rate limit monitoring and backoff
    - Retry logic for transient failures
    - Structured error handling
    """

    GITHUB_GRAPHQL_ENDPOINT = "https://api.github.com/graphql"
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    RATE_LIMIT_BUFFER = 100  # Keep 100 requests as buffer

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub client.
        
        Args:
            token: GitHub Personal Access Token. If None, uses settings.GITHUB_TOKEN
        """
        self.token = token or settings.GITHUB_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github.v4+json",
        }
        self._rate_limit_remaining: Optional[int] = None
        self._rate_limit_reset_at: Optional[datetime] = None
        
        logger.info("GitHub client initialized", extra={"endpoint": self.GITHUB_GRAPHQL_ENDPOINT})
    
    async def execute_query(self, query: str, variables: Optional[dict[str, Any]] = None, retry_count: int = 0) -> dict[str, Any]:
        """
        Execute a GraphQL query against GitHub API.
        
        Args:
            query: GraphQL query string
            variables: Query variables
            retry_count: Current retry attempt (for internal use)
        
        Returns:
            Response data dictionary
        
        Raises:
            RateLimitError: If rate limit is exceeded
            GitHubAPIError: If API returns an error
            AppConnectionError: If network request fails
        """
        # Check rate limit before making request
        await self._check_rate_limit()
        
        payload = {
            "query": query,
            "variables": variables or {},
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.debug(
                    "Executing GitHub GraphQL query",
                    extra={
                        "variables": variables,
                        "retry_count": retry_count,
                    }
                )
                
                response = await client.post(
                    self.GITHUB_GRAPHQL_ENDPOINT,
                    json=payload,
                    headers=self.headers,
                )
                
                # Update rate limit info from headers
                self._update_rate_limit_from_response(response)
                
                # Handle HTTP errors
                if response.status_code == 401:
                    raise GitHubAPIError(
                        "GitHub authentication failed. Check your token.",
                        details={"status_code": 401}
                    )
                
                if response.status_code == 403:
                    # Could be rate limit or forbidden
                    if "rate limit" in response.text.lower():
                        raise RateLimitError(
                            "GitHub API rate limit exceeded",
                            details={
                                "reset_at": self._rate_limit_reset_at,
                                "remaining": self._rate_limit_remaining,
                            }
                        )
                    raise GitHubAPIError(
                        "GitHub API access forbidden",
                        details={"status_code": 403, "response": response.text}
                    )
                
                if response.status_code >= 500:
                    # Server error - retry
                    if retry_count < self.MAX_RETRIES:
                        await asyncio.sleep(self.RETRY_DELAY * (retry_count + 1))
                        return await self.execute_query(query, variables, retry_count + 1)
                    
                    raise GitHubAPIError(
                        f"GitHub API server error: {response.status_code}",
                        details={"status_code": response.status_code}
                    )
                
                response.raise_for_status()
                
                # Parse JSON response
                data = response.json()
                
                # Check for GraphQL errors
                if "errors" in data:
                    error_messages = [err.get("message", "Unknown error") for err in data["errors"]]
                    raise GitHubAPIError(
                        f"GraphQL errors: {'; '.join(error_messages)}",
                        details={"errors": data["errors"]}
                    )
                
                # Update rate limit from response data
                if "data" in data and data["data"] and "rateLimit" in data["data"]:
                    self._update_rate_limit_from_data(data["data"]["rateLimit"])
                
                logger.info(
                    "GitHub query executed successfully",
                    extra={
                        "rate_limit_remaining": self._rate_limit_remaining,
                        "variables": variables,
                    }
                )
                
                return data["data"]
        
        except httpx.TimeoutException as e:
            logger.error(f"GitHub API request timeout: {e}")
            if retry_count < self.MAX_RETRIES:
                await asyncio.sleep(self.RETRY_DELAY)
                return await self.execute_query(query, variables, retry_count + 1)
            raise AppConnectionError(f"GitHub API timeout after {self.MAX_RETRIES} retries") from e
        
        except httpx.RequestError as e:
            logger.error(f"GitHub API request failed: {e}", exc_info=True)
            if retry_count < self.MAX_RETRIES:
                await asyncio.sleep(self.RETRY_DELAY)
                return await self.execute_query(query, variables, retry_count + 1)
            raise AppConnectionError(f"GitHub API connection error: {e}") from e
    
    async def _check_rate_limit(self) -> None:
        """
        Check if we're approaching rate limit and wait if necessary.
        
        Raises:
            RateLimitError: If rate limit is exceeded and we need to wait
        """
        if self._rate_limit_remaining is None:
            # First request, don't know limits yet
            return
        
        if self._rate_limit_remaining < self.RATE_LIMIT_BUFFER:
            logger.warning(
                "Approaching GitHub rate limit",
                extra={
                    "remaining": self._rate_limit_remaining,
                    "reset_at": self._rate_limit_reset_at,
                }
            )
            
            if self._rate_limit_remaining <= 10:
                # Very close to limit, calculate wait time
                if self._rate_limit_reset_at:
                    now = datetime.utcnow()
                    if self._rate_limit_reset_at > now:
                        wait_seconds = (self._rate_limit_reset_at - now).total_seconds()
                        logger.info(f"Rate limit critical, waiting {wait_seconds}s until reset")
                        await asyncio.sleep(wait_seconds + 1)
    
    def _update_rate_limit_from_response(self, response: httpx.Response) -> None:
        """Update rate limit info from response headers."""
        if "X-RateLimit-Remaining" in response.headers:
            self._rate_limit_remaining = int(response.headers["X-RateLimit-Remaining"])
        
        if "X-RateLimit-Reset" in response.headers:
            reset_timestamp = int(response.headers["X-RateLimit-Reset"])
            self._rate_limit_reset_at = datetime.utcfromtimestamp(reset_timestamp)
    
    def _update_rate_limit_from_data(self, rate_limit_data: dict) -> None:
        """Update rate limit info from GraphQL response data."""
        self._rate_limit_remaining = rate_limit_data.get("remaining")
        
        if "resetAt" in rate_limit_data:
            # Parse ISO 8601 timestamp
            reset_str = rate_limit_data["resetAt"]
            self._rate_limit_reset_at = datetime.fromisoformat(reset_str.replace("Z", "+00:00"))
    
    async def check_authentication(self) -> bool:
        """
        Test if authentication is working.
        
        Returns:
            True if authenticated successfully
        
        Raises:
            GitHubAPIError: If authentication fails
        """
        query = """
        query {
          viewer {
            login
          }
          rateLimit {
            limit
            remaining
            resetAt
          }
        }
        """
        
        try:
            data = await self.execute_query(query)
            logger.info(
                "GitHub authentication successful",
                extra={
                    "user": data["viewer"]["login"],
                    "rate_limit": data["rateLimit"],
                }
            )
            return True
        except GitHubAPIError as e:
            logger.error(f"GitHub authentication failed: {e.message}")
            raise
    
    @property
    def rate_limit_status(self) -> dict[str, Any]:
        """Get current rate limit status."""
        return {
            "remaining": self._rate_limit_remaining,
            "reset_at": self._rate_limit_reset_at,
            "buffer": self.RATE_LIMIT_BUFFER,
        }
