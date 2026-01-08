"""
Velocity calculation for GitHub repositories.
Measures the rate of activity over different time periods.
"""

import pathway as pw
from backend.core.logger import get_logger

logger = get_logger(__name__)


# Time period durations (in hours)
WINDOW_DURATIONS = {
    '1h': 1,
    '24h': 24,
    '7d': 168,  # 7 days * 24 hours
}


class VelocityCalculator:
    """
    Calculates activity velocity (rate) for GitHub repositories.
    
    Velocity metrics:
    - Events per hour
    - Commits per hour
    - PRs per hour
    - Issues per hour
    - Releases per day
    """
    
    def __init__(self, windowed_scored_tables: dict[str, pw.Table]):
        """
        Initialize velocity calculator.
        
        Args:
            windowed_scored_tables: Dictionary of window tables with activity scores
                                   e.g., {'repos_1h_scored': table, ...}
        """
        self.windowed_tables = windowed_scored_tables
        logger.info("VelocityCalculator initialized")
    
    def calculate_velocities(self) -> dict[str, pw.Table]:
        """
        Calculate velocity metrics for each time window.
        
        Returns:
            Dictionary of tables with velocity columns added:
            {
                'repos_1h_velocity': table with velocity metrics,
                'repos_24h_velocity': table with velocity metrics,
                'repos_7d_velocity': table with velocity metrics
            }
        """
        logger.info("Calculating velocity metrics")
        
        result = {}
        
        for table_name, table in self.windowed_tables.items():
            # Extract window period (e.g., 'repos_1h_scored' -> '1h')
            window = table_name.replace('repos_', '').replace('_scored', '')
            
            if window not in WINDOW_DURATIONS:
                logger.warning(f"Unknown window period: {window}, skipping")
                continue
            
            duration_hours = WINDOW_DURATIONS[window]
            
            # Calculate velocities (rate per hour)
            table_with_velocity = table.select(
                # Keep all existing columns
                pw.this.repo_full_name,
                pw.this.window_period,
                pw.this.events_in_window,
                pw.this.commits_in_window,
                pw.this.prs_in_window,
                pw.this.issues_in_window,
                pw.this.releases_in_window,
                pw.this.latest_event_time,
                pw.this.activity_score,
                
                # Add velocity metrics (events per hour)
                events_per_hour=pw.this.events_in_window / duration_hours,
                commits_per_hour=pw.this.commits_in_window / duration_hours,
                prs_per_hour=pw.this.prs_in_window / duration_hours,
                issues_per_hour=pw.this.issues_in_window / duration_hours,
                releases_per_day=(pw.this.releases_in_window / duration_hours) * 24,
                
                # Activity score velocity (points per hour)
                score_per_hour=pw.this.activity_score / duration_hours,
            )
            
            result[f'repos_{window}_velocity'] = table_with_velocity
            logger.debug(f"Calculated velocity for {window} window")
        
        logger.info(f"Velocity metrics calculated for {len(result)} windows")
        return result


def add_velocity_metrics(windowed_scored_tables: dict[str, pw.Table]) -> dict[str, pw.Table]:
    """
    Add velocity metrics to windowed scored tables.
    
    Args:
        windowed_scored_tables: Scored tables for each window
    
    Returns:
        Dictionary with velocity tables:
        {
            'repos_1h_velocity': table,
            'repos_24h_velocity': table,
            'repos_7d_velocity': table
        }
    
    Example:
        >>> scored = {'repos_1h_scored': table1, 'repos_24h_scored': table2}
        >>> velocity = add_velocity_metrics(scored)
        >>> print(velocity.keys())
        dict_keys(['repos_1h_velocity', 'repos_24h_velocity'])
    """
    calculator = VelocityCalculator(windowed_scored_tables)
    return calculator.calculate_velocities()


def get_velocity_summary(velocity_table: pw.Table) -> pw.Table:
    """
    Get a summary of velocities across all repositories.
    
    Args:
        velocity_table: Table with velocity metrics
    
    Returns:
        Summary table with aggregate velocity stats
    """
    # Calculate summary statistics
    summary = velocity_table.reduce(
        total_repos=pw.reducers.count(),
        avg_events_per_hour=pw.reducers.avg(velocity_table.events_per_hour),
        max_events_per_hour=pw.reducers.max(velocity_table.events_per_hour),
        avg_score_per_hour=pw.reducers.avg(velocity_table.score_per_hour),
        max_score_per_hour=pw.reducers.max(velocity_table.score_per_hour),
    )
    
    logger.info("Velocity summary calculated")
    return summary