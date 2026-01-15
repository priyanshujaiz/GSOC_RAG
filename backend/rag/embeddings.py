"""
OpenAI embedding integration for Pathway RAG system.
Handles text-to-vector conversion for repository summaries.
"""

from typing import Optional
import pathway as pw
from pathway.xpacks.llm import embedders
from backend.core.config import Settings
from backend.core.logger import get_logger

logger = get_logger(__name__)
settings = Settings()

class EmbeddingService:
    """
    Service for embedding text using OpenAI's embedding models.
    
    Uses text-embedding-3-small:
    - 1536 dimensions
    - Fast and cost-effective
    - Good quality for RAG
    """
    
    def __init__(self, model: str = "text-embedding-3-small"):
        """
        Initialize embedding service.
        
        Args:
            model: OpenAI embedding model to use
        """
        self.model = model
        self.embedder = None
        logger.info(f"EmbeddingService initialized with model: {model}")
    
    def create_embedder(self) -> embedders.OpenAIEmbedder:
        """
        Create OpenAI embedder instance.
        
        Returns:
            Configured OpenAI embedder
        """
        if self.embedder is None:
            logger.debug("Creating OpenAI embedder")
            
            self.embedder = embedders.OpenAIEmbedder(
                api_key=settings.OPENAI_API_KEY,
                model=self.model,
                # retry_strategy=embedders.ExponentialBackoffRetryStrategy(
                #     max_retries=3
                # ),
                # cache_strategy=embedders.DiskCacheStrategy(
                #     cache_folder="./data/embedding_cache"
                # )
            )
            
            logger.info("OpenAI embedder created successfully")
        
        return self.embedder


def create_embedder(model: str = "text-embedding-3-small") -> embedders.OpenAIEmbedder:
    """
    Factory function to create embedding service.
    
    Args:
        model: OpenAI embedding model name
    
    Returns:
        OpenAI embedder instance
    
    Example:
        >>> embedder = create_embedder()
        >>> # Use with Pathway vector store
    """
    service = EmbeddingService(model=model)
    return service.create_embedder()


def prepare_summaries_for_embedding(summaries_table: pw.Table) -> pw.Table:
    """
    Prepare summary table for embedding by selecting required columns.
    
    Args:
        summaries_table: Table with repository summaries
    
    Returns:
        Table ready for vector indexing with:
        - text: The content to embed (summary)
        - metadata: Additional context (repo, score, trend)
    
    Schema:
        - text: str (the summary text)
        - metadata: dict (repo_full_name, activity_score, trend_status)
    """
    logger.debug("Preparing summaries for embedding")
    
    # Select and rename columns for Pathway vector store
    prepared = summaries_table.select(
        # Main text to embed
        data=pw.this.summary,
        
        # Metadata for retrieval context
        _metadata=pw.apply(
            lambda repo, score, trend, window: {
                "repo_full_name": repo,
                "activity_score": score,
                "trend_status": trend,
                "window_period": window,
            },
            pw.this.repo_full_name,
            pw.this.activity_score,
            pw.this.trend_status,
            pw.this.window_period,
        )
    )
    
    logger.info("Summaries prepared for embedding")
    return prepared