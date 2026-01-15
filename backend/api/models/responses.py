"""
Response models for API endpoints.
All outgoing response schemas using Pydantic.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SourceInfo(BaseModel):
    """Information about a source used in RAG response."""

    repo_full_name: str = Field(..., description="Repository identifier")
    summary: str = Field(..., description="Repository summary text")
    activity_score: float = Field(..., description="Activity score")
    trend_status: str = Field(..., description="Trend indicator (HOT, ACTIVE, etc)")
    relevance_score: Optional[float] = Field(
        None, description="Similarity score from retrieval"
    )


class ChatResponse(BaseModel):
    """Response model for RAG chat endpoint."""

    answer: str = Field(..., description="Generated answer from LLM")
    query: str = Field(..., description="Original user query")
    model: str = Field(..., description="LLM model used")
    tokens_used: int = Field(..., description="Total tokens consumed")
    sources: List[SourceInfo] = Field(..., description="Sources used for answer")
    num_sources: int = Field(..., description="Number of sources retrieved")
    suggested_questions: List[str] = Field(
        default_factory=list, description="Follow-up question suggestions"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
    request_id: Optional[str] = Field(None, description="Request tracking ID")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "answer": "Based on recent data, openai/openai-python is 🔥 HOT...",
                    "query": "Which repos are trending?",
                    "model": "gpt-4o-mini",
                    "tokens_used": 547,
                    "sources": [
                        {
                            "repo_full_name": "openai/openai-python",
                            "summary": "openai/openai-python is 🔥 HOT with 12 events...",
                            "activity_score": 18.0,
                            "trend_status": "🔥 HOT",
                            "relevance_score": 0.92,
                        }
                    ],
                    "num_sources": 5,
                    "suggested_questions": [
                        "What commits were made recently?",
                        "Which Python repos are beginner-friendly?",
                    ],
                    "timestamp": "2026-01-15T10:30:00Z",
                }
            ]
        }
    }


class RepoMetrics(BaseModel):
    """Repository metrics for a specific time window."""

    events_in_window: int = Field(..., description="Total events")
    commits_in_window: int = Field(..., description="Commits count")
    prs_in_window: int = Field(..., description="Pull requests count")
    issues_in_window: int = Field(..., description="Issues count")
    releases_in_window: int = Field(..., description="Releases count")
    activity_score: float = Field(..., description="Weighted activity score")
    events_per_hour: Optional[float] = Field(None, description="Event velocity")
    score_per_hour: Optional[float] = Field(None, description="Score velocity")


class RepoResponse(BaseModel):
    """Response model for single repository details."""

    repo_full_name: str = Field(..., description="Repository identifier")
    activity_score: float = Field(..., description="Current activity score")
    trend_status: str = Field(..., description="Trend status (HOT, ACTIVE, etc)")
    momentum: str = Field(..., description="Momentum (ACCELERATING, STEADY, etc)")
    summary: str = Field(..., description="Natural language summary")
    metrics_1h: Optional[RepoMetrics] = Field(None, description="1-hour metrics")
    metrics_24h: Optional[RepoMetrics] = Field(None, description="24-hour metrics")
    metrics_7d: Optional[RepoMetrics] = Field(None, description="7-day metrics")
    rank: Optional[int] = Field(None, description="Rank in top repositories")
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, description="Last data update"
    )


class EventInfo(BaseModel):
    """Information about a single GitHub event."""

    event_id: str = Field(..., description="Unique event identifier")
    repo_full_name: str = Field(..., description="Repository")
    event_type: str = Field(..., description="Event type (commit, pr, issue, release)")
    timestamp: str = Field(..., description="Event timestamp (ISO 8601)")
    title: str = Field(..., description="Event title/message")
    author: str = Field(..., description="Event author")
    url: str = Field(..., description="GitHub URL")


class RepoEventsResponse(BaseModel):
    """Response model for repository events."""

    repo_full_name: str = Field(..., description="Repository identifier")
    events: List[EventInfo] = Field(..., description="List of events")
    total_count: int = Field(..., description="Total events returned")
    filtered_type: Optional[str] = Field(None, description="Filter applied")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TopReposResponse(BaseModel):
    """Response model for top repositories endpoint."""

    repositories: List[RepoResponse] = Field(..., description="Ranked repositories")
    total_count: int = Field(..., description="Number of repositories returned")
    time_window: str = Field(..., description="Time window used for ranking")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "repositories": [
                        {
                            "repo_full_name": "openai/openai-python",
                            "activity_score": 18.0,
                            "trend_status": "🔥 HOT",
                            "momentum": "ACCELERATING",
                            "summary": "openai/openai-python is 🔥 HOT...",
                            "rank": 1,
                        }
                    ],
                    "total_count": 10,
                    "time_window": "1h",
                    "timestamp": "2026-01-15T10:30:00Z",
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Overall system status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    pipeline_running: bool = Field(..., description="Pathway pipeline status")
    rag_available: bool = Field(..., description="RAG system availability")
    uptime_seconds: Optional[float] = Field(None, description="Service uptime")
    version: str = Field(default="0.1.0", description="API version")


class MetricsResponse(BaseModel):
    """Response model for system metrics endpoint."""

    total_events_processed: int = Field(..., description="Total events ingested")
    total_repositories: int = Field(..., description="Repositories tracked")
    active_repositories: int = Field(..., description="Repositories with recent activity")
    total_queries: int = Field(..., description="Total RAG queries processed")
    average_query_time_ms: Optional[float] = Field(
        None, description="Average query latency"
    )
    total_tokens_used: int = Field(..., description="Total LLM tokens consumed")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[dict] = Field(None, description="Additional error details")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "ValidationError",
                    "message": "Query must be between 1 and 500 characters",
                    "request_id": "abc-123",
                    "timestamp": "2026-01-15T10:30:00Z",
                }
            ]
        }
    }


class BatchChatResponse(BaseModel):
    """Response model for batch chat queries."""

    results: List[ChatResponse] = Field(..., description="List of chat responses")
    total_queries: int = Field(..., description="Number of queries processed")
    total_tokens_used: int = Field(..., description="Total tokens consumed")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    