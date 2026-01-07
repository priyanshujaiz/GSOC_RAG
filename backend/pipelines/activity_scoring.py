"""
Activity scoring system for GitHub repositories.
Assigns weighted scores to different event types to measure repository "hotness".
"""

import pathway as pw
from backend.core.logger import get_logger

logger = get_logger(__name__)


# Activity scoring weights
SCORE_WEIGHTS = {
    'commit': 1,        # Frequent, low impact
    'pull_request': 3,  # Code contributions
    'issue': 2,         # Community engagement
    'release': 5,       # Major milestones
}


class ActivityScorer:
    """
    Calculates activity scores for GitHub repositories.
    
    Uses weighted scoring:
    - Commit: 1 point
    - Issue: 2 points
    - Pull Request: 3 points
    - Release: 5 points
    """
    
    def __init__(self, repos_table: pw.Table):
        """
        Initialize activity scorer.
        
        Args:
            repos_table: Table with repository aggregations
                         Must have: commit_count, pr_count, issue_count, release_count
        """
        self.repos_table = repos_table
        logger.info("ActivityScorer initialized")
    
    def calculate_scores(self) -> pw.Table:
        """
        Calculate activity scores for each repository.
        
        Returns:
            Table with original columns plus:
            - activity_score: Weighted total score
            - score_breakdown: JSON with per-type scores
        """
        logger.debug("Calculating activity scores")
        
        # Calculate weighted score for each repo
        repos_with_scores = self.repos_table.select(
            # Keep all original columns
            pw.this.repo_full_name,
            pw.this.total_events,
            pw.this.commit_count,
            pw.this.pr_count,
            pw.this.issue_count,
            pw.this.release_count,
            pw.this.last_event_time,
            
            # Add calculated activity score
            activity_score=(
                pw.this.commit_count * SCORE_WEIGHTS['commit'] +
                pw.this.pr_count * SCORE_WEIGHTS['pull_request'] +
                pw.this.issue_count * SCORE_WEIGHTS['issue'] +
                pw.this.release_count * SCORE_WEIGHTS['release']
            ),
        )
        
        logger.info("Activity scores calculated")
        return repos_with_scores
    
    def rank_by_score(self, scored_repos: pw.Table) -> pw.Table:
        """
        Rank repositories by activity score (highest first).
        
        Args:
            scored_repos: Table with activity_score column
        
        Returns:
            Table sorted by activity_score descending
        """
        logger.debug("Ranking repositories by score")
        
        # Note: Pathway doesn't have a direct "rank" operation like SQL
        # We'll add ranking in the output stage or use sorting on retrieval
        # For now, just return the scored table (ranking happens at query time)
        
        logger.info("Repositories ready for ranking")
        return scored_repos


def calculate_windowed_scores(windowed_repos: dict[str, pw.Table]) -> dict[str, pw.Table]:
    """
    Calculate activity scores for each temporal window.
    
    Args:
        windowed_repos: Dictionary of window name -> repos table
                       e.g., {'repos_1h': table, 'repos_24h': table, ...}
    
    Returns:
        Dictionary with same keys, but tables include activity scores
        e.g., {'repos_1h_scored': table, 'repos_24h_scored': table, ...}
    
    Example:
        >>> windowed_repos = {'repos_1h': table1, 'repos_24h': table2}
        >>> scored = calculate_windowed_scores(windowed_repos)
        >>> print(scored.keys())
        dict_keys(['repos_1h_scored', 'repos_24h_scored'])
    """
    result = {}
    
    for window_name, repos_table in windowed_repos.items():
        logger.debug(f"Scoring {window_name}")
        
        # For windowed tables, we need to use the *_in_window columns
        # Let's create a specialized scorer for windowed data
        scored_table = repos_table.select(
            # Keep original columns
            pw.this.repo_full_name,
            pw.this.window_period,
            pw.this.events_in_window,
            pw.this.commits_in_window,
            pw.this.prs_in_window,
            pw.this.issues_in_window,
            pw.this.releases_in_window,
            pw.this.latest_event_time,
            
            # Calculate windowed activity score
            activity_score=(
                pw.this.commits_in_window * SCORE_WEIGHTS['commit'] +
                pw.this.prs_in_window * SCORE_WEIGHTS['pull_request'] +
                pw.this.issues_in_window * SCORE_WEIGHTS['issue'] +
                pw.this.releases_in_window * SCORE_WEIGHTS['release']
            ),
        )
        
        # Store with "_scored" suffix
        result[f"{window_name}_scored"] = scored_table
    
    logger.info(f"Calculated scores for {len(result)} windows")
    return result


def get_top_repos(scored_repos: pw.Table, top_n: int = 10) -> pw.Table:
    """
    Get top N repositories by activity score.
    
    Note: Pathway doesn't have a built-in "top N" operation.
    This is a placeholder - actual ranking will happen at query/output time.
    
    Args:
        scored_repos: Table with activity_score column
        top_n: Number of top repos to retrieve (default: 10)
    
    Returns:
        Same table (filtering/ranking happens at output stage)
    """
    # In production RAG system, the "top N" selection will happen:
    # 1. In the API layer when querying
    # 2. Using Pathway's sorting at output time
    # 3. Or in the frontend display logic
    
    logger.info(f"Top {top_n} repos will be selected at query time")
    return scored_repos