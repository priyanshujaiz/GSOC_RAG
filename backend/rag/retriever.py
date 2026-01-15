"""
Semantic retrieval for RAG system.
Searches vector index to find relevant repository summaries for user queries.
"""

from typing import List, Dict, Any, Optional
import pathway as pw
from pathway.xpacks.llm import vector_store
from backend.core.logger import get_logger
from backend.rag.embeddings import create_embedder

logger = get_logger(__name__)


class SemanticRetriever:
    """
    Retrieves relevant repository summaries based on semantic similarity.
    
    Uses vector similarity search to find repos matching user queries.
    """
    
    def __init__(self, vector_server: vector_store.VectorStoreServer):
        """
        Initialize semantic retriever.
        
        Args:
            vector_server: VectorStoreServer instance with embedded summaries
        """
        self.vector_server = vector_server
        logger.info("SemanticRetriever initialized")
    
    def retrieve(
        self, 
        query: str, 
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve most relevant repository summaries for a query.
        
        This performs:
        1. Query embedding (convert question to vector)
        2. Similarity search (find closest vectors)
        3. Return top-K results with metadata
        
        Args:
            query: Natural language question (e.g., "Which Python repos are trending?")
            top_k: Number of results to return (default: 5)
            metadata_filter: Optional filters (e.g., {"window_period": "1h"})
        
        Returns:
            List of result dictionaries with:
            - text: The repository summary
            - metadata: Repo info (name, score, trend)
            - similarity_score: How relevant (0-1)
        
        Example:
            >>> retriever = SemanticRetriever(vector_server)
            >>> results = retriever.retrieve("Which repos are most active?", top_k=5)
            >>> for result in results:
            ...     print(f"{result['metadata']['repo_full_name']}: {result['similarity_score']}")
        """
        logger.info(f"Retrieving top-{top_k} results for query: '{query}'")
        
        try:
            # The VectorStoreServer handles the entire retrieval pipeline:
            # - Embeds the query automatically
            # - Performs similarity search
            # - Returns top-K results
            
            # Note: This is a simplified interface
            # In actual implementation, we'll need to query via the REST endpoint
            # that VectorStoreServer exposes when running with pw.run()
            
            logger.debug(f"Query length: {len(query)} characters")
            logger.debug(f"Metadata filter: {metadata_filter}")
            
            # For now, we'll return a placeholder that shows the structure
            # The actual query happens through the VectorStoreServer's HTTP endpoint
            # which we'll integrate in the query engine
            
            results = {
                "query": query,
                "top_k": top_k,
                "vector_server": self.vector_server,
                "metadata_filter": metadata_filter
            }
            
            logger.info(f"Retrieval prepared for {top_k} results")
            return results
            
        except Exception as e:
            logger.error(f"Retrieval failed: {e}", exc_info=True)
            raise


class RetrievalResult:
    """
    Structured result from semantic retrieval.
    
    Attributes:
        text: The retrieved document text (summary)
        metadata: Additional information about the document
        score: Similarity score (0-1, higher is more relevant)
    """
    
    def __init__(self, text: str, metadata: Dict[str, Any], score: float):
        """
        Initialize retrieval result.
        
        Args:
            text: Document text
            metadata: Document metadata
            score: Similarity score
        """
        self.text = text
        self.metadata = metadata
        self.score = score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "text": self.text,
            "metadata": self.metadata,
            "score": self.score
        }
    
    def __repr__(self) -> str:
        """String representation."""
        repo = self.metadata.get("repo_full_name", "unknown")
        return f"RetrievalResult(repo={repo}, score={self.score:.3f})"


def create_retriever(
    vector_server: vector_store.VectorStoreServer
) -> SemanticRetriever:
    """
    Factory function to create semantic retriever.
    
    Args:
        vector_server: VectorStoreServer instance
    
    Returns:
        SemanticRetriever instance
    
    Example:
        >>> vector_index = create_rag_index(summaries)
        >>> retriever = create_retriever(vector_index)
        >>> results = retriever.retrieve("Show me active repos")
    """
    return SemanticRetriever(vector_server)