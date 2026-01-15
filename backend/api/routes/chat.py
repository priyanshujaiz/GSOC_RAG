"""
RAG chat endpoints.
Provides natural language question-answering over repository data.
"""

import time
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status

from backend.api.models.requests import BatchChatRequest, ChatRequest
from backend.api.models.responses import (
    BatchChatResponse,
    ChatResponse,
    SourceInfo,
)
from backend.api.routes.health import update_metrics
from backend.core.logger import get_logger
from backend.rag.query_engine import RAGQueryEngine

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask questions about repositories",
    description="Natural language question-answering using RAG over live GitHub data",
    tags=["Chat"],
)
async def chat_query(request: ChatRequest) -> ChatResponse:
    """
    Ask natural language questions about repository activity.

    Uses Retrieval-Augmented Generation (RAG) to provide grounded,
    evidence-based answers about repository metrics, trends, and activity.

    The system:
    1. Searches for relevant repository summaries
    2. Constructs context from recent data
    3. Generates an answer using GPT-4o-mini
    4. Includes citations and sources

    Example questions:
    - "Which repositories are most active right now?"
    - "What Python repos have the most commits today?"
    - "Which repos are trending in the last hour?"
    - "Compare openai/openai-python and langchain-ai/langchain"

    Args:
        request: ChatRequest with query and optional top_k

    Returns:
        ChatResponse with answer, sources, and metadata
    """
    query = request.query
    top_k = request.top_k

    logger.info(
        "Chat query received",
        extra={
            "query": query,
            "query_length": len(query),
            "top_k": top_k,
        },
    )

    # Record start time for metrics
    start_time = time.time()

    try:
        # Get query engine from app state
        query_engine = _get_query_engine()

        if query_engine is None:
            logger.error("Query engine not available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG system is not ready. Please try again in a moment.",
            )

        # Execute RAG query
        logger.debug(f"Executing RAG query with top_k={top_k}")
        result = await query_engine.query(
            user_question=query,
            top_k=top_k,
            include_sources=True,
        )

        # Calculate query duration
        duration_ms = (time.time() - start_time) * 1000

        # Extract sources and format them
        sources = _format_sources(result.get("sources", []))

        # Build response
        response = ChatResponse(
            answer=result["answer"],
            query=query,
            model=result.get("model", "gpt-4o-mini"),
            tokens_used=result.get("tokens_used", 0),
            sources=sources,
            num_sources=len(sources),
            suggested_questions=result.get("suggested_questions", []),
            timestamp=datetime.utcnow(),
        )

        # Update metrics
        update_metrics(
            queries=1,
            tokens_used=result.get("tokens_used", 0),
            query_duration_ms=duration_ms,
        )

        logger.info(
            "Chat query completed",
            extra={
                "query": query,
                "duration_ms": round(duration_ms, 2),
                "tokens_used": result.get("tokens_used", 0),
                "num_sources": len(sources),
                "answer_length": len(result["answer"]),
            },
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Chat query failed",
            extra={
                "query": query,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {str(e)}",
        )


@router.post(
    "/chat/batch",
    response_model=BatchChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Process multiple questions in batch",
    description="Execute multiple RAG queries in parallel for efficiency",
    tags=["Chat"],
)
async def batch_chat_query(request: BatchChatRequest) -> BatchChatResponse:
    """
    Process multiple questions in a single request.

    Executes queries in parallel for efficiency. Useful for:
    - Dashboard widgets with multiple data points
    - Automated monitoring queries
    - Bulk analysis

    Args:
        request: BatchChatRequest with list of queries

    Returns:
        BatchChatResponse with results for all queries
    """
    queries = request.queries
    top_k = request.top_k

    logger.info(
        "Batch chat query received",
        extra={
            "num_queries": len(queries),
            "top_k": top_k,
        },
    )

    start_time = time.time()

    try:
        # Get query engine
        query_engine = _get_query_engine()

        if query_engine is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG system is not ready",
            )

        # Execute batch query
        results = await query_engine.batch_query(queries, top_k=top_k)

        # Format results
        formatted_results = []
        total_tokens = 0

        for result in results:
            if "error" in result:
                # Skip failed queries (already logged by engine)
                continue

            sources = _format_sources(result.get("sources", []))

            formatted_results.append(
                ChatResponse(
                    answer=result["answer"],
                    query=result["query"],
                    model=result.get("model", "gpt-4o-mini"),
                    tokens_used=result.get("tokens_used", 0),
                    sources=sources,
                    num_sources=len(sources),
                    suggested_questions=result.get("suggested_questions", []),
                    timestamp=datetime.utcnow(),
                )
            )

            total_tokens += result.get("tokens_used", 0)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Update metrics
        update_metrics(
            queries=len(formatted_results),
            tokens_used=total_tokens,
            query_duration_ms=duration_ms / len(formatted_results)
            if formatted_results
            else 0,
        )

        logger.info(
            "Batch chat query completed",
            extra={
                "num_queries": len(queries),
                "successful": len(formatted_results),
                "duration_ms": round(duration_ms, 2),
                "total_tokens": total_tokens,
            },
        )

        return BatchChatResponse(
            results=formatted_results,
            total_queries=len(formatted_results),
            total_tokens_used=total_tokens,
            timestamp=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Batch chat query failed",
            extra={
                "num_queries": len(queries),
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch query failed: {str(e)}",
        )


# Helper functions


def _get_query_engine() -> RAGQueryEngine | None:
    """
    Get query engine from application state.

    Returns:
        RAGQueryEngine instance or None if not initialized
    """
    from backend.api.main import app_state

    query_engine = app_state.get("query_engine")

    if query_engine is None:
        logger.warning("Query engine not found in app state")

    return query_engine


def _format_sources(sources: List[Dict[str, Any]]) -> List[SourceInfo]:
    """
    Format retrieval sources into SourceInfo models.

    Args:
        sources: Raw sources from query engine

    Returns:
        List of SourceInfo objects
    """
    formatted = []

    for source in sources:
        try:
            # Extract metadata
            metadata = source.get("metadata", {})

            formatted.append(
                SourceInfo(
                    repo_full_name=metadata.get("repo_full_name", "unknown"),
                    summary=source.get("text", ""),
                    activity_score=metadata.get("activity_score", 0.0),
                    trend_status=metadata.get("trend_status", "UNKNOWN"),
                    relevance_score=source.get("score", None),
                )
            )
        except Exception as e:
            logger.warning(
                "Failed to format source",
                extra={"error": str(e), "source": source},
            )
            continue

    return formatted


@router.get(
    "/chat/suggestions",
    status_code=status.HTTP_200_OK,
    summary="Get suggested questions",
    description="Returns example questions users can ask",
    tags=["Chat"],
)
async def get_suggested_questions() -> Dict[str, List[str]]:
    """
    Get suggested questions for users.

    Provides example queries organized by category to help users
    understand what questions they can ask.

    Returns:
        Dictionary of question categories and examples
    """
    return {
        "trending": [
            "Which repositories are most active right now?",
            "What's trending in the last hour?",
            "Show me the hottest repos today",
        ],
        "activity": [
            "Which repos have the most commits in the last 24 hours?",
            "What repositories are getting the most pull requests?",
            "Show me repos with recent releases",
        ],
        "comparison": [
            "Compare openai/openai-python and langchain-ai/langchain",
            "Which is more active: fastapi or django?",
            "Compare Python vs JavaScript repos",
        ],
        "specific": [
            "What's new in pathwaycom/pathway?",
            "Has microsoft/vscode been active lately?",
            "Tell me about recent activity in python repos",
        ],
        "momentum": [
            "Which repos are accelerating?",
            "Show me repos that slowed down today",
            "What repos are gaining momentum?",
        ],
    }


@router.get(
    "/chat/health",
    status_code=status.HTTP_200_OK,
    summary="RAG system health",
    description="Check if RAG system is ready to answer questions",
    tags=["Chat"],
)
async def chat_health() -> Dict[str, Any]:
    """
    Check RAG system health and readiness.

    Returns:
        Health status of chat/RAG system
    """
    from backend.api.main import app_state

    query_engine = app_state.get("query_engine")
    vector_server = app_state.get("vector_server")

    ready = query_engine is not None and vector_server is not None

    return {
        "ready": ready,
        "query_engine_available": query_engine is not None,
        "vector_index_available": vector_server is not None,
        "timestamp": datetime.utcnow().isoformat(),
    }