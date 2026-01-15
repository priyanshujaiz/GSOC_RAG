"""
Prompt templates for RAG system.
Ensures LLM answers are grounded in retrieved repository data.
"""

from typing import List, Dict, Any
from backend.core.logger import get_logger

logger = get_logger(__name__)


# System prompt that defines the AI's role and behavior
SYSTEM_PROMPT = """You are an expert analyst specializing in GitHub repository activity and open-source project trends.

Your role is to provide accurate, data-driven insights about repository activity based ONLY on the information provided to you.

Guidelines:
1. Base your answers ONLY on the provided context
2. Include specific metrics and numbers when available
3. Cite repository names when mentioning specific data
4. Use the trend indicators (🔥 HOT, 📈 ACTIVE, 📊 MODERATE) when relevant
5. If the context doesn't contain enough information, say so clearly
6. Be concise but informative
7. Compare repositories when asked
8. Highlight recent changes and momentum

DO NOT:
- Make up information not in the context
- Use knowledge from your training data
- Speculate about future trends
- Provide information about repositories not in the context"""


def build_rag_prompt(
    user_question: str,
    retrieved_summaries: List[Dict[str, Any]],
    include_metadata: bool = True
) -> str:
    """
    Build complete prompt for LLM with user question and retrieved context.
    
    Args:
        user_question: The user's natural language question
        retrieved_summaries: List of retrieved repository summaries with metadata
        include_metadata: Whether to include detailed metadata (default: True)
    
    Returns:
        Complete formatted prompt ready for LLM
    
    Example:
        >>> summaries = [
        ...     {"text": "repo is HOT...", "metadata": {"repo_full_name": "openai/gpt-4"}}
        ... ]
        >>> prompt = build_rag_prompt("Which repos are active?", summaries)
    """
    logger.debug(f"Building RAG prompt for question: '{user_question}'")
    logger.debug(f"Number of retrieved summaries: {len(retrieved_summaries)}")
    
    # Build context section from retrieved summaries
    context_sections = []
    
    for idx, summary in enumerate(retrieved_summaries, 1):
        text = summary.get("text", "")
        metadata = summary.get("metadata", {})
        
        # Extract key metadata
        repo_name = metadata.get("repo_full_name", "Unknown")
        activity_score = metadata.get("activity_score", 0)
        trend_status = metadata.get("trend_status", "")
        window_period = metadata.get("window_period", "")
        
        # Format context entry
        context_entry = f"Repository {idx}: {repo_name}\n{text}"
        
        if include_metadata:
            context_entry += f"\n[Score: {activity_score}, Window: {window_period}]"
        
        context_sections.append(context_entry)
    
    # Join all context sections
    full_context = "\n\n".join(context_sections)
    
    # Build complete prompt
    prompt = f"""User Question: {user_question}

Context (Recent Repository Activity):
{full_context}

Please answer the user's question based on the context provided above. Include specific repository names, metrics, and trends in your answer."""
    
    logger.info("RAG prompt built successfully")
    logger.debug(f"Prompt length: {len(prompt)} characters")
    
    return prompt


def build_simple_prompt(user_question: str, context: str) -> str:
    """
    Build simple prompt with just question and context.
    
    Useful for direct queries without structured metadata.
    
    Args:
        user_question: User's question
        context: Raw context text
    
    Returns:
        Simple formatted prompt
    """
    prompt = f"""Question: {user_question}

Context:
{context}

Answer based only on the context provided:"""
    
    return prompt


