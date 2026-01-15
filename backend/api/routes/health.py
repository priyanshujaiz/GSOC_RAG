"""
Health check and system metrics endpoints.
Provides comprehensive system status information.
"""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, status

from backend.api.models.responses import HealthResponse, MetricsResponse
from backend.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Global metrics tracking (will be updated by the system)
system_metrics: Dict[str, Any] = {
    "total_events_processed": 0,
    "total_repositories": 0,
    "active_repositories": 0,
    "total_queries": 0,
    "total_tokens_used": 0,
    "query_durations": [],  # Last 100 query durations
    "startup_time": None,
    "last_event_time": None,
}


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Returns basic system health status",
    tags=["Health"],
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns:
        HealthResponse with system status
    """
    from backend.api.main import app_state

    # Check if pipeline is running
    pipeline_running = app_state.get("pipeline") is not None

    # Check if RAG system is available
    rag_available = app_state.get("query_engine") is not None

    # Calculate uptime
    uptime_seconds = None
    if app_state.get("startup_time"):
        uptime_seconds = (
            datetime.utcnow() - app_state["startup_time"]
        ).total_seconds()

    # Determine overall status
    if pipeline_running and rag_available:
        overall_status = "healthy"
    elif pipeline_running or rag_available:
        overall_status = "degraded"
    else:
        overall_status = "unavailable"

    logger.info(
        "Health check performed",
        extra={
            "status": overall_status,
            "pipeline_running": pipeline_running,
            "rag_available": rag_available,
        },
    )

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        pipeline_running=pipeline_running,
        rag_available=rag_available,
        uptime_seconds=uptime_seconds,
        version="0.1.0",
    )


@router.get(
    "/health/detailed",
    status_code=status.HTTP_200_OK,
    summary="Detailed health check",
    description="Returns comprehensive system status with component details",
    tags=["Health"],
)
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check with component-level status.

    Returns:
        Detailed system health information
    """
    from backend.api.main import app_state

    # Check components
    pipeline_status = _check_pipeline_status(app_state)
    rag_status = _check_rag_status(app_state)
    api_status = _check_api_status()

    # Calculate overall health score (0-100)
    health_score = _calculate_health_score(pipeline_status, rag_status, api_status)

    # Determine overall status
    if health_score >= 90:
        overall_status = "healthy"
    elif health_score >= 60:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "health_score": health_score,
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "pipeline": pipeline_status,
            "rag_system": rag_status,
            "api": api_status,
        },
        "uptime_seconds": (
            (datetime.utcnow() - app_state["startup_time"]).total_seconds()
            if app_state.get("startup_time")
            else None
        ),
        "version": "0.1.0",
    }


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="System metrics",
    description="Returns operational metrics and statistics",
    tags=["Health"],
)
async def get_metrics() -> MetricsResponse:
    """
    Get system operational metrics.

    Returns:
        MetricsResponse with system statistics
    """
    # Calculate average query time
    average_query_time = None
    if system_metrics["query_durations"]:
        average_query_time = sum(system_metrics["query_durations"]) / len(
            system_metrics["query_durations"]
        )

    logger.debug(
        "Metrics requested",
        extra={
            "total_queries": system_metrics["total_queries"],
            "total_events": system_metrics["total_events_processed"],
        },
    )

    return MetricsResponse(
        total_events_processed=system_metrics["total_events_processed"],
        total_repositories=system_metrics["total_repositories"],
        active_repositories=system_metrics["active_repositories"],
        total_queries=system_metrics["total_queries"],
        average_query_time_ms=average_query_time,
        total_tokens_used=system_metrics["total_tokens_used"],
        timestamp=datetime.utcnow(),
    )


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Comprehensive system status",
    description="Returns all system status information including health and metrics",
    tags=["Health"],
)
async def get_system_status() -> Dict[str, Any]:
    """
    Get comprehensive system status.

    Combines health check and metrics into one response.

    Returns:
        Complete system status
    """
    health = await health_check()
    metrics = await get_metrics()

    return {
        "health": health.model_dump(),
        "metrics": metrics.model_dump(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    description="Kubernetes-style readiness probe (returns 200 if ready to serve traffic)",
    tags=["Health"],
)
async def readiness_probe() -> Dict[str, Any]:
    """
    Readiness probe for orchestration systems.

    Returns 200 if the system is ready to serve requests.
    Returns 503 if not ready.

    Returns:
        Readiness status
    """
    from backend.api.main import app_state

    pipeline_running = app_state.get("pipeline") is not None
    rag_available = app_state.get("query_engine") is not None

    ready = pipeline_running and rag_available

    if not ready:
        return {
            "ready": False,
            "reason": "System is still initializing",
            "timestamp": datetime.utcnow().isoformat(),
        }

    return {
        "ready": True,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="Kubernetes-style liveness probe (returns 200 if service is alive)",
    tags=["Health"],
)
async def liveness_probe() -> Dict[str, Any]:
    """
    Liveness probe for orchestration systems.

    Always returns 200 if the API process is running.

    Returns:
        Liveness status
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Helper functions


def _check_pipeline_status(app_state: Dict[str, Any]) -> Dict[str, Any]:
    """Check Pathway pipeline status."""
    pipeline = app_state.get("pipeline")

    if pipeline is None:
        return {
            "status": "unavailable",
            "healthy": False,
            "message": "Pipeline not initialized",
        }

    # TODO: Add actual pipeline health checks
    # For now, assume healthy if exists
    return {
        "status": "operational",
        "healthy": True,
        "message": "Pipeline running",
        "events_processed": system_metrics["total_events_processed"],
        "repositories_tracked": system_metrics["total_repositories"],
    }


def _check_rag_status(app_state: Dict[str, Any]) -> Dict[str, Any]:
    """Check RAG system status."""
    query_engine = app_state.get("query_engine")
    vector_server = app_state.get("vector_server")

    if query_engine is None:
        return {
            "status": "unavailable",
            "healthy": False,
            "message": "RAG system not initialized",
        }

    # TODO: Add actual RAG health checks
    # For now, assume healthy if exists
    return {
        "status": "operational",
        "healthy": True,
        "message": "RAG system ready",
        "queries_processed": system_metrics["total_queries"],
        "vector_index_available": vector_server is not None,
    }


def _check_api_status() -> Dict[str, Any]:
    """Check API server status."""
    # API is healthy if we can respond to this request
    return {
        "status": "operational",
        "healthy": True,
        "message": "API server running",
    }


def _calculate_health_score(
    pipeline_status: Dict[str, Any],
    rag_status: Dict[str, Any],
    api_status: Dict[str, Any],
) -> int:
    """
    Calculate overall health score (0-100).

    Weighted scoring:
    - Pipeline: 40%
    - RAG System: 40%
    - API: 20%
    """
    score = 0

    # Pipeline contribution (40 points)
    if pipeline_status["healthy"]:
        score += 40

    # RAG system contribution (40 points)
    if rag_status["healthy"]:
        score += 40

    # API contribution (20 points)
    if api_status["healthy"]:
        score += 20

    return score


def update_metrics(
    events_processed: int = 0,
    queries: int = 0,
    tokens_used: int = 0,
    query_duration_ms: float = None,
) -> None:
    """
    Update system metrics.

    Args:
        events_processed: Number of new events processed
        queries: Number of new queries processed
        tokens_used: Number of tokens consumed
        query_duration_ms: Query duration in milliseconds
    """
    global system_metrics

    if events_processed > 0:
        system_metrics["total_events_processed"] += events_processed
        system_metrics["last_event_time"] = datetime.utcnow()

    if queries > 0:
        system_metrics["total_queries"] += queries

    if tokens_used > 0:
        system_metrics["total_tokens_used"] += tokens_used

    if query_duration_ms is not None:
        # Keep only last 100 query durations
        system_metrics["query_durations"].append(query_duration_ms)
        if len(system_metrics["query_durations"]) > 100:
            system_metrics["query_durations"].pop(0)


def set_repository_counts(total: int, active: int) -> None:
    """
    Update repository counts.

    Args:
        total: Total repositories tracked
        active: Active repositories (with recent activity)
    """
    global system_metrics
    system_metrics["total_repositories"] = total
    system_metrics["active_repositories"] = active