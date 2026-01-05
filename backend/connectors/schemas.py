"""
Schema definitions for GitHub events in Pathway.
Defines the structure of data flowing through the pipeline.
"""

from typing import Literal
from datetime import datetime


# Event types we track
EventType = Literal["commit", "pull_request", "issue", "release"]


class GitHubEventSchema:
    """
    Schema for GitHub events in Pathway tables.
    
    Each event has:
    - id: Unique identifier (string)
    - repo_full_name: Repository in "owner/repo" format
    - event_type: Type of event (commit, PR, issue, release)
    - timestamp: When the event occurred
    - title: Event title/message
    - author: Who created the event
    - url: Link to the event on GitHub
    - metadata: Additional event-specific data (JSON)
    """
    
    # Column names (for reference)
    ID = "id"
    REPO_FULL_NAME = "repo_full_name"
    EVENT_TYPE = "event_type"
    TIMESTAMP = "timestamp"
    TITLE = "title"
    AUTHOR = "author"
    URL = "url"
    METADATA = "metadata"
    
    @staticmethod
    def columns() -> list[str]:
        """Get list of column names."""
        return [
            GitHubEventSchema.ID,
            GitHubEventSchema.REPO_FULL_NAME,
            GitHubEventSchema.EVENT_TYPE,
            GitHubEventSchema.TIMESTAMP,
            GitHubEventSchema.TITLE,
            GitHubEventSchema.AUTHOR,
            GitHubEventSchema.URL,
            GitHubEventSchema.METADATA,
        ]


class RepositoryStateSchema:
    """
    Schema for tracking repository state.
    Used to remember what we've already fetched.
    """
    
    REPO_FULL_NAME = "repo_full_name"
    LAST_FETCH_TIME = "last_fetch_time"
    TOTAL_EVENTS_FETCHED = "total_events_fetched"
    
    @staticmethod
    def columns() -> list[str]:
        """Get list of column names."""
        return [
            RepositoryStateSchema.REPO_FULL_NAME,
            RepositoryStateSchema.LAST_FETCH_TIME,
            RepositoryStateSchema.TOTAL_EVENTS_FETCHED,
        ]