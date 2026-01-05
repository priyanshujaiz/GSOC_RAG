"""
GitHub streaming connector for Pathway.
Continuously polls GitHub API and yields events to Pathway tables.
"""

import pathway as pw
from typing import Optional
from datetime import datetime, timedelta
import asyncio
from backend.core.github_client import GitHubClient
from backend.core.config import Settings
from backend.core.logger import get_logger
from backend.utils.github_queries import (
    REPOSITORY_EVENTS_QUERY,
    parse_repository_url,
    build_query_variables,
)
from backend.connectors.event_transformer import GitHubEventTransformer
from backend.connectors.schemas import GitHubEventSchema

logger = get_logger(__name__)

settings = Settings()


class GitHubConnector(pw.io.python.ConnectorSubject):
    """
    Pathway connector that streams GitHub repository events.
    
    Features:
    - Polls multiple repositories at configurable intervals
    - Tracks state to avoid duplicate events
    - Handles rate limiting automatically
    - Transforms events to standardized schema
    """
    
    def __init__(
        self,
        repositories: list[str],
        poll_interval: Optional[int] = None,
        lookback_hours: int = 24,
    ):
        """
        Initialize GitHub streaming connector.
        
        Args:
            repositories: List of repositories to track (e.g., ["owner/repo", ...])
            poll_interval: Seconds between polls (default: from settings)
            lookback_hours: On first run, fetch events from this many hours ago
        """
        super().__init__()
        
        self.repositories = repositories
        self.poll_interval = poll_interval or settings.GITHUB_POLL_INTERVAL
        self.lookback_hours = lookback_hours
        
        # Track last fetch time per repository
        self._last_fetch_times: dict[str, datetime] = {}
        
        # Initialize GitHub client
        self.client = GitHubClient()
        
        # Event transformer
        self.transformer = GitHubEventTransformer()
        
        logger.info(
            "GitHub connector initialized",
            extra={
                "repositories": repositories,
                "poll_interval": self.poll_interval,
                "lookback_hours": lookback_hours,
            }
        )
    
    def run(self) -> None:
        """
        Main connector loop - continuously polls GitHub and yields events.
        
        This method runs forever, polling GitHub at regular intervals.
        """
        logger.info("Starting GitHub connector main loop")
        
        # Verify authentication before starting
        try:
            asyncio.run(self.client.check_authentication())
        except Exception as e:
            logger.error(f"GitHub authentication failed: {e}", exc_info=True)
            raise
        
        # Initialize last fetch times
        self._initialize_fetch_times()
        
        # Main polling loop
        iteration = 0
        while True:
            iteration += 1
            logger.info(f"Starting poll iteration {iteration}")
            
            try:
                # Fetch events for all repositories
                events = asyncio.run(self._fetch_all_events())
                
                # Yield events to Pathway
                if events:
                    logger.info(f"Yielding {len(events)} events to Pathway")
                    for event in events:
                        self.next(**event)
                    
                    # Commit the batch
                    self.commit()
                else:
                    logger.debug("No new events in this iteration")
                
                # Log rate limit status
                rate_limit = self.client.rate_limit_status
                logger.info(
                    f"Rate limit: {rate_limit['remaining']} remaining",
                    extra={"rate_limit": rate_limit}
                )
                
            except Exception as e:
                logger.error(
                    f"Error in poll iteration {iteration}: {e}",
                    exc_info=True
                )
                # Don't crash - continue polling
            
            # Sleep until next poll
            logger.debug(f"Sleeping {self.poll_interval}s until next poll")
            asyncio.run(asyncio.sleep(self.poll_interval))
    
    def _initialize_fetch_times(self) -> None:
        """
        Initialize last fetch times for all repositories.
        On first run, set to lookback_hours ago.
        """
        initial_time = datetime.utcnow() - timedelta(hours=self.lookback_hours)
        
        for repo in self.repositories:
            self._last_fetch_times[repo] = initial_time
        
        logger.info(
            f"Initialized fetch times to {self.lookback_hours}h ago",
            extra={"initial_time": initial_time.isoformat()}
        )
    
    async def _fetch_all_events(self) -> list[dict]:
        """
        Fetch events for all tracked repositories.
        
        Returns:
            List of all events from all repositories
        """
        all_events = []
        
        for repo in self.repositories:
            try:
                events = await self._fetch_repo_events(repo)
                all_events.extend(events)
            except Exception as e:
                logger.error(
                    f"Failed to fetch events for {repo}: {e}",
                    exc_info=True
                )
                # Continue with other repos
                continue
        
        return all_events
    
    async def _fetch_repo_events(self, repo: str) -> list[dict]:
        """
        Fetch events for a single repository.
        
        Args:
            repo: Repository in "owner/repo" format
        
        Returns:
            List of events
        """
        logger.debug(f"Fetching events for {repo}")
        
        # Parse repository URL
        owner, name = parse_repository_url(repo)
        
        # Get last fetch time
        since = self._last_fetch_times.get(repo)
        
        # Build query variables
        variables = build_query_variables(owner, name, since=since)
        
        # Execute query
        response_data = await self.client.execute_query(
            REPOSITORY_EVENTS_QUERY,
            variables
        )
        
        # Transform events
        events = self.transformer.extract_events_from_response(
            response_data,
            repo,
            since=since
        )
        
        # Update last fetch time
        if events:
            # Use the latest event timestamp
            latest_timestamp = max(
                datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                for event in events
            )
            self._last_fetch_times[repo] = latest_timestamp
            
            logger.info(
                f"Fetched {len(events)} events from {repo}",
                extra={
                    "repo": repo,
                    "event_count": len(events),
                    "latest_timestamp": latest_timestamp.isoformat(),
                }
            )
        else:
            # No new events, but update fetch time to now
            self._last_fetch_times[repo] = datetime.utcnow()
        
        return events


# Factory function to create connector and return Pathway table
def create_github_stream(
    repositories: list[str],
    poll_interval: Optional[int] = None,
    lookback_hours: int = 24,
) -> pw.Table:
    """
    Create a GitHub streaming connector and return Pathway table.
    
    Args:
        repositories: List of repositories to track (e.g., ["owner/repo", ...])
        poll_interval: Seconds between polls (default: from settings)
        lookback_hours: On first run, fetch events from this many hours ago
    
    Returns:
        Pathway table with GitHub events
    
    Example:
        >>> repos = ["pathwaycom/pathway", "fastapi/fastapi"]
        >>> events_table = create_github_stream(repos, poll_interval=30)
    """
    # Define schema for the table
    class GitHubEventInputSchema(pw.Schema):
        id: str
        repo_full_name: str
        event_type: str
        timestamp: str
        title: str
        author: str
        url: str
        metadata: str
    
    # Create the connector
    return pw.io.python.read(
        GitHubConnector(
            repositories=repositories,
            poll_interval=poll_interval,
            lookback_hours=lookback_hours,
        ),
        schema=GitHubEventInputSchema,
        autocommit_duration_ms=1000,  # Auto-commit every second
    )