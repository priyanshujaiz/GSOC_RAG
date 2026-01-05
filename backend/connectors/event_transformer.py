"""
Transforms GitHub API responses into standardized event format.
"""

from typing import Any
from datetime import datetime
import json
from backend.core.logger import get_logger

logger = get_logger(__name__)


class GitHubEventTransformer:
    """
    Transforms GitHub GraphQL responses into standardized events.
    
    Handles different event types:
    - Commits
    - Pull Requests
    - Issues
    - Releases
    """
    
    @staticmethod
    def transform_commit(commit_data: dict[str, Any], repo_full_name: str, repo_url: str) -> dict[str, Any]:
        """
        Transform a commit from GitHub API to our event format.
        
        Args:
            commit_data: Commit data from GitHub GraphQL
            repo_full_name: Repository in "owner/repo" format
            repo_url: Repository URL
        
        Returns:
            Standardized event dictionary
        """
        oid = commit_data["oid"]
        message = commit_data["message"]
        committed_date = commit_data["committedDate"]
        author = commit_data.get("author", {})
        author_name = author.get("name", "Unknown")
        
        return {
            "id": f"commit_{repo_full_name}_{oid}",
            "repo_full_name": repo_full_name,
            "event_type": "commit",
            "timestamp": committed_date,
            "title": message.split("\n")[0][:100],  # First line, max 100 chars
            "author": author_name,
            "url": f"{repo_url}/commit/{oid}",
            "metadata": json.dumps({
                "sha": oid,
                "full_message": message,
                "author_email": author.get("email"),
            }),
        }
    
    @staticmethod
    def transform_pull_request(pr_data: dict[str, Any], repo_full_name: str, repo_url: str) -> dict[str, Any]:
        """
        Transform a pull request from GitHub API to our event format.
        
        Args:
            pr_data: PR data from GitHub GraphQL
            repo_full_name: Repository in "owner/repo" format
            repo_url: Repository URL
        
        Returns:
            Standardized event dictionary
        """
        number = pr_data["number"]
        title = pr_data["title"]
        state = pr_data["state"]
        created_at = pr_data["createdAt"]
        updated_at = pr_data["updatedAt"]
        merged = pr_data.get("merged", False)
        author = pr_data.get("author", {})
        author_login = author.get("login", "Unknown") if author else "Unknown"
        
        # Use updated_at as timestamp (shows recent activity)
        timestamp = updated_at if updated_at else created_at
        
        return {
            "id": f"pr_{repo_full_name}_{number}",
            "repo_full_name": repo_full_name,
            "event_type": "pull_request",
            "timestamp": timestamp,
            "title": title[:200],  # Max 200 chars
            "author": author_login,
            "url": f"{repo_url}/pull/{number}",
            "metadata": json.dumps({
                "number": number,
                "state": state,
                "merged": merged,
                "created_at": created_at,
                "updated_at": updated_at,
            }),
        }
    
    @staticmethod
    def transform_issue(issue_data: dict[str, Any], repo_full_name: str, repo_url: str) -> dict[str, Any]:
        """
        Transform an issue from GitHub API to our event format.
        
        Args:
            issue_data: Issue data from GitHub GraphQL
            repo_full_name: Repository in "owner/repo" format
            repo_url: Repository URL
        
        Returns:
            Standardized event dictionary
        """
        number = issue_data["number"]
        title = issue_data["title"]
        state = issue_data["state"]
        created_at = issue_data["createdAt"]
        updated_at = issue_data["updatedAt"]
        author = issue_data.get("author", {})
        author_login = author.get("login", "Unknown") if author else "Unknown"
        
        # Use updated_at as timestamp
        timestamp = updated_at if updated_at else created_at
        
        return {
            "id": f"issue_{repo_full_name}_{number}",
            "repo_full_name": repo_full_name,
            "event_type": "issue",
            "timestamp": timestamp,
            "title": title[:200],
            "author": author_login,
            "url": f"{repo_url}/issues/{number}",
            "metadata": json.dumps({
                "number": number,
                "state": state,
                "created_at": created_at,
                "updated_at": updated_at,
            }),
        }
    
    @staticmethod
    def transform_release(release_data: dict[str, Any], repo_full_name: str, repo_url: str) -> dict[str, Any]:
        """
        Transform a release from GitHub API to our event format.
        
        Args:
            release_data: Release data from GitHub GraphQL
            repo_full_name: Repository in "owner/repo" format
            repo_url: Repository URL
        
        Returns:
            Standardized event dictionary
        """
        name = release_data["name"]
        tag_name = release_data["tagName"]
        created_at = release_data["createdAt"]
        author = release_data.get("author", {})
        author_login = author.get("login", "Unknown") if author else "Unknown"
        
        return {
            "id": f"release_{repo_full_name}_{tag_name}",
            "repo_full_name": repo_full_name,
            "event_type": "release",
            "timestamp": created_at,
            "title": name or tag_name,
            "author": author_login,
            "url": f"{repo_url}/releases/tag/{tag_name}",
            "metadata": json.dumps({
                "tag_name": tag_name,
                "name": name,
                "created_at": created_at,
            }),
        }
    
    @classmethod
    def extract_events_from_response(
        cls,
        response_data: dict[str, Any],
        repo_full_name: str,
        since: datetime | None = None
    ) -> list[dict[str, Any]]:
        """
        Extract all events from a GitHub GraphQL response.
        
        Args:
            response_data: Response from GitHub GraphQL query
            repo_full_name: Repository in "owner/repo" format
            since: Only include events after this time
        
        Returns:
            List of standardized events
        """
        events = []
        
        if not response_data or "repository" not in response_data:
            logger.warning(f"No repository data in response for {repo_full_name}")
            return events
        
        repo = response_data["repository"]
        repo_url = repo["url"]
        
        # Extract commits
        if repo.get("defaultBranchRef") and repo["defaultBranchRef"].get("target"):
            target = repo["defaultBranchRef"]["target"]
            if target.get("history") and target["history"].get("edges"):
                for edge in target["history"]["edges"]:
                    commit = edge["node"]
                    event = cls.transform_commit(commit, repo_full_name, repo_url)
                    if cls._is_event_after_since(event, since):
                        events.append(event)
        
        # Extract pull requests
        if repo.get("pullRequests") and repo["pullRequests"].get("edges"):
            for edge in repo["pullRequests"]["edges"]:
                pr = edge["node"]
                event = cls.transform_pull_request(pr, repo_full_name, repo_url)
                if cls._is_event_after_since(event, since):
                    events.append(event)
        
        # Extract issues
        if repo.get("issues") and repo["issues"].get("edges"):
            for edge in repo["issues"]["edges"]:
                issue = edge["node"]
                event = cls.transform_issue(issue, repo_full_name, repo_url)
                if cls._is_event_after_since(event, since):
                    events.append(event)
        
        # Extract releases
        if repo.get("releases") and repo["releases"].get("edges"):
            for edge in repo["releases"]["edges"]:
                release = edge["node"]
                event = cls.transform_release(release, repo_full_name, repo_url)
                if cls._is_event_after_since(event, since):
                    events.append(event)
        
        logger.info(
            f"Extracted {len(events)} events from {repo_full_name}",
            extra={"repo": repo_full_name, "event_count": len(events)}
        )
        
        return events
    
    @staticmethod
    def _is_event_after_since(event: dict[str, Any], since: datetime | None) -> bool:
        """Check if event timestamp is after 'since' time."""
        if since is None:
            return True
        
        # Parse ISO timestamp
        event_time_str = event["timestamp"]
        event_time = datetime.fromisoformat(event_time_str.replace("Z", "+00:00"))
        
        return event_time > since