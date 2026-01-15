"""
Repository endpoints.
Provides access to repository data, metrics, and events.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from backend.api.models.requests import (
    RepoDetailsRequest,
    RepoEventsRequest,
    TopReposRequest,
)
from backend.api.models.responses import (
    EventInfo,
    RepoEventsResponse,
    RepoMetrics,
    RepoResponse,
    TopReposResponse,
)
from backend.api.routes.health import set_repository_counts, update_metrics
from backend.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/repos/top10",
    response_model=TopReposResponse,
    status_code=status.HTTP_200_OK,
    summary="Get top 10 repositories",
    description="Returns the top 10 most active repositories based on activity score",
    tags=["Repositories"],
)
async def get_top_repositories(
    limit: int = Query(default=10, ge=1, le=50, description="Number of repos to return"),
    time_window: str = Query(
        default="1h",
        pattern="^(1h|24h|7d)$",
        description="Time window: 1h, 24h, or 7d",
    ),
    min_score: Optional[float] = Query(
        default=None, ge=0.0, description="Minimum activity score"
    ),
) -> TopReposResponse:
    """
    Get top repositories ranked by activity score.

    The ranking is based on weighted activity:
    - Commits: 1 point
    - Issues: 2 points
    - Pull Requests: 3 points
    - Releases: 5 points

    Args:
        limit: Number of repositories to return (1-50)
        time_window: Time window for ranking (1h, 24h, 7d)
        min_score: Optional minimum score threshold

    Returns:
        List of top repositories with metrics
    """
    logger.info(
        "Top repositories requested",
        extra={
            "limit": limit,
            "time_window": time_window,
            "min_score": min_score,
        },
    )

    try:
        # Get data from Pathway pipeline
        repos_data = await _get_top_repos_from_pipeline(limit, time_window, min_score)

        # Update metrics
        if repos_data:
            set_repository_counts(total=len(repos_data), active=len(repos_data))

        return TopReposResponse(
            repositories=repos_data,
            total_count=len(repos_data),
            time_window=time_window,
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(
            "Error fetching top repositories",
            extra={"error": str(e), "time_window": time_window},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to fetch repository data",
        )


@router.get(
    "/repos/{repo_id}",
    response_model=RepoResponse,
    status_code=status.HTTP_200_OK,
    summary="Get repository details",
    description="Returns detailed information about a specific repository",
    tags=["Repositories"],
)
async def get_repository_details(
    repo_id: str,
    time_window: str = Query(
        default="1h", pattern="^(1h|24h|7d)$", description="Time window for metrics"
    ),
) -> RepoResponse:
    """
    Get detailed information about a specific repository.

    The repo_id should be in format: "owner-repo" (e.g., "openai-openai-python")
    or "owner/repo" (e.g., "openai/openai-python").

    Args:
        repo_id: Repository identifier (owner/repo or owner-repo)
        time_window: Time window for metrics (1h, 24h, 7d)

    Returns:
        Detailed repository information
    """
    # Normalize repo_id (convert dashes to slashes)
    repo_full_name = repo_id.replace("-", "/")

    logger.info(
        "Repository details requested",
        extra={"repo_id": repo_id, "repo_full_name": repo_full_name},
    )

    try:
        # Get data from Pathway pipeline
        repo_data = await _get_repo_details_from_pipeline(repo_full_name, time_window)

        if repo_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository '{repo_full_name}' not found or has no activity",
            )

        return repo_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching repository details",
            extra={"repo_id": repo_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to fetch repository data",
        )


@router.get(
    "/repos/{repo_id}/events",
    response_model=RepoEventsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get repository events",
    description="Returns recent events for a specific repository",
    tags=["Repositories"],
)
async def get_repository_events(
    repo_id: str,
    limit: int = Query(default=50, ge=1, le=200, description="Max events to return"),
    event_type: Optional[str] = Query(
        default=None,
        pattern="^(commit|pull_request|issue|release)$",
        description="Filter by event type",
    ),
    since_minutes: Optional[int] = Query(
        default=None, ge=1, le=10080, description="Events from last N minutes"
    ),
) -> RepoEventsResponse:
    """
    Get recent events for a specific repository.

    Args:
        repo_id: Repository identifier (owner/repo or owner-repo)
        limit: Maximum number of events to return
        event_type: Filter by event type (commit, pull_request, issue, release)
        since_minutes: Only events from last N minutes

    Returns:
        List of repository events
    """
    # Normalize repo_id
    repo_full_name = repo_id.replace("-", "/")

    logger.info(
        "Repository events requested",
        extra={
            "repo_id": repo_id,
            "limit": limit,
            "event_type": event_type,
            "since_minutes": since_minutes,
        },
    )

    try:
        # Get events from Pathway pipeline
        events = await _get_repo_events_from_pipeline(
            repo_full_name, limit, event_type, since_minutes
        )

        return RepoEventsResponse(
            repo_full_name=repo_full_name,
            events=events,
            total_count=len(events),
            filtered_type=event_type,
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(
            "Error fetching repository events",
            extra={"repo_id": repo_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to fetch event data",
        )


# Helper functions to interact with Pathway pipeline


async def _get_top_repos_from_pipeline(
    limit: int, time_window: str, min_score: Optional[float]
) -> List[RepoResponse]:
    """
    Get top repositories from Pathway pipeline.

    This function accesses the pipeline's summary tables and returns
    formatted repository data.

    Args:
        limit: Number of repositories to return
        time_window: Time window (1h, 24h, 7d)
        min_score: Minimum score threshold

    Returns:
        List of repository responses
    """
    from backend.api.main import app_state

    pipeline_tables = app_state.get("pipeline_tables")

    if pipeline_tables is None:
        logger.warning("Pipeline not available, returning mock data")
        return _get_mock_top_repos(limit)

    # Select the appropriate summary table based on time window
    table_map = {
        "1h": "summaries_short",
        "24h": "summaries_medium",
        "7d": "summaries_medium",  # Use medium for 7d as well
    }

    summary_table_name = table_map.get(time_window, "summaries_short")
    summary_table = pipeline_tables.get(summary_table_name)

    if summary_table is None:
        logger.warning(f"Summary table '{summary_table_name}' not found")
        return _get_mock_top_repos(limit)

    # TODO: Convert Pathway table to list of RepoResponse objects
    # For now, return mock data
    # In production, you would:
    # 1. Use pw.io.jsonlines output connector or
    # 2. Query via Pathway's HTTP server or
    # 3. Use collect() if running in test mode

    logger.info("Using mock data for top repos (TODO: integrate with pipeline)")
    return _get_mock_top_repos(limit)


async def _get_repo_details_from_pipeline(
    repo_full_name: str, time_window: str
) -> Optional[RepoResponse]:
    """
    Get detailed repository information from Pathway pipeline.

    Args:
        repo_full_name: Repository identifier (owner/repo)
        time_window: Time window for metrics

    Returns:
        Repository details or None if not found
    """
    from backend.api.main import app_state

    pipeline_tables = app_state.get("pipeline_tables")

    if pipeline_tables is None:
        logger.warning("Pipeline not available, returning mock data")
        return _get_mock_repo_details(repo_full_name)

    # TODO: Query specific repo from pipeline tables
    # For now, return mock data

    logger.info(f"Using mock data for repo '{repo_full_name}' (TODO: integrate)")
    return _get_mock_repo_details(repo_full_name)


async def _get_repo_events_from_pipeline(
    repo_full_name: str,
    limit: int,
    event_type: Optional[str],
    since_minutes: Optional[int],
) -> List[EventInfo]:
    """
    Get repository events from Pathway pipeline.

    Args:
        repo_full_name: Repository identifier
        limit: Maximum events to return
        event_type: Event type filter
        since_minutes: Time filter

    Returns:
        List of events
    """
    from backend.api.main import app_state

    pipeline_tables = app_state.get("pipeline_tables")

    if pipeline_tables is None:
        logger.warning("Pipeline not available, returning mock events")
        return _get_mock_events(repo_full_name, limit)

    # TODO: Query events table from pipeline
    # For now, return mock data

    logger.info(f"Using mock data for events (TODO: integrate)")
    return _get_mock_events(repo_full_name, limit)


# Mock data functions (for testing until pipeline integration is complete)


def _get_mock_top_repos(limit: int) -> List[RepoResponse]:
    """Generate mock top repositories for testing."""
    mock_repos = [
        {
            "repo_full_name": "openai/openai-python",
            "activity_score": 18.0,
            "trend_status": "🔥 HOT",
            "momentum": "ACCELERATING",
            "summary": "openai/openai-python is 🔥 HOT with 12 events in 1h window. Activity: 3 commits, 4 PRs, 2 issues, 1 releases. Score: 18 points. Momentum: ACCELERATING.",
            "rank": 1,
        },
        {
            "repo_full_name": "langchain-ai/langchain",
            "activity_score": 15.0,
            "trend_status": "🔥 HOT",
            "momentum": "STEADY",
            "summary": "langchain-ai/langchain is 🔥 HOT with 10 events in 1h window. Activity: 2 commits, 3 PRs, 2 issues, 0 releases. Score: 15 points. Momentum: STEADY.",
            "rank": 2,
        },
        {
            "repo_full_name": "pathwaycom/pathway",
            "activity_score": 12.0,
            "trend_status": "📈 ACTIVE",
            "momentum": "ACCELERATING",
            "summary": "pathwaycom/pathway is 📈 ACTIVE with 8 events in 1h window. Activity: 4 commits, 1 PRs, 2 issues, 0 releases. Score: 12 points. Momentum: ACCELERATING.",
            "rank": 3,
        },
    ]

    return [
        RepoResponse(
            repo_full_name=repo["repo_full_name"],
            activity_score=repo["activity_score"],
            trend_status=repo["trend_status"],
            momentum=repo["momentum"],
            summary=repo["summary"],
            rank=repo["rank"],
            last_updated=datetime.utcnow(),
        )
        for repo in mock_repos[:limit]
    ]


def _get_mock_repo_details(repo_full_name: str) -> RepoResponse:
    """Generate mock repository details."""
    return RepoResponse(
        repo_full_name=repo_full_name,
        activity_score=18.0,
        trend_status="🔥 HOT",
        momentum="ACCELERATING",
        summary=f"{repo_full_name} is 🔥 HOT with 12 events in 1h window.",
        metrics_1h=RepoMetrics(
            events_in_window=12,
            commits_in_window=3,
            prs_in_window=4,
            issues_in_window=2,
            releases_in_window=1,
            activity_score=18.0,
            events_per_hour=12.0,
            score_per_hour=18.0,
        ),
        rank=1,
        last_updated=datetime.utcnow(),
    )


def _get_mock_events(repo_full_name: str, limit: int) -> List[EventInfo]:
    """Generate mock events."""
    return [
        EventInfo(
            event_id=f"commit_{repo_full_name.replace('/', '-')}_abc{i}",
            repo_full_name=repo_full_name,
            event_type="commit",
            timestamp=datetime.utcnow().isoformat(),
            title=f"Mock commit {i}: Update feature",
            author="mock_author",
            url=f"https://github.com/{repo_full_name}/commit/abc{i}",
        )
        for i in range(min(limit, 5))
    ]