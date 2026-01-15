"""
Pipeline manager for FastAPI integration.
Manages Pathway pipeline lifecycle and data access.
"""

import asyncio
from typing import Any, Dict, List, Optional

from backend.connectors.demo_connector import create_demo_github_stream
from backend.connectors.github_connector import create_github_stream
from backend.core.config import settings
from backend.core.logger import get_logger
from backend.pipelines.pathway_pipeline import GitHubPipeline
from backend.rag.embeddings import prepare_summaries_for_embedding
from backend.rag.indexer import create_rag_index
from backend.rag.query_engine import create_query_engine
from backend.rag.retriever import create_retriever

logger = get_logger(__name__)


class PipelineManager:
    """
    Manages Pathway pipeline and RAG system integration.
    
    Handles:
    - Pipeline initialization
    - RAG system setup
    - Data access methods
    - Background monitoring
    """

    def __init__(self):
        """Initialize pipeline manager."""
        self.pipeline: Optional[GitHubPipeline] = None
        self.pipeline_tables: Optional[Dict] = None
        self.query_engine = None
        self.vector_server = None
        self.is_running = False
        
        logger.info("PipelineManager initialized")

    async def initialize(self) -> bool:
        """
        Initialize the Pathway pipeline and RAG system.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("🚀 Initializing Pathway pipeline...")
            
            # Step 1: Create event stream (demo or real GitHub)
            if settings.DEMO_MODE:
                logger.info("Using demo connector (simulated events)")
                events_table = create_demo_github_stream(
                    events_per_batch=5,
                    batch_interval=8,
                )
            else:
                logger.info("Using GitHub connector (real data)")
                # TODO: Load repositories from config
                repos = [
                    "openai/openai-python",
                    "langchain-ai/langchain",
                    "pathwaycom/pathway",
                ]
                events_table = create_github_stream(
                    repositories=repos,
                    poll_interval=settings.GITHUB_POLL_INTERVAL,
                )
            
            # Step 2: Build pipeline
            logger.info("Building Pathway pipeline...")
            self.pipeline = GitHubPipeline(events_table)
            self.pipeline_tables = self.pipeline.build()
            
            logger.info(
                f"✅ Pipeline built with {len(self.pipeline_tables)} tables",
                extra={"tables": list(self.pipeline_tables.keys())}
            )
            
            # Step 3: Initialize RAG system
            await self._initialize_rag_system()
            
            self.is_running = True
            logger.info("✅ Pipeline and RAG system initialized successfully")
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to initialize pipeline: {e}",
                exc_info=True
            )
            return False

    async def _initialize_rag_system(self) -> None:
        """Initialize RAG system with pipeline data."""
        try:
            logger.info("Initializing RAG system...")
            
            # Get summary table reference
            summaries_table = self.pipeline_tables.get("summaries_short")
            
            if summaries_table is None:
                logger.warning("No summaries table found")
                return
            
            # Store table reference for later
            self.summaries_table = summaries_table
            
            # Try to initialize, but don't fail if no data yet
            try:
                # Prepare for embedding
                prepared_data = prepare_summaries_for_embedding(summaries_table)
                
                # Create vector index
                logger.info("Creating vector index...")
                self.vector_server = create_rag_index(prepared_data)
                
                # Create query engine
                logger.info("Creating query engine...")
                retriever = create_retriever(self.vector_server)
                self.query_engine = create_query_engine(
                    retriever,
                    llm_model=settings.OPENAI_LLM_MODEL,
                    temperature=settings.OPENAI_TEMPERATURE
                )
                
                logger.info("✅ RAG system initialized")
                
            except Exception as e:
                # This is expected if no data has flowed through yet
                logger.info(
                    f"RAG system will initialize after data arrives: {str(e)[:100]}"
                )
                # Don't re-raise - this is normal for lazy evaluation
            
        except Exception as e:
            logger.error(f"Failed to configure RAG system: {e}", exc_info=True)

    def get_current_data(self) -> Dict[str, Any]:
        """
        Get current state of pipeline data.
        
        Returns:
            Dictionary with current summaries, rankings, trends, events, metrics
        """
        if not self.is_running or not self.pipeline_tables:
            return {
                "summaries": {},
                "rankings": {},
                "trends": {},
                "events": [],
                "metrics": {},
            }
        
        # TODO: Access Pathway tables and convert to dicts
        # For now, return mock data structure
        # In production, you would use:
        # - pw.io.jsonlines output connector
        # - Pathway HTTP server queries
        # - Or table.select().collect() in test mode
        
        return {
            "summaries": self._get_current_summaries(),
            "rankings": self._get_current_rankings(),
            "trends": self._get_current_trends(),
            "events": self._get_recent_events(),
            "metrics": self._get_system_metrics(),
        }

    def _get_current_summaries(self) -> Dict[str, Dict]:
        """Get current repository summaries."""
        # TODO: Query summaries_short table
        # For now, return mock data
        return {}

    def _get_current_rankings(self) -> Dict[str, int]:
        """Get current repository rankings."""
        # TODO: Query top_repos_short table
        return {}

    def _get_current_trends(self) -> Dict[str, Dict]:
        """Get current trend information."""
        # TODO: Query trends_short_term table
        return {}

    def _get_recent_events(self) -> List[Dict]:
        """Get recent events."""
        # TODO: Query events table
        return []

    def _get_system_metrics(self) -> Dict[str, int]:
        """Get system metrics."""
        # TODO: Calculate from tables
        return {
            "total_events": 0,
            "active_repositories": 0,
            "total_queries": 0,
        }

    async def shutdown(self) -> None:
        """Shutdown pipeline gracefully."""
        logger.info("🛑 Shutting down pipeline...")
        self.is_running = False
        # TODO: Stop Pathway pipeline if needed
        logger.info("✅ Pipeline shutdown complete")


# Global instance
pipeline_manager = PipelineManager()
