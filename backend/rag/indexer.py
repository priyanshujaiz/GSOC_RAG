"""
Vector indexing for RAG system using Pathway's LLM xPack.
Implements incremental vector store that auto-updates on data changes.
"""

import pathway as pw
from pathway.xpacks.llm import embedders, vector_store
from backend.core.logger import get_logger
from backend.rag.embeddings import create_embedder, prepare_summaries_for_embedding

logger = get_logger(__name__)


class RAGVectorIndexer:
    """
    Manages incremental vector indexing of repository summaries.
    
    Features:
    - Auto-updating vector index
    - Incremental embedding (only changed summaries)
    - In-memory vector store (no external DB needed)
    - Ready for semantic search
    """
    
    def __init__(self, embedder: embedders.OpenAIEmbedder):
        """
        Initialize vector indexer.
        
        Args:
            embedder: OpenAI embedder instance
        """
        self.embedder = embedder
        self.vector_server = None
        logger.info("RAGVectorIndexer initialized")
    
    def build_vector_index(self, summaries_table: pw.Table) -> vector_store.VectorStoreServer:
        """
        Build auto-updating vector index from summaries.
        
        This is the CORE of the RAG system:
        1. Takes summary table from pipeline
        2. Prepares for embedding (text + metadata)
        3. Creates vector store server
        4. Auto-updates when summaries change!
        
        Args:
            summaries_table: Table with repository summaries
        
        Returns:
            VectorStoreServer instance for querying
        """
        logger.info("Building vector index from summaries")
        
        # Step 1: Prepare data for embedding
        prepared_data = prepare_summaries_for_embedding(summaries_table)
        
        # Step 2: Create vector store server
        # This automatically:
        # - Embeds the 'text' column
        # - Stores vectors with metadata
        # - Updates incrementally when data changes
        self.vector_server = vector_store.VectorStoreServer(
            prepared_data,
            embedder=self.embedder,
            parser=None,  # No parsing needed, we have clean text
        )
        
        logger.info("Vector index built successfully")
        logger.debug(f"OpenAI embedder initialized")
        
        return self.vector_server
    
    def get_index(self) -> vector_store.VectorStoreServer:
        """
        Get the vector index instance.
        
        Returns:
            VectorStoreServer instance
        
        Raises:
            RuntimeError: If index not built yet
        """
        if self.vector_server is None:
            raise RuntimeError("Vector index not built. Call build_vector_index() first.")
        
        return self.vector_server


def create_rag_index(
    summaries_table: pw.Table,
    embedding_model: str = "text-embedding-3-small"
) -> vector_store.VectorStoreServer:
    """
    Factory function to create RAG vector index.
    
    This is the main entry point for Phase 3 integration.
    
    Args:
        summaries_table: Table from pipeline with summaries
        embedding_model: OpenAI model to use for embeddings
    
    Returns:
        VectorStoreServer ready for semantic search
    
    Example:
        >>> # In your pipeline:
        >>> summaries = generate_repository_summaries(trends)
        >>> vector_index = create_rag_index(summaries)
        >>> # Now ready for queries!
    """
    logger.info(f"Creating RAG index with model: {embedding_model}")
    
    # Create embedder
    embedder = create_embedder(model=embedding_model)
    
    # Build index
    indexer = RAGVectorIndexer(embedder)
    vector_server = indexer.build_vector_index(summaries_table)
    
    logger.info("RAG index created successfully")
    return vector_server