def build_comparison_prompt(
    user_question: str,
    retrieved_summaries: List[Dict[str, Any]]
) -> str:
    """
    Build prompt optimized for comparing repositories.
    
    Args:
        user_question: Comparison question (e.g., "Compare repo A vs repo B")
        retrieved_summaries: Retrieved repository summaries
    
    Returns:
        Comparison-focused prompt
    """
    logger.debug("Building comparison prompt")
    
    # Extract repository data for comparison
    repo_data = []
    for summary in retrieved_summaries:
        text = summary.get("text", "")
        metadata = summary.get("metadata", {})
        
        repo_data.append({
            "name": metadata.get("repo_full_name", "Unknown"),
            "summary": text,
            "score": metadata.get("activity_score", 0),
            "trend": metadata.get("trend_status", ""),
        })
    
    # Build comparison table
    comparison_text = "Repository Comparison:\n\n"
    for data in repo_data:
        comparison_text += f"• {data['name']}\n"
        comparison_text += f"  Status: {data['trend']}\n"
        comparison_text += f"  Score: {data['score']}\n"
        comparison_text += f"  Details: {data['summary']}\n\n"
    
    prompt = f"""User Question: {user_question}

{comparison_text}

Please compare these repositories based on the data provided. Highlight key differences in activity, trends, and momentum."""
    
    logger.info("Comparison prompt built")
    return prompt


def build_trending_prompt(retrieved_summaries: List[Dict[str, Any]]) -> str:
    """
    Build prompt optimized for trending/hot repository queries.
    
    Args:
        retrieved_summaries: Retrieved summaries (should be sorted by score)
    
    Returns:
        Trending-focused prompt
    """
    # Sort by activity score (descending)
    sorted_summaries = sorted(
        retrieved_summaries,
        key=lambda x: x.get("metadata", {}).get("activity_score", 0),
        reverse=True
    )
    
    trending_text = "Most Active Repositories (by activity score):\n\n"
    
    for idx, summary in enumerate(sorted_summaries, 1):
        metadata = summary.get("metadata", {})
        repo = metadata.get("repo_full_name", "Unknown")
        score = metadata.get("activity_score", 0)
        trend = metadata.get("trend_status", "")
        text = summary.get("text", "")
        
        trending_text += f"{idx}. {repo} ({trend}, Score: {score})\n"
        trending_text += f"   {text}\n\n"
    
    prompt = f"""{trending_text}

Summarize the most active and trending repositories from this list. Explain what makes them stand out."""
    
    return prompt


def extract_key_metrics(summary_text: str) -> Dict[str, Any]:
    """
    Extract key metrics from a summary text.
    
    Useful for structured data extraction.
    
    Args:
        summary_text: Repository summary text
    
    Returns:
        Dictionary with extracted metrics
    """
    # Simple extraction (could be enhanced with regex)
    metrics = {
        "has_commits": "commit" in summary_text.lower(),
        "has_prs": "pr" in summary_text.lower(),
        "has_issues": "issue" in summary_text.lower(),
        "has_releases": "release" in summary_text.lower(),
        "is_hot": "🔥 HOT" in summary_text,
        "is_active": "📈 ACTIVE" in summary_text,
        "is_accelerating": "ACCELERATING" in summary_text,
    }
    
    return metrics


# Suggested follow-up questions based on context
SUGGESTED_QUESTIONS = [
    "Which repositories are most active right now?",
    "Show me trending Python repositories",
    "What repos have the most pull requests?",
    "Which projects are accelerating in activity?",
    "Compare the top 3 most active repositories",
    "What's happening with [specific repo name]?",
    "Show me repositories with recent releases",
    "Which repos have the most commits today?",
]


def get_suggested_questions(
    retrieved_summaries: List[Dict[str, Any]],
    max_suggestions: int = 3
) -> List[str]:
    """
    Generate contextual suggested questions based on retrieved data.
    
    Args:
        retrieved_summaries: Retrieved repository summaries
        max_suggestions: Maximum number of suggestions to return
    
    Returns:
        List of suggested follow-up questions
    """
    suggestions = []
    
    # Get repo names from summaries
    repo_names = [
        s.get("metadata", {}).get("repo_full_name", "")
        for s in retrieved_summaries
        if s.get("metadata", {}).get("repo_full_name")
    ]
    
    # Add specific repo questions
    if repo_names:
        suggestions.append(f"Tell me more about {repo_names[0]}")
    
    if len(repo_names) >= 2:
        suggestions.append(f"Compare {repo_names[0]} and {repo_names[1]}")
    
    # Add general questions
    suggestions.extend([
        "What are the current trends?",
        "Show me repositories with high momentum",
    ])
    
    return suggestions[:max_suggestions]