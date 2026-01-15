"""
FastAPI application entry point.
Live Open-Source Intelligence Platform - API Layer
"""
import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict
from backend.api.routes import health,repos, chat, websocket

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.utils.pipeline_manager import pipeline_manager
from backend.api.utils.change_detector import ChangeDetector
from backend.api.routes.websocket import broadcast_update

from backend.core.config import Settings
settings = Settings()
from backend.core.exceptions import (
    GitHubAPIError,
    PathwayError,
    RAGError,
    RateLimitError,
)
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Global state for pipeline and RAG system
app_state: Dict[str, Any] = {
    "pipeline": None,
    "query_engine": None,
    "vector_server": None,
    "startup_time": None,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("🚀 Starting FastAPI application")
    app_state["startup_time"] = datetime.utcnow()
    
    try:
        # Initialize pipeline
        logger.info("Initializing Pathway pipeline...")
        success = await pipeline_manager.initialize()
        
        if success:
            # Store in app state
            app_state["pipeline"] = pipeline_manager.pipeline
            app_state["pipeline_tables"] = pipeline_manager.pipeline_tables
            app_state["query_engine"] = pipeline_manager.query_engine
            app_state["vector_server"] = pipeline_manager.vector_server
            
            # Initialize change detector
            change_detector = ChangeDetector()
            app_state["change_detector"] = change_detector
            
            # Register WebSocket broadcast as callback
            async def broadcast_changes(messages):
                for message in messages:
                    await broadcast_update(message)
            
            change_detector.register_callback(broadcast_changes)
            
            # Start background monitoring task
            monitoring_task = asyncio.create_task(_monitor_pipeline_changes())
            app_state["monitoring_task"] = monitoring_task
            
            logger.info("✅ Application startup complete")
        else:
            logger.warning("⚠️ Pipeline initialization failed, running in degraded mode")
        
        yield
        
    finally:
        # Shutdown
        logger.info("🛑 Shutting down FastAPI application")
        
        # Cancel monitoring task
        if "monitoring_task" in app_state:
            app_state["monitoring_task"].cancel()
        
        # Shutdown pipeline
        await pipeline_manager.shutdown()
        
        logger.info("✅ Application shutdown complete")


async def _monitor_pipeline_changes():
    """
    Background task to monitor pipeline for changes.
    Runs continuously and broadcasts updates via WebSocket.
    """
    logger.info("📡 Starting pipeline monitoring task")
    
    change_detector = app_state.get("change_detector")
    
    if not change_detector:
        logger.error("Change detector not initialized")
        return
    
    try:
        while True:
            # Poll interval (check every 5 seconds)
            await asyncio.sleep(5)
            
            if not pipeline_manager.is_running:
                continue
            
            # Get current data from pipeline
            current_data = pipeline_manager.get_current_data()
            
            # Check for changes
            messages = await change_detector.check_for_changes(
                current_summaries=current_data["summaries"],
                current_rankings=current_data["rankings"],
                current_trends=current_data["trends"],
                current_events=current_data["events"],
                current_metrics=current_data["metrics"],
            )
            
            if messages:
                logger.info(
                    f"📢 Broadcasting {len(messages)} change(s)",
                    extra={"message_types": [m.get("type") for m in messages]}
                )
            
    except asyncio.CancelledError:
        logger.info("📡 Pipeline monitoring task cancelled")
    except Exception as e:
        logger.error(f"Error in monitoring task: {e}", exc_info=True)

# Initialize FastAPI app
app = FastAPI(
    title="Live Open-Source Intelligence Platform",
    description="Dynamic RAG System for Real-Time GitHub Activity Monitoring",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# Request ID Middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to each request."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Add to logger context
    logger.bind(request_id=request_id)
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and their duration."""
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request started",
        extra={
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else None,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log response
    logger.info(
        "Request completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    
    return response


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Log the error
    logger.error(
        "Unhandled exception",
        extra={
            "error": str(exc),
            "error_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
            "request_id": request_id,
        },
        exc_info=True,
    )
    
    # Return generic error response
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# Custom Exception Handlers
@app.exception_handler(GitHubAPIError)
async def github_api_error_handler(request: Request, exc: GitHubAPIError):
    """Handle GitHub API errors."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.warning(
        "GitHub API error",
        extra={
            "error": str(exc),
            "request_id": request_id,
        },
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "GitHub API error",
            "message": str(exc),
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(RateLimitError)
async def rate_limit_error_handler(request: Request, exc: RateLimitError):
    """Handle rate limit errors."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.warning(
        "Rate limit exceeded",
        extra={
            "error": str(exc),
            "request_id": request_id,
        },
    )
    
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "message": str(exc),
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(RAGError)
async def rag_error_handler(request: Request, exc: RAGError):
    """Handle RAG system errors."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        "RAG system error",
        extra={
            "error": str(exc),
            "request_id": request_id,
        },
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "RAG system error",
            "message": str(exc),
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(PathwayError)
async def pathway_error_handler(request: Request, exc: PathwayError):
    """Handle Pathway pipeline errors."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        "Pathway pipeline error",
        extra={
            "error": str(exc),
            "request_id": request_id,
        },
    )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "Pipeline error",
            "message": str(exc),
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "Live Open-Source Intelligence Platform",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/api/v1/health",
        "timestamp": datetime.utcnow().isoformat(),
    }


# Basic health check (will be enhanced in routes/health.py)
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


# TODO: Import and register routers
# from backend.api.routes import health, repos, chat, websocket
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(repos.router, prefix="/api/v1", tags=["Repositories"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])



if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
    )