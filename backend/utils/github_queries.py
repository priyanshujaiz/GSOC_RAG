"""
GitHub GraphQL query templates and utilities.
Which handles authentication, query construction, and response parsing.
"""

from typing import Optional
from datetime import datetime


# GraphQL query to fetch repository events like:commits, PRs, issues, and releases
REPOSITORY_EVENTS_QUERY = """
query GetRepositoryEvents($owner: String!, $name: String!, $since: GitTimestamp, $first: Int = 50) {
  repository(owner: $owner, name: $name) {
    name
    owner {
      login
    }
    url
    
    # Recent commits
    defaultBranchRef {
      target {
        ... on Commit {
          history(first: $first, since: $since) {
            edges {
              node {
                oid
                message
                committedDate
                author {
                  name
                  email
                }
              }
            }
          }
        }
      }
    }
    
    # Recent pull requests
    pullRequests(first: $first, orderBy: {field: UPDATED_AT, direction: DESC}) {
      edges {
        node {
          number
          title
          state
          createdAt
          updatedAt
          merged
          author {
            login
          }
        }
      }
    }
    
    # Recent issues
    issues(first: $first, orderBy: {field: UPDATED_AT, direction: DESC}) {
      edges {
        node {
          number
          title
          state
          createdAt
          updatedAt
          author {
            login
          }
        }
      }
    }
    
    # Recent releases
    releases(first: 10, orderBy: {field: CREATED_AT, direction: DESC}) {
      edges {
        node {
          name
          tagName
          createdAt
          author {
            login
          }
        }
      }
    }
  }
  
  # Rate limit information
  rateLimit {
    limit
    cost
    remaining
    resetAt
  }
}
"""


# Simpler query for rate limit checking
RATE_LIMIT_QUERY = """
query {
  rateLimit {
    limit
    cost
    remaining
    resetAt
  }
}
"""


def parse_repository_url(repo_url: str) -> tuple[str, str]:
    """
    Parse GitHub repository URL to extract owner and name.
    
    Args:
        repo_url: GitHub repository URL (e.g., "https://github.com/owner/repo")
    
    Returns:
        Tuple of (owner, name)
    
    Raises:
        ValueError: If URL format is invalid
    
    Examples:
        >>> parse_repository_url("https://github.com/pathwaycom/pathway")
        ('pathwaycom', 'pathway')
        >>> parse_repository_url("pathwaycom/pathway")
        ('pathwaycom', 'pathway')
    """
    # Handle both full URLs and "owner/repo" format
    repo_url = repo_url.strip()
    repo_url = repo_url.rstrip("/")
    
    # If it's a full URL, extract the path
    if repo_url.startswith("http"):
        parts = repo_url.split("github.com/")
        if len(parts) != 2:
            raise ValueError(f"Invalid GitHub URL format: {repo_url}")
        path = parts[1]
    else:
        path = repo_url
    
    # Split into owner and name
    parts = path.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid repository format: {repo_url}. Expected 'owner/repo'")
    
    owner, name = parts
    if not owner or not name:
        raise ValueError(f"Owner and repository name cannot be empty: {repo_url}")
    
    return owner, name


def format_datetime_for_github(dt: Optional[datetime]) -> Optional[str]:
    """
    Format datetime for GitHub GraphQL API (ISO 8601 format).
    
    Args:
        dt: Datetime to format
    
    Returns:
        ISO 8601 formatted string or None
    
    Example:
        >>> from datetime import datetime
        >>> dt = datetime(2026, 1, 4, 12, 0, 0)
        >>> format_datetime_for_github(dt)
        '2026-01-04T12:00:00Z'
    """
    if dt is None:
        return None
    
    # GitHub expects ISO 8601 format with 'Z' suffix
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_query_variables(
    owner: str,
    name: str,
    since: Optional[datetime] = None,
    first: int = 50
) -> dict:
    """
    Build variables for GitHub GraphQL query.
    
    Args:
        owner: Repository owner
        name: Repository name
        since: Fetch events since this timestamp
        first: Number of items to fetch per category
    
    Returns:
        Dictionary of query variables
    """
    variables = {
        "owner": owner,
        "name": name,
        "first": first,
    }
    
    if since is not None:
        variables["since"] = format_datetime_for_github(since)
    
    return variables