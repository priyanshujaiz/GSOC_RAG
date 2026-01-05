"""
Demo/Mock connector for testing without GitHub API.
Simulates GitHub events with controllable timing and content.
"""

import pathway as pw
from typing import Optional
from datetime import datetime, timedelta
import time
import random
from backend.core.logger import get_logger
from backend.connectors.schemas import GitHubEventSchema

logger = get_logger(__name__)


class DemoGitHubConnector(pw.io.python.ConnectorSubject):
    """
    Demo connector that simulates GitHub events.
    
    Features:
    - Generates realistic fake events
    - Controllable event rate
    - No API calls required
    - Perfect for testing
    """
    
    # Sample data for realistic events
    SAMPLE_REPOS = [
        "pathwaycom/pathway",
        "fastapi/fastapi",
        "langchain-ai/langchain",
        "openai/openai-python",
        "microsoft/vscode",
    ]
    
    SAMPLE_AUTHORS = [
        "alice_dev",
        "bob_coder",
        "charlie_eng",
        "diana_tech",
        "eve_programmer",
    ]
    
    SAMPLE_COMMIT_MESSAGES = [
        "Fix bug in authentication",
        "Add new feature for data processing",
        "Update documentation",
        "Refactor core module",
        "Improve performance",
        "Fix typo in README",
        "Add unit tests",
        "Update dependencies",
        "Optimize database queries",
        "Fix security vulnerability",
    ]
    
    SAMPLE_PR_TITLES = [
        "Feature: Add dark mode support",
        "Fix: Memory leak in worker thread",
        "Docs: Update installation guide",
        "Chore: Update CI/CD pipeline",
        "Refactor: Simplify authentication logic",
        "Enhancement: Improve error messages",
        "Fix: Handle edge case in parser",
        "Feature: Add export functionality",
        "Performance: Optimize render loop",
        "Security: Update vulnerable dependency",
    ]
    
    SAMPLE_ISSUE_TITLES = [
        "Bug: Application crashes on startup",
        "Feature Request: Add batch processing",
        "Question: How to configure logging?",
        "Bug: Incorrect data validation",
        "Enhancement: Better error handling needed",
        "Documentation: Missing API examples",
        "Bug: Memory usage too high",
        "Feature: Support for new file format",
        "Question: Best practices for deployment?",
        "Bug: UI not responsive on mobile",
    ]
    
    SAMPLE_RELEASE_NAMES = [
        "v1.0.0 - Initial Release",
        "v1.1.0 - Feature Update",
        "v1.1.1 - Bug Fixes",
        "v2.0.0 - Major Update",
        "v2.1.0 - Performance Improvements",
    ]
    
    def __init__(
        self,
        repositories: Optional[list[str]] = None,
        events_per_batch: int = 10,
        batch_interval: int = 5,
        event_types: Optional[list[str]] = None,
    ):
        """
        Initialize demo connector.
        
        Args:
            repositories: List of repos to simulate (default: use samples)
            events_per_batch: Number of events to generate per batch
            batch_interval: Seconds between batches
            event_types: Types to generate (default: all types)
        """
        super().__init__()
        
        self.repositories = repositories or self.SAMPLE_REPOS
        self.events_per_batch = events_per_batch
        self.batch_interval = batch_interval
        self.event_types = event_types or ["commit", "pull_request", "issue", "release"]
        
        self._event_counter = 0
        
        logger.info(
            "Demo connector initialized",
            extra={
                "repositories": self.repositories,
                "events_per_batch": events_per_batch,
                "batch_interval": batch_interval,
                "event_types": self.event_types,
            }
        )
    
    def run(self) -> None:
        """
        Main loop - generates events at regular intervals.
        """
        logger.info("Starting demo connector main loop")
        
        batch_num = 0
        
        while True:
            batch_num += 1
            logger.info(f"Generating batch {batch_num}")
            
            try:
                # Generate events
                events = self._generate_event_batch()
                
                # Yield to Pathway
                for event in events:
                    self.next(**event)
                
                # Commit batch
                self.commit()
                
                logger.info(
                    f"Generated {len(events)} demo events",
                    extra={"batch": batch_num, "event_count": len(events)}
                )
                
            except Exception as e:
                logger.error(f"Error generating demo events: {e}", exc_info=True)
            
            # Sleep until next batch
            time.sleep(self.batch_interval)
    
    def _generate_event_batch(self) -> list[dict]:
        """
        Generate a batch of fake events.
        
        Returns:
            List of event dictionaries
        """
        events = []
        
        for _ in range(self.events_per_batch):
            event_type = random.choice(self.event_types)
            
            if event_type == "commit":
                event = self._generate_commit_event()
            elif event_type == "pull_request":
                event = self._generate_pr_event()
            elif event_type == "issue":
                event = self._generate_issue_event()
            elif event_type == "release":
                event = self._generate_release_event()
            else:
                continue
            
            events.append(event)
        
        return events
    
    def _generate_commit_event(self) -> dict:
        """Generate a fake commit event."""
        self._event_counter += 1
        repo = random.choice(self.repositories)
        author = random.choice(self.SAMPLE_AUTHORS)
        message = random.choice(self.SAMPLE_COMMIT_MESSAGES)
        
        # Random timestamp within last hour
        timestamp = datetime.utcnow() - timedelta(minutes=random.randint(0, 60))
        
        return {
            "id": f"demo_commit_{repo}_{self._event_counter}",
            "repo_full_name": repo,
            "event_type": "commit",
            "timestamp": timestamp.isoformat() + "Z",
            "title": message,
            "author": author,
            "url": f"https://github.com/{repo}/commit/demo{self._event_counter}",
            "metadata": f'{{"sha": "demo{self._event_counter}", "demo": true}}',
        }
    
    def _generate_pr_event(self) -> dict:
        """Generate a fake pull request event."""
        self._event_counter += 1
        repo = random.choice(self.repositories)
        author = random.choice(self.SAMPLE_AUTHORS)
        title = random.choice(self.SAMPLE_PR_TITLES)
        state = random.choice(["OPEN", "CLOSED", "MERGED"])
        
        timestamp = datetime.utcnow() - timedelta(minutes=random.randint(0, 60))
        
        return {
            "id": f"demo_pr_{repo}_{self._event_counter}",
            "repo_full_name": repo,
            "event_type": "pull_request",
            "timestamp": timestamp.isoformat() + "Z",
            "title": title,
            "author": author,
            "url": f"https://github.com/{repo}/pull/{self._event_counter}",
            "metadata": f'{{"number": {self._event_counter}, "state": "{state}", "demo": true}}',
        }
    
    def _generate_issue_event(self) -> dict:
        """Generate a fake issue event."""
        self._event_counter += 1
        repo = random.choice(self.repositories)
        author = random.choice(self.SAMPLE_AUTHORS)
        title = random.choice(self.SAMPLE_ISSUE_TITLES)
        state = random.choice(["OPEN", "CLOSED"])
        
        timestamp = datetime.utcnow() - timedelta(minutes=random.randint(0, 60))
        
        return {
            "id": f"demo_issue_{repo}_{self._event_counter}",
            "repo_full_name": repo,
            "event_type": "issue",
            "timestamp": timestamp.isoformat() + "Z",
            "title": title,
            "author": author,
            "url": f"https://github.com/{repo}/issues/{self._event_counter}",
            "metadata": f'{{"number": {self._event_counter}, "state": "{state}", "demo": true}}',
        }
    
    def _generate_release_event(self) -> dict:
        """Generate a fake release event."""
        self._event_counter += 1
        repo = random.choice(self.repositories)
        author = random.choice(self.SAMPLE_AUTHORS)
        name = random.choice(self.SAMPLE_RELEASE_NAMES)
        
        timestamp = datetime.utcnow() - timedelta(hours=random.randint(1, 24))
        
        return {
            "id": f"demo_release_{repo}_{self._event_counter}",
            "repo_full_name": repo,
            "event_type": "release",
            "timestamp": timestamp.isoformat() + "Z",
            "title": name,
            "author": author,
            "url": f"https://github.com/{repo}/releases/tag/demo-v{self._event_counter}",
            "metadata": f'{{"tag_name": "demo-v{self._event_counter}", "demo": true}}',
        }


# Factory function
def create_demo_github_stream(
    repositories: Optional[list[str]] = None,
    events_per_batch: int = 10,
    batch_interval: int = 5,
    event_types: Optional[list[str]] = None,
) -> pw.Table:
    """
    Create a demo GitHub streaming connector.
    
    Args:
        repositories: List of repos to simulate
        events_per_batch: Events to generate per batch
        batch_interval: Seconds between batches
        event_types: Types to generate
    
    Returns:
        Pathway table with demo events
    
    Example:
        >>> events = create_demo_github_stream(events_per_batch=5, batch_interval=10)
    """
    class GitHubEventInputSchema(pw.Schema):
        id: str
        repo_full_name: str
        event_type: str
        timestamp: str
        title: str
        author: str
        url: str
        metadata: str
    
    return pw.io.python.read(
        DemoGitHubConnector(
            repositories=repositories,
            events_per_batch=events_per_batch,
            batch_interval=batch_interval,
            event_types=event_types,
        ),
        schema=GitHubEventInputSchema,
        autocommit_duration_ms=1000,
    )