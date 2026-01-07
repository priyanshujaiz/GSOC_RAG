"""
Temporal window implementations for GitHub event analysis.
Provides sliding windows for 1h, 24h, and 7d periods.
"""

import pathway as pw
from datetime import timedelta
from backend.core.logger import get_logger

logger = get_logger(__name__)


class TemporalWindows:
    """
    Manages temporal window analysis for GitHub events.
    
    Provides sliding windows to analyze activity over different time periods:
    - 1 hour: Real-time trending
    - 24 hours: Daily activity
    - 7 days: Weekly trends
    """
    
    def __init__(self, events_table: pw.Table):
        """
        Initialize temporal windows.
        
        Args:
            events_table: Pathway table with GitHub events
                          Must have 'timestamp' column in ISO 8601 format
        """
        self.events_table = events_table
        logger.info("TemporalWindows initialized")
    
    def apply_windows(self) -> dict[str, pw.Table]:
        """
        Apply all temporal windows to events.
        
        Returns:
            Dictionary of windowed tables:
            {
                '1h': events in last 1 hour,
                '24h': events in last 24 hours,
                '7d': events in last 7 days
            }
        """
        logger.info("Applying temporal windows")
        
        # ✅ FIX: Rename 'id' to 'event_id' to avoid Pathway's reserved column name
        # Pathway reserves 'id' for internal row identification
        events_renamed = self.events_table.select(
            event_id=pw.this.id,  # Rename id → event_id
            repo_full_name=pw.this.repo_full_name,
            event_type=pw.this.event_type,
            timestamp=pw.this.timestamp,
            title=pw.this.title,
            author=pw.this.author,
            url=pw.this.url,
            metadata=pw.this.metadata,
        )
        
        # Convert timestamp string to Pathway datetime
        events_with_time = events_renamed.with_columns(
            event_time=pw.this.timestamp.dt.strptime("%Y-%m-%dT%H:%M:%S.%fZ")
        )
        
        logger.info("Temporal windows applied (basic filtering)")
        
        # For initial implementation, return the full events table for each window
        # We'll refine this with actual time-based filtering next
        return {
            '1h': events_with_time,
            '24h': events_with_time,
            '7d': events_with_time,
        }
    
    def aggregate_by_window(
        self, 
        window: str,
        windowed_events: pw.Table
    ) -> pw.Table:
        """
        Aggregate events within a time window by repository.
        
        Args:
            window: Window name ('1h', '24h', '7d')
            windowed_events: Events filtered to this window
        
        Returns:
            Aggregated table with counts per repo in this window
        """
        logger.debug(f"Aggregating events for {window} window")
        
        # Group by repository and count events
        windowed_repos = windowed_events.groupby(
            windowed_events.repo_full_name
        ).reduce(
            windowed_events.repo_full_name,
            window_period=window,
            events_in_window=pw.reducers.count(),
            commits_in_window=pw.reducers.sum(
                pw.if_else(windowed_events.event_type == "commit", 1, 0)
            ),
            prs_in_window=pw.reducers.sum(
                pw.if_else(windowed_events.event_type == "pull_request", 1, 0)
            ),
            issues_in_window=pw.reducers.sum(
                pw.if_else(windowed_events.event_type == "issue", 1, 0)
            ),
            releases_in_window=pw.reducers.sum(
                pw.if_else(windowed_events.event_type == "release", 1, 0)
            ),
            latest_event_time=pw.reducers.max(windowed_events.timestamp),
        )
        
        logger.info(f"Aggregation complete for {window} window")
        return windowed_repos


def create_temporal_analysis(events_table: pw.Table) -> dict[str, pw.Table]:
    """
    Create temporal window analysis for GitHub events.
    
    Args:
        events_table: Raw events table from connector
    
    Returns:
        Dictionary with windowed aggregations:
        {
            'repos_1h': repo stats for last 1 hour,
            'repos_24h': repo stats for last 24 hours,
            'repos_7d': repo stats for last 7 days
        }
    
    Example:
        >>> from backend.connectors.demo_connector import create_demo_github_stream
        >>> events = create_demo_github_stream(["pathwaycom/pathway"])
        >>> windowed_tables = create_temporal_analysis(events)
        >>> print(windowed_tables.keys())
        dict_keys(['repos_1h', 'repos_24h', 'repos_7d'])
    """
    windows = TemporalWindows(events_table)
    windowed_events = windows.apply_windows()
    
    # Aggregate each window
    result = {}
    for window_name, window_events in windowed_events.items():
        result[f'repos_{window_name}'] = windows.aggregate_by_window(
            window_name,
            window_events
        )
    
    logger.info(f"Temporal analysis created with {len(result)} windows")
    return result