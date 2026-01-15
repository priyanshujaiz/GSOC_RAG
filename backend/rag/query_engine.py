"""
RAG Query Engine - orchestrates the complete RAG pipeline.
Handles query → retrieve → augment → generate flow.
"""

from typing import Dict, Any, List, Optional
import asyncio
from openai import AsyncOpenAI
from backend.core.config import Settings
from backend.core.logger import get_logger
from backend.rag.retriever import SemanticRetriever, RetrievalResult
from backend.rag.prompts import (
    SYSTEM_PROMPT,
    build_rag_prompt,
    build_comparison_prompt,
    build_trending_prompt,
    get_suggested_questions
)
settings=Settings()

logger = get_logger(__name__)


class RAGQueryEngine:
    """
    Complete RAG query engine implementing:
    - Retrieval: Find relevant summaries
    - Augmentation: Build context with retrieved data
    - Generation: Use LLM to generate grounded answers
    """
    
    def __init__(
        self,
        retriever: SemanticRetriever,
        llm_model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_tokens: int = 1000
    ):
        """
        Initialize RAG query engine.
        
        Args:
            retriever: SemanticRetriever instance for searching vector index
            llm_model: OpenAI model to use (default: gpt-4o-mini)
            temperature: LLM temperature (0 = deterministic, 1 = creative)
            max_tokens: Maximum tokens in response
        """
        self.retriever = retriever
        self.llm_model = llm_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize OpenAI client
        self.llm_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        logger.info(f"RAGQueryEngine initialized with model: {llm_model}")
        logger.debug(f"Temperature: {temperature}, Max tokens: {max_tokens}")
    
    async def query(
        self,
        user_question: str,
        top_k: int = 5,
        include_sources: bool = True,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute complete RAG pipeline for a user question.
        
        This is the main entry point that orchestrates:
        1. RETRIEVE: Search vector index for relevant summaries
        2. AUGMENT: Build prompt with retrieved context
        3. GENERATE: Call LLM to generate answer
        
        Args:
            user_question: Natural language question
            top_k: Number of summaries to retrieve (default: 5)
            include_sources: Whether to include source summaries in response
            metadata_filter: Optional filters for retrieval
        
        Returns:
            Dictionary containing:
            - answer: The LLM-generated answer
            - sources: Retrieved summaries (if include_sources=True)
            - query: Original question
            - model: LLM model used
            - tokens_used: Approximate token count
        
        Example:
            >>> engine = RAGQueryEngine(retriever)
            >>> result = await engine.query("Which repos are most active?")
            >>> print(result["answer"])
        """
        logger.info(f"Processing query: '{user_question}'")
        
        try:
            # Step 1: RETRIEVE - Get relevant summaries
            logger.debug("Step 1: Retrieving relevant summaries")
            retrieval_results = await self._retrieve(
                user_question, 
                top_k=top_k,
                metadata_filter=metadata_filter
            )
            
            logger.info(f"Retrieved {len(retrieval_results)} summaries")
            
            # Step 2: AUGMENT - Build prompt with context
            logger.debug("Step 2: Building prompt with context")
            prompt = self._build_prompt(user_question, retrieval_results)
            
            logger.debug(f"Prompt built: {len(prompt)} characters")
            
            # Step 3: GENERATE - Call LLM
            logger.debug("Step 3: Generating answer with LLM")
            answer, usage = await self._generate(prompt)
            
            logger.info("Answer generated successfully")
            
            # Build response
            response = {
                "answer": answer,
                "query": user_question,
                "model": self.llm_model,
                "tokens_used": usage.get("total_tokens", 0),
            }
            
            # Add sources if requested
            if include_sources:
                response["sources"] = [
                    result.to_dict() for result in retrieval_results
                ]
                response["num_sources"] = len(retrieval_results)
            
            # Add suggested follow-up questions
            response["suggested_questions"] = get_suggested_questions(
                [r.to_dict() for r in retrieval_results],
                max_suggestions=3
            )
            
            logger.debug(f"Total tokens used: {response['tokens_used']}")
            
            return response
            
        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)
            raise RAGQueryError(f"Failed to process query: {e}") from e
    
    async def _retrieve(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant summaries from vector index.
        
        Args:
            query: User question
            top_k: Number of results
            metadata_filter: Optional filters
        
        Returns:
            List of RetrievalResult objects
        """
        # For now, this is a placeholder that returns mock results
        # In production, this would query the VectorStoreServer's HTTP endpoint
        
        logger.debug(f"Retrieving top-{top_k} results for: '{query}'")
        
        # Simulate retrieval results
        # In actual implementation, this would call:
        # results = self.retriever.retrieve(query, top_k, metadata_filter)
        
        mock_results = [
            RetrievalResult(
                text=f"openai/openai-python is 🔥 HOT with 12 events in 1h window. Activity: 3 commits, 4 PRs, 2 issues, 1 releases. Score: 18 points. Momentum: ACCELERATING.",
                metadata={
                    "repo_full_name": "openai/openai-python",
                    "activity_score": 18,
                    "trend_status": "🔥 HOT",
                    "window_period": "1h"
                },
                score=0.92
            ),
            RetrievalResult(
                text=f"langchain-ai/langchain is 📈 ACTIVE with 8 events in 1h window. Activity: 2 commits, 3 PRs, 2 issues, 1 releases. Score: 14 points. Momentum: STEADY.",
                metadata={
                    "repo_full_name": "langchain-ai/langchain",
                    "activity_score": 14,
                    "trend_status": "📈 ACTIVE",
                    "window_period": "1h"
                },
                score=0.85
            ),
            RetrievalResult(
                text=f"fastapi/fastapi is 📊 MODERATE with 4 events in 1h window. Activity: 1 commits, 2 PRs, 1 issues, 0 releases. Score: 8 points. Momentum: STEADY.",
                metadata={
                    "repo_full_name": "fastapi/fastapi",
                    "activity_score": 8,
                    "trend_status": "📊 MODERATE",
                    "window_period": "1h"
                },
                score=0.78
            ),
        ]
        
        logger.debug(f"Mock retrieval returned {len(mock_results)} results")
        return mock_results[:top_k]
    
    def _build_prompt(
        self,
        user_question: str,
        retrieval_results: List[RetrievalResult]
    ) -> str:
        """
        Build prompt with retrieved context.
        
        Args:
            user_question: User's question
            retrieval_results: Retrieved summaries
        
        Returns:
            Complete prompt for LLM
        """
        # Convert RetrievalResult objects to dict format
        summaries = [result.to_dict() for result in retrieval_results]
        
        # Detect query type and use appropriate prompt builder
        question_lower = user_question.lower()
        
        if "compar" in question_lower:
            prompt = build_comparison_prompt(user_question, summaries)
            logger.debug("Using comparison prompt template")
        elif "trend" in question_lower or "hot" in question_lower or "popular" in question_lower:
            prompt = build_trending_prompt(summaries)
            logger.debug("Using trending prompt template")
        else:
            prompt = build_rag_prompt(user_question, summaries)
            logger.debug("Using standard RAG prompt template")
        
        return prompt
    
    async def _generate(self, prompt: str) -> tuple[str, Dict[str, int]]:
        """
        Generate answer using LLM.
        
        Args:
            prompt: Complete prompt with context
        
        Returns:
            Tuple of (answer_text, usage_stats)
        """
        logger.debug(f"Calling {self.llm_model} with prompt length: {len(prompt)}")
        
        try:
            response = await self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            answer = response.choices[0].message.content
            
            # Extract usage statistics
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            
            logger.info(f"LLM response received: {usage['total_tokens']} tokens")
            logger.debug(f"Answer length: {len(answer)} characters")
            
            return answer, usage
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}", exc_info=True)
            raise
    
    async def batch_query(
        self,
        questions: List[str],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Process multiple queries in parallel.
        
        Useful for testing or bulk operations.
        
        Args:
            questions: List of user questions
            top_k: Number of summaries per query
        
        Returns:
            List of response dictionaries
        """
        logger.info(f"Processing batch of {len(questions)} queries")
        
        # Execute queries in parallel
        tasks = [self.query(q, top_k=top_k) for q in questions]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        successful_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Query {idx} failed: {result}")
                successful_results.append({
                    "error": str(result),
                    "query": questions[idx]
                })
            else:
                successful_results.append(result)
        
        logger.info(f"Batch complete: {len(successful_results)} results")
        return successful_results


class RAGQueryError(Exception):
    """Custom exception for RAG query errors."""
    pass


def create_query_engine(
    retriever: SemanticRetriever,
    llm_model: str = "gpt-4o-mini",
    temperature: float = 0.3
) -> RAGQueryEngine:
    """
    Factory function to create RAG query engine.
    
    Args:
        retriever: SemanticRetriever instance
        llm_model: OpenAI model name
        temperature: LLM temperature
    
    Returns:
        RAGQueryEngine instance
    
    Example:
        >>> retriever = create_retriever(vector_server)
        >>> engine = create_query_engine(retriever)
        >>> result = await engine.query("Show me active repos")
    """
    return RAGQueryEngine(
        retriever=retriever,
        llm_model=llm_model,
        temperature=temperature
    )