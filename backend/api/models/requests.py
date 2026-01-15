"""
Request models for API endpoints.
All incoming request validation using Pydantic.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for RAG chat endpoint."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language question about repository activity",
        examples=["Which repositories are most active right now?"],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of relevant repositories to retrieve for context",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "Which Python repositories are trending?",
                    "top_k": 5,
                },
                {
                    "query": "What repos have the most commits in the last hour?",
                    "top_k": 3,
                },
            ]
        }
    }


class RepoDetailsRequest(BaseModel):
    """Query parameters for repository details endpoint."""

    include_events: bool = Field(
        default=False,
        description="Whether to include recent events in response",
    )
    event_limit: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of events to return",
    )
    time_window: str = Field(
        default="1h",
        pattern="^(1h|24h|7d)$",
        description="Time window for metrics: 1h, 24h, or 7d",
    )


class RepoEventsRequest(BaseModel):
    """Query parameters for repository events endpoint."""

    limit: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of events to return",
    )
    event_type: Optional[str] = Field(
        default=None,
        pattern="^(commit|pull_request|issue|release)$",
        description="Filter by event type",
    )
    since_minutes: Optional[int] = Field(
        default=None,
        ge=1,
        le=10080,  # 7 days in minutes
        description="Only events from last N minutes",
    )


class TopReposRequest(BaseModel):
    """Query parameters for top repositories endpoint."""

    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of top repositories to return",
    )
    time_window: str = Field(
        default="1h",
        pattern="^(1h|24h|7d)$",
        description="Time window for ranking: 1h, 24h, or 7d",
    )
    min_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Minimum activity score threshold",
    )


class BatchChatRequest(BaseModel):
    """Request model for batch chat queries (future enhancement)."""

    queries: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of questions to process",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of sources per query",
    )