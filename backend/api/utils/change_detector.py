"""
Change detection for triggering WebSocket updates.
Monitors pipeline data and detects changes to broadcast.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from backend.api.models.websocket_events import (
    create_metrics_update_message,
    create_new_event_message,
    create_ranking_change_message,
    create_summary_update_message,
    create_trend_change_message,
)
from backend.core.logger import get_logger

logger = get_logger(__name__)


class ChangeDetector:
    """
    Detects changes in repository data and generates update messages.
    
    Monitors:
    - New events
    - Summary updates
    - Ranking changes
    - Trend changes
    - System metrics
    """

    def __init__(self):
        """Initialize change detector."""
        self.previous_state: Dict[str, Any] = {
            "summaries": {},  # repo_name -> summary
            "rankings": {},  # repo_name -> rank
            "trends": {},  # repo_name -> (trend_status, momentum)
            "event_ids": set(),  # Set of processed event IDs
            "metrics": {},  # System metrics
        }
        
        self.change_callbacks: List = []
        logger.info("ChangeDetector initialized")

    def register_callback(self, callback) -> None:
        """
        Register a callback to be called when changes are detected.
        
        Args:
            callback: Async function to call with change messages
        """
        self.change_callbacks.append(callback)
        logger.info(f"Registered change callback: {callback.__name__}")

    async def check_for_changes(
        self,
        current_summaries: Dict[str, Dict],
        current_rankings: Dict[str, int],
        current_trends: Dict[str, Dict],
        current_events: List[Dict],
        current_metrics: Dict[str, int],
    ) -> List[Dict[str, Any]]:
        """
        Check for changes between previous and current state.
        
        Args:
            current_summaries: Current repository summaries
            current_rankings: Current repository rankings
            current_trends: Current trend information
            current_events: Current event list
            current_metrics: Current system metrics
            
        Returns:
            List of change messages to broadcast
        """
        messages = []

        # 1. Check for new events
        new_event_messages = self._detect_new_events(current_events)
        messages.extend(new_event_messages)

        # 2. Check for summary changes
        summary_messages = self._detect_summary_changes(current_summaries)
        messages.extend(summary_messages)

        # 3. Check for ranking changes
        ranking_messages = self._detect_ranking_changes(current_rankings)
        messages.extend(ranking_messages)

        # 4. Check for trend changes
        trend_messages = self._detect_trend_changes(current_trends)
        messages.extend(trend_messages)

        # 5. Check for metrics changes
        metrics_messages = self._detect_metrics_changes(current_metrics)
        messages.extend(metrics_messages)

        # Notify callbacks
        if messages:
            await self._notify_callbacks(messages)

        return messages

    def _detect_new_events(self, current_events: List[Dict]) -> List[Dict]:
        """
        Detect new events that haven't been seen before.
        
        Args:
            current_events: List of current events
            
        Returns:
            List of new event messages
        """
        messages = []
        
        for event in current_events:
            event_id = event.get("event_id")
            
            if event_id and event_id not in self.previous_state["event_ids"]:
                # New event detected!
                message = create_new_event_message(
                    event_id=event_id,
                    repo_full_name=event.get("repo_full_name", "unknown"),
                    event_type=event.get("event_type", "unknown"),
                    title=event.get("title", ""),
                    author=event.get("author", "unknown"),
                    url=event.get("url", ""),
                )
                messages.append(message)
                
                # Mark as seen
                self.previous_state["event_ids"].add(event_id)
                
                logger.debug(
                    f"New event detected: {event_id}",
                    extra={"repo": event.get("repo_full_name")}
                )
        
        return messages

    def _detect_summary_changes(
        self, current_summaries: Dict[str, Dict]
    ) -> List[Dict]:
        """
        Detect changes in repository summaries.
        
        Args:
            current_summaries: Current summaries
            
        Returns:
            List of summary update messages
        """
        messages = []
        
        for repo_name, summary_data in current_summaries.items():
            previous = self.previous_state["summaries"].get(repo_name)
            
            # Check if summary changed
            current_summary = summary_data.get("summary", "")
            previous_summary = previous.get("summary", "") if previous else ""
            
            if current_summary != previous_summary:
                message = create_summary_update_message(
                    repo_full_name=repo_name,
                    summary=current_summary,
                    activity_score=summary_data.get("activity_score", 0.0),
                    trend_status=summary_data.get("trend_status", "UNKNOWN"),
                    momentum=summary_data.get("momentum", "UNKNOWN"),
                    events_in_window=summary_data.get("events_in_window", 0),
                )
                messages.append(message)
                
                logger.debug(
                    f"Summary changed for {repo_name}",
                    extra={"repo": repo_name}
                )
            
            # Update state
            self.previous_state["summaries"][repo_name] = summary_data
        
        return messages

    def _detect_ranking_changes(
        self, current_rankings: Dict[str, int]
    ) -> List[Dict]:
        """
        Detect changes in repository rankings.
        
        Args:
            current_rankings: Current rankings (repo_name -> rank)
            
        Returns:
            List of ranking change messages
        """
        messages = []
        
        for repo_name, new_rank in current_rankings.items():
            old_rank = self.previous_state["rankings"].get(repo_name)
            
            if old_rank != new_rank:
                # Get activity score from summaries
                activity_score = (
                    self.previous_state["summaries"]
                    .get(repo_name, {})
                    .get("activity_score", 0.0)
                )
                
                message = create_ranking_change_message(
                    repo_full_name=repo_name,
                    old_rank=old_rank,
                    new_rank=new_rank,
                    activity_score=activity_score,
                )
                messages.append(message)
                
                logger.info(
                    f"Ranking changed for {repo_name}: {old_rank} -> {new_rank}",
                    extra={"repo": repo_name, "old_rank": old_rank, "new_rank": new_rank}
                )
        
        # Update state
        self.previous_state["rankings"] = current_rankings.copy()
        
        return messages

    def _detect_trend_changes(self, current_trends: Dict[str, Dict]) -> List[Dict]:
        """
        Detect changes in repository trends.
        
        Args:
            current_trends: Current trend information
            
        Returns:
            List of trend change messages
        """
        messages = []
        
        for repo_name, trend_data in current_trends.items():
            previous = self.previous_state["trends"].get(repo_name)
            
            new_trend = trend_data.get("trend_status")
            new_momentum = trend_data.get("momentum")
            
            old_trend = previous.get("trend_status") if previous else None
            old_momentum = previous.get("momentum") if previous else None
            
            # Check if trend or momentum changed
            if new_trend != old_trend or new_momentum != old_momentum:
                message = create_trend_change_message(
                    repo_full_name=repo_name,
                    old_trend=old_trend,
                    new_trend=new_trend,
                    old_momentum=old_momentum,
                    new_momentum=new_momentum,
                )
                messages.append(message)
                
                logger.info(
                    f"Trend changed for {repo_name}",
                    extra={
                        "repo": repo_name,
                        "old_trend": old_trend,
                        "new_trend": new_trend,
                    }
                )
            
            # Update state
            self.previous_state["trends"][repo_name] = trend_data
        
        return messages

    def _detect_metrics_changes(self, current_metrics: Dict[str, int]) -> List[Dict]:
        """
        Detect significant changes in system metrics.
        
        Args:
            current_metrics: Current system metrics
            
        Returns:
            List of metrics update messages
        """
        messages = []
        
        previous = self.previous_state["metrics"]
        
        # Only broadcast if metrics changed significantly
        if not previous or self._metrics_changed_significantly(previous, current_metrics):
            message = create_metrics_update_message(
                total_events=current_metrics.get("total_events", 0),
                active_repositories=current_metrics.get("active_repositories", 0),
                total_queries=current_metrics.get("total_queries", 0),
            )
            messages.append(message)
            
            logger.debug("Metrics updated", extra=current_metrics)
        
        # Update state
        self.previous_state["metrics"] = current_metrics.copy()
        
        return messages

    def _metrics_changed_significantly(
        self, old: Dict[str, int], new: Dict[str, int]
    ) -> bool:
        """
        Check if metrics changed significantly enough to broadcast.
        
        Args:
            old: Previous metrics
            new: Current metrics
            
        Returns:
            True if significant change detected
        """
        # Define thresholds
        thresholds = {
            "total_events": 10,  # Every 10 events
            "active_repositories": 1,  # Any change
            "total_queries": 5,  # Every 5 queries
        }
        
        for key, threshold in thresholds.items():
            old_val = old.get(key, 0)
            new_val = new.get(key, 0)
            
            if abs(new_val - old_val) >= threshold:
                return True
        
        return False

    async def _notify_callbacks(self, messages: List[Dict]) -> None:
        """
        Notify all registered callbacks with change messages.
        
        Args:
            messages: List of change messages
        """
        for callback in self.change_callbacks:
            try:
                await callback(messages)
            except Exception as e:
                logger.error(
                    f"Callback error: {e}",
                    extra={"callback": callback.__name__},
                    exc_info=True
                )

    def reset_state(self) -> None:
        """Reset detector state (useful for testing)."""
        self.previous_state = {
            "summaries": {},
            "rankings": {},
            "trends": {},
            "event_ids": set(),
            "metrics": {},
        }
        logger.info("ChangeDetector state reset")

    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get summary of current state.
        
        Returns:
            Dictionary with state statistics
        """
        return {
            "tracked_repositories": len(self.previous_state["summaries"]),
            "tracked_events": len(self.previous_state["event_ids"]),
            "registered_callbacks": len(self.change_callbacks),
        }