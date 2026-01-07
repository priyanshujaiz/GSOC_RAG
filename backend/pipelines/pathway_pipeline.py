"""
Pathway pipeline for processing GitHub events.
This is the main data processing pipeline that transforms raw events
into meaningful metrics and summaries.
"""

import pathway as pw
from typing import Optional
from backend.core.logger import get_logger
from backend.core.config import Settings
from backend.pipelines.temporal_windows import create_temporal_analysis
from backend.pipelines.activity_scoring import ActivityScorer, calculate_windowed_scores

logger = get_logger(__name__)
settings = Settings()

class GitHubPipeline:
    """
    Main Pathway pipeline for GitHub event processing.
    
    This pipeline takes raw GitHub events and processes them through
    multiple transformation stages to produce metrics, summaries, and rankings.
    """
    
    def __init__(self, events_table: pw.Table):
        """
        Initialize the pipeline with an input events table.
        
        Args:
            events_table: Pathway table containing GitHub events from connector
        """
        self.events_table = events_table
        
        # These will be populated by transformation methods
        self.repos_table: Optional[pw.Table] = None
        self.metrics_table: Optional[pw.Table] = None
        
        logger.info("GitHubPipeline initialized")
    
    def build(self) -> dict[str, pw.Table]:
        """
        Build the complete pipeline and return all output tables.
        
        Returns:
            Dictionary of table names to Pathway tables
        """
        logger.info("Building Pathway pipeline")
        
        # Stage 1: Basic event processing
        processed_events = self._process_events()
        
        # Stage 2: Filter by event type (NEW!)
        filtered_tables = self._filter_by_type(processed_events)
        
        # Stage 3: Repository-level aggregations
        self.repos_table = self._aggregate_by_repo(processed_events)
        
        # Stage 4: Metrics calculation
        self.metrics_table = self._calculate_metrics(self.repos_table)
        

        temporal_tables = create_temporal_analysis(processed_events)
        scorer = ActivityScorer(self.repos_table)
        repos_scored = scorer.calculate_scores()

        windowed_scored = calculate_windowed_scores(temporal_tables)
        
        logger.info("Pipeline built successfully with temporal analysis")
        
        return {
            'events': processed_events,
            'commits': filtered_tables['commits'],
            'prs': filtered_tables['prs'],
            'issues': filtered_tables['issues'],
            'releases': filtered_tables['releases'],
            'repos': self.repos_table,
            'repos_scored': repos_scored,
            'metrics': self.metrics_table,
            **temporal_tables,
            **windowed_scored,
        }

    def _filter_by_type(self, events: pw.Table) -> dict[str, pw.Table]:
        """
        Filter events by type into separate tables.
        
        Args:
            events: All events table
        
        Returns:
            Dictionary with filtered tables:
            {
                'commits': commits only,
                'prs': pull requests only,
                'issues': issues only,
                'releases': releases only
            }
        """
        logger.debug("Filtering events by type")
        
        # Filter for each event type
        commits = events.filter(events.event_type == "commit")
        prs = events.filter(events.event_type == "pull_request")
        issues = events.filter(events.event_type == "issue")
        releases = events.filter(events.event_type == "release")
        
        # Count events in each table (for logging)
        commits_count = commits.reduce(count=pw.reducers.count())
        prs_count = prs.reduce(count=pw.reducers.count())
        issues_count = issues.reduce(count=pw.reducers.count())
        releases_count = releases.reduce(count=pw.reducers.count())
        
        logger.info(
            "Events filtered by type",
            extra={
                "filter_types": ["commit", "pull_request", "issue", "release"]
            }
        )
        
        return {
            'commits': commits,
            'prs': prs,
            'issues': issues,
            'releases': releases,
        }
    
    def _process_events(self) -> pw.Table:
        """
        Process raw events - add computed fields, filters, etc.
        
        Returns:
            Processed events table
        """
        # For now, just return the raw events
        # We'll add transformations in Task 3
        logger.debug("Processing events (no transformations yet)")
        return self.events_table
    
    def _aggregate_by_repo(self, events: pw.Table) -> pw.Table:
        """
        Aggregate events by repository.
        
        Args:
            events: Processed events table
        
        Returns:
            Repository-level aggregation table
        """
        logger.debug("Aggregating events by repository")
        repos = events.groupby(events.repo_full_name).reduce(
            events.repo_full_name,
            total_events=pw.reducers.count(),
            commit_count=pw.reducers.sum(
                pw.if_else(events.event_type == "commit", 1, 0)
            ),
            pr_count=pw.reducers.sum(
                pw.if_else(events.event_type == "pull_request", 1, 0)
            ),
            issue_count=pw.reducers.sum(
                pw.if_else(events.event_type == "issue", 1, 0)
            ),
            release_count=pw.reducers.sum(
                pw.if_else(events.event_type == "release", 1, 0)
            ),
            last_event_time=pw.reducers.max(events.timestamp),
        )
        
        logger.info("Repository aggregations computed")
        return repos
    
    def _calculate_metrics(self, repos: pw.Table) -> pw.Table:
        """
        Calculate metrics from repository aggregations.
        
        Args:
            repos: Repository-level table
        
        Returns:
            Metrics table
        """
        logger.debug("Calculating global metrics")
        # Calculate overall metrics across all repos
        metrics = repos.reduce(
            total_repos=pw.reducers.count(),
            total_events=pw.reducers.sum(repos.total_events),
            total_commits=pw.reducers.sum(repos.commit_count),
            total_prs=pw.reducers.sum(repos.pr_count),
            total_issues=pw.reducers.sum(repos.issue_count),
            total_releases=pw.reducers.sum(repos.release_count),
        )
        
        logger.info("Global metrics computed")
        return metrics


def create_pipeline(events_table: pw.Table) -> GitHubPipeline:
    """
    Factory function to create a GitHubPipeline instance.
    
    Args:
        events_table: Input events table from connector
    
    Returns:
        Configured GitHubPipeline instance
    
    Example:
        >>> from backend.connectors.github_connector import create_github_stream
        >>> events = create_github_stream(["pathwaycom/pathway"])
        >>> pipeline = create_pipeline(events)
        >>> tables = pipeline.build()
    """
    pipeline = GitHubPipeline(events_table)
    return pipeline