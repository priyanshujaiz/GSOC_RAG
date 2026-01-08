"""
Live summary generation for GitHub repositories.
Creates human-readable text summaries for RAG system.
"""

import pathway as pw
from backend.core.logger import get_logger

logger = get_logger(__name__)


class SummaryGenerator:
    """
    Generates natural language summaries of repository activity.
    
    Summaries include:
    - Activity metrics (events, scores)
    - Time-based context (window period)
    - Trend indicators (HOT, ACCELERATING)
    - Key statistics
    """
    
    def __init__(self):
        """Initialize summary generator."""
        logger.info("SummaryGenerator initialized")
    
    def generate_summaries(self, trends_table: pw.Table) -> pw.Table:
        """
        Generate text summaries from trend data using pw.apply().
        
        Args:
            trends_table: Table with all metrics (trends, scores, velocity)
        
        Returns:
            Table with added 'summary' column containing natural language text
        """
        logger.debug("Generating repository summaries")
        
        # ✅ CORRECT: Use pw.apply() with lambda - universal Pathway pattern
        summaries = trends_table.with_columns(
            summary=pw.apply(
                lambda repo, trend, events, window, commits, prs, issues, releases, score, momentum: 
                    f"{repo} is {trend} with {events} events in {window} window. "
                    f"Activity: {commits} commits, {prs} PRs, {issues} issues, {releases} releases. "
                    f"Score: {score} points. Momentum: {momentum}.",
                pw.this.repo_full_name,
                pw.this.trend_status,
                pw.this.events_in_window,
                pw.this.window_period,
                pw.this.commits_in_window,
                pw.this.prs_in_window,
                pw.this.issues_in_window,
                pw.this.releases_in_window,
                pw.this.activity_score,
                pw.this.momentum,
            )
        )
        
        logger.info("Repository summaries generated")
        return summaries


def generate_repository_summaries(trends_table: pw.Table) -> pw.Table:
    """
    Generate natural language summaries for repositories.
    
    Args:
        trends_table: Table with trend data and metrics
    
    Returns:
        Table with summary column added
    
    Example:
        >>> trends = get_trends_table()
        >>> summaries = generate_repository_summaries(trends)
        >>> # Each row now has a 'summary' column with human-readable text
    """
    generator = SummaryGenerator()
    return generator.generate_summaries(trends_table)


def create_top_n_ranking(summaries_table: pw.Table, n: int = 10) -> pw.Table:
    """
    Create Top-N ranking of repositories by activity score.
    
    Note: Pathway doesn't have built-in "top N with rank" operation.
    In production, ranking would be done at query time or in the API layer.
    This function marks repos as "top tier" for filtering.
    
    Args:
        summaries_table: Table with summaries and scores
        n: Number of top repos to identify (default: 10)
    
    Returns:
        Table with ranking indicators
    """
    # Add a "is_top_tier" indicator based on score threshold
    ranked = summaries_table.select(
        pw.this.repo_full_name,
        pw.this.window_period,
        pw.this.summary,
        pw.this.activity_score,
        pw.this.score_per_hour,
        pw.this.trend_status,
        pw.this.momentum,
        
        # Mark as top tier if score is high
        is_top_tier=pw.if_else(
            pw.this.activity_score > 10,
            True,
            False
        ),
    )
    
    logger.info(f"Top-{n} ranking prepared")
    return ranked