"""
WebSocket event models and message formats.
Defines all event types and their data structures.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List,Literal, Optional

from pydantic import BaseModel, Field


class WSEventType(str, Enum):
    """WebSocket event types."""

    # Connection events
    CONNECTION = "connection"
    DISCONNECTION = "disconnection"
    HEARTBEAT = "heartbeat"
    PING = "ping"
    PONG = "pong"

    # Data update events
    NEW_EVENT = "new_event"
    SUMMARY_UPDATE = "summary_update"
    RANKING_CHANGE = "ranking_change"
    TREND_CHANGE = "trend_change"
    METRICS_UPDATE = "metrics_update"

    # System events
    SYSTEM_STATUS = "system_status"
    ERROR = "error"


class WSMessage(BaseModel):
    """Base WebSocket message format."""

    type: WSEventType = Field(..., description="Event type")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data")


class ConnectionMessage(BaseModel):
    """Connection established message."""

    type: Literal["connection"] = Field(
        default="connection",
        description="Message type identifier"
    )
    status: str = Field(..., description="Connection status")
    client_id: str = Field(..., description="Client identifier")
    message: str = Field(..., description="Welcome message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NewEventMessage(BaseModel):
    """New GitHub event notification."""

    type: Literal["new_event"] = Field(
        default="new_event",
        description="Message type identifier"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)

    # Event-specific fields
    event_id: str = Field(..., description="Unique event identifier")
    repo_full_name: str = Field(..., description="Repository name")
    event_type: str = Field(
        ..., description="Event type (commit, pull_request, issue, release)"
    )
    title: str = Field(..., description="Event title")
    author: str = Field(..., description="Event author")
    url: str = Field(..., description="GitHub URL")


class SummaryUpdateMessage(BaseModel):
    """Repository summary updated notification."""

    type: Literal["summary_update"] = Field(
        default="summary_update",
        description="Message type identifier"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    repo_full_name: str = Field(..., description="Repository name")
    summary: str = Field(..., description="New summary text")
    activity_score: float = Field(..., description="Current activity score")
    trend_status: str = Field(..., description="Trend status")
    momentum: str = Field(..., description="Momentum indicator")
    events_in_window: int = Field(..., description="Events in current window")


class RankingChangeMessage(BaseModel):
    """Repository ranking changed notification."""

    type: Literal["ranking_change"] = Field(
        default="ranking_change",
        description="Message type identifier"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    repo_full_name: str = Field(..., description="Repository name")
    old_rank: Optional[int] = Field(None, description="Previous rank")
    new_rank: int = Field(..., description="Current rank")
    activity_score: float = Field(..., description="Current activity score")
    change: str = Field(..., description="Change direction (up, down, new, out)")


class TrendChangeMessage(BaseModel):
    """Repository trend changed notification."""

    type: Literal["trend_change"] = Field(
        default="trend_change",
        description="Message type identifier"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    repo_full_name: str = Field(..., description="Repository name")
    old_trend: Optional[str] = Field(None, description="Previous trend")
    new_trend: str = Field(..., description="Current trend")
    old_momentum: Optional[str] = Field(None, description="Previous momentum")
    new_momentum: str = Field(..., description="Current momentum")


class MetricsUpdateMessage(BaseModel):
    """System metrics updated notification."""

    type: Literal["metrics_update"] = Field(
        default="metrics_update",
        description="Message type identifier"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_events: int = Field(..., description="Total events processed")
    active_repositories: int = Field(..., description="Active repositories")
    total_queries: int = Field(..., description="Total queries processed")


class SystemStatusMessage(BaseModel):
    """System status notification."""

    type: Literal["system_status"] = Field(
        default="system_status",
        description="Message type identifier"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(..., description="System status")
    pipeline_running: bool = Field(..., description="Pipeline status")
    rag_available: bool = Field(..., description="RAG availability")
    message: Optional[str] = Field(None, description="Status message")


class ErrorMessage(BaseModel):
    """Error notification."""

    type: Literal["error"] = Field(
        default="error",
        description="Message type identifier"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")


# Helper functions for creating messages


def create_new_event_message(
    event_id: str,
    repo_full_name: str,
    event_type: str,
    title: str,
    author: str,
    url: str,
    **kwargs,
) -> Dict[str, Any]:
    """Create a new event message."""
    return {
        "type": "new_event",
        "timestamp": datetime.utcnow().isoformat(),
        "event_id": event_id,
        "repo_full_name": repo_full_name,
        "event_type": event_type,
        "title": title,
        "author": author,
        "url": url,
        "data": kwargs,
    }


def create_summary_update_message(
    repo_full_name: str,
    summary: str,
    activity_score: float,
    trend_status: str,
    momentum: str,
    events_in_window: int,
) -> Dict[str, Any]:
    """Create a summary update message."""
    return {
        "type": "summary_update",
        "timestamp": datetime.utcnow().isoformat(),
        "repo_full_name": repo_full_name,
        "summary": summary,
        "activity_score": activity_score,
        "trend_status": trend_status,
        "momentum": momentum,
        "events_in_window": events_in_window,
    }


def create_ranking_change_message(
    repo_full_name: str,
    old_rank: Optional[int],
    new_rank: int,
    activity_score: float,
) -> Dict[str, Any]:
    """Create a ranking change message."""
    # Determine change direction
    if old_rank is None:
        change = "new"
    elif new_rank > 10:
        change = "out"
    elif old_rank > new_rank:
        change = "up"
    elif old_rank < new_rank:
        change = "down"
    else:
        change = "none"

    return {
        "type": "ranking_change",
        "timestamp": datetime.utcnow().isoformat(),
        "repo_full_name": repo_full_name,
        "old_rank": old_rank,
        "new_rank": new_rank,
        "activity_score": activity_score,
        "change": change,
    }


def create_trend_change_message(
    repo_full_name: str,
    old_trend: Optional[str],
    new_trend: str,
    old_momentum: Optional[str],
    new_momentum: str,
) -> Dict[str, Any]:
    """Create a trend change message."""
    return {
        "type": "trend_change",
        "timestamp": datetime.utcnow().isoformat(),
        "repo_full_name": repo_full_name,
        "old_trend": old_trend,
        "new_trend": new_trend,
        "old_momentum": old_momentum,
        "new_momentum": new_momentum,
    }


def create_metrics_update_message(
    total_events: int, active_repositories: int, total_queries: int
) -> Dict[str, Any]:
    """Create a metrics update message."""
    return {
        "type": "metrics_update",
        "timestamp": datetime.utcnow().isoformat(),
        "total_events": total_events,
        "active_repositories": active_repositories,
        "total_queries": total_queries,
    }