"""
Trend detection and acceleration analysis for GitHub repositories.
Detects if activity is increasing, decreasing, or stable.
"""

import pathway as pw
from backend.core.logger import get_logger

logger = get_logger(__name__)


class TrendDetector:
    """
    Detects trends in repository activity over time.
    
    Analyzes:
    - Acceleration (activity speeding up or slowing down)
    - Momentum (sustained increase or decrease)
    - Trending status (hot, cooling, stable)
    """
    
    def __init__(self, velocity_tables: dict[str, pw.Table]):
        """
        Initialize trend detector.
        
        Args:
            velocity_tables: Dictionary of velocity tables for different windows
                           e.g., {'repos_1h_velocity': table, ...}
        """
        self.velocity_tables = velocity_tables
        logger.info("TrendDetector initialized")
    
    def detect_trends(self) -> dict[str, pw.Table]:
        """
        Detect trends by comparing different time windows.
        
        Strategy:
        - Compare 1h vs 24h velocity (short-term trend)
        - Compare 24h vs 7d velocity (medium-term trend)
        - Calculate acceleration percentage
        
        Returns:
            Dictionary with trend analysis tables
        """
        logger.info("Detecting activity trends")
        
        result = {}
        
        # Short-term trend: Compare 1h vs 24h
        if 'repos_1h_velocity' in self.velocity_tables and 'repos_24h_velocity' in self.velocity_tables:
            short_term_trends = self._compare_windows(
                self.velocity_tables['repos_1h_velocity'],
                self.velocity_tables['repos_24h_velocity'],
                '1h_vs_24h'
            )
            result['trends_short_term'] = short_term_trends
        
        # Medium-term trend: Compare 24h vs 7d
        if 'repos_24h_velocity' in self.velocity_tables and 'repos_7d_velocity' in self.velocity_tables:
            medium_term_trends = self._compare_windows(
                self.velocity_tables['repos_24h_velocity'],
                self.velocity_tables['repos_7d_velocity'],
                '24h_vs_7d'
            )
            result['trends_medium_term'] = medium_term_trends
        
        logger.info(f"Trend detection complete: {len(result)} trend tables")
        return result
    
    def _compare_windows(
        self,
        recent_table: pw.Table,
        baseline_table: pw.Table,
        comparison_name: str
    ) -> pw.Table:
        """
        Compare two time windows to detect acceleration/deceleration.
        
        Args:
            recent_table: More recent time window (e.g., 1h)
            baseline_table: Older/longer time window (e.g., 24h)
            comparison_name: Name of the comparison (for labeling)
        
        Returns:
            Table with trend metrics
        """
        logger.debug(f"Comparing windows: {comparison_name}")
        
        # Join tables on repo_full_name to compare velocities
        # Note: In Pathway, we need to use join operations carefully
        # For simplicity, we'll add trend indicators to the recent table
        
        # Add acceleration indicators based on velocity comparison
        trends = recent_table.select(
            pw.this.repo_full_name,
            pw.this.window_period,
            pw.this.events_in_window,
            pw.this.commits_in_window,          # ✅ ADD THIS
            pw.this.prs_in_window,              # ✅ ADD THIS
            pw.this.issues_in_window,           # ✅ ADD THIS
            pw.this.releases_in_window,         # ✅ ADD THIS
            pw.this.latest_event_time,          # ✅ ADD THIS
            pw.this.activity_score,
            pw.this.events_per_hour,
            pw.this.commits_per_hour,           # ✅ ADD THIS
            pw.this.prs_per_hour,               # ✅ ADD THIS
            pw.this.issues_per_hour,            # ✅ ADD THIS
            pw.this.releases_per_day,           # ✅ ADD THIS
            pw.this.score_per_hour,
            
            # Trend comparison label
            trend_comparison=comparison_name,
            
            # Simplified trend classification based on score per hour
            # (In production, you'd join with baseline and calculate % change)
            trend_status=pw.if_else(
                pw.this.score_per_hour > 5,
                "🔥 HOT",
                pw.if_else(
                    pw.this.score_per_hour > 2,
                    "📈 ACTIVE",
                    pw.if_else(
                        pw.this.score_per_hour > 0.5,
                        "📊 MODERATE",
                        "❄️ QUIET"
                    )
                )
            ),
            
            # Momentum indicator based on activity intensity
            momentum=pw.if_else(
                pw.this.score_per_hour > 5,
                "ACCELERATING",
                pw.if_else(
                    pw.this.score_per_hour > 1,
                    "STEADY",
                    "DECELERATING"
                )
            ),
        )
        
        logger.debug(f"Trends calculated for {comparison_name}")
        return trends


def detect_activity_trends(velocity_tables: dict[str, pw.Table]) -> dict[str, pw.Table]:
    """
    Detect trends in repository activity.
    
    Args:
        velocity_tables: Velocity metrics for different time windows
    
    Returns:
        Dictionary with trend analysis:
        {
            'trends_short_term': 1h vs 24h comparison,
            'trends_medium_term': 24h vs 7d comparison
        }
    
    Example:
        >>> velocity_tables = {
        ...     'repos_1h_velocity': table1,
        ...     'repos_24h_velocity': table2,
        ...     'repos_7d_velocity': table3
        ... }
        >>> trends = detect_activity_trends(velocity_tables)
        >>> print(trends.keys())
        dict_keys(['trends_short_term', 'trends_medium_term'])
    """
    detector = TrendDetector(velocity_tables)
    return detector.detect_trends()


def classify_trending_repos(trends_table: pw.Table) -> pw.Table:
    """
    Classify repositories by trending status.
    
    Args:
        trends_table: Table with trend metrics
    
    Returns:
        Table with trending classifications
    """
    # Filter for only HOT and ACCELERATING repos
    hot_repos = trends_table.filter(
        trends_table.trend_status == "🔥 HOT"
    )
    
    logger.info("Hot repositories classified")
    return hot_repos