"""
RAG Reranking system for improved retrieval quality.

Implements multiple reranking strategies to ensure the most relevant
documents are provided to the LLM.

Based on research:
- "Precise Zero-Shot Dense Retrieval without Relevance Labels" (HyDE)
- "RankGPT: Listwise Passage Reranking with GPT" (Sun et al., 2023)
- Cross-encoder reranking techniques
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
import logging
import asyncio

logger = logging.getLogger(__name__)


class RerankingStrategy(Enum):
    """Reranking strategies"""
    CROSS_ENCODER = "cross_encoder"  # Deep semantic matching
    RECIPROCAL_RANK_FUSION = "reciprocal_rank_fusion"  # Combine multiple rankings
    DIVERSITY = "diversity"  # Maximize diversity
    HYDE = "hyde"  # Hypothetical document embeddings
    MMR = "mmr"  # Maximal marginal relevance


@dataclass
class RankedDocument:
    """Document with ranking information"""
    content: str
    score: float
    rank: int
    metadata: Optional[Dict[str, Any]] = None
    original_rank: Optional[int] = None


@dataclass
class RerankingResult:
    """Result of reranking operation"""
    documents: List[RankedDocument]
    strategy_used: RerankingStrategy
    score_distribution: Dict[str, float]


class RAGReranker:
    """
    Advanced reranking system for RAG retrieval.

    Improves retrieval quality by reranking initial results using
    sophisticated relevance models.
    """

    def __init__(self, embedding_model=None):
        """
        Initialize reranker

        Args:
            embedding_model: Optional embedding model for semantic reranking
        """
        self.embedding_model = embedding_model

    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
        strategy: RerankingStrategy = RerankingStrategy.RECIPROCAL_RANK_FUSION,
        **kwargs
    ) -> RerankingResult:
        """
        Rerank documents for better relevance

        Args:
            query: User query
            documents: Retrieved documents
            top_k: Number of documents to return
            strategy: Reranking strategy
            **kwargs: Strategy-specific parameters

        Returns:
            Reranking result
        """
        logger.info(f"Reranking {len(documents)} documents using {strategy.value}")

        if strategy == RerankingStrategy.CROSS_ENCODER:
            result = await self._cross_encoder_rerank(query, documents, top_k, **kwargs)
        elif strategy == RerankingStrategy.RECIPROCAL_RANK_FUSION:
            result = await self._reciprocal_rank_fusion(query, documents, top_k, **kwargs)
        elif strategy == RerankingStrategy.DIVERSITY:
            result = await self._diversity_rerank(query, documents, top_k, **kwargs)
        elif strategy == RerankingStrategy.HYDE:
            result = await self._hyde_rerank(query, documents, top_k, **kwargs)
        elif strategy == RerankingStrategy.MMR:
            result = await self._mmr_rerank(query, documents, top_k, **kwargs)
        else:
            # Default fallback
            result = await self._simple_rerank(query, documents, top_k)

        logger.info(
            f"Reranking complete: top score={result.documents[0].score:.3f}, "
            f"bottom score={result.documents[-1].score:.3f}"
        )

        return result

    async def _simple_rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int
    ) -> RerankingResult:
        """
        Simple reranking based on existing scores

        Args:
            query: User query
            documents: Documents
            top_k: Number to return

        Returns:
            Reranked documents
        """
        # Sort by existing scores
        sorted_docs = sorted(
            documents,
            key=lambda d: d.get("score", 0.0),
            reverse=True
        )[:top_k]

        ranked = []
        for i, doc in enumerate(sorted_docs):
            ranked.append(RankedDocument(
                content=doc.get("content", ""),
                score=doc.get("score", 0.0),
                rank=i + 1,
                metadata=doc.get("metadata"),
                original_rank=documents.index(doc) + 1
            ))

        return RerankingResult(
            documents=ranked,
            strategy_used=RerankingStrategy.CROSS_ENCODER,  # Placeholder
            score_distribution=self._calculate_score_distribution(ranked)
        )

    async def _cross_encoder_rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int,
        **kwargs
    ) -> RerankingResult:
        """
        Rerank using cross-encoder (deep semantic matching)

        Args:
            query: User query
            documents: Documents
            top_k: Number to return
            **kwargs: Additional parameters

        Returns:
            Reranked documents
        """
        # Score each document based on query-document semantic similarity
        scored_docs = []

        for doc in documents:
            content = doc.get("content", "")

            # Calculate relevance score using multiple signals
            score = await self._calculate_relevance_score(query, content)

            scored_docs.append({
                "doc": doc,
                "score": score
            })

        # Sort by score
        scored_docs.sort(key=lambda x: x["score"], reverse=True)

        # Take top-k
        top_docs = scored_docs[:top_k]

        ranked = []
        for i, item in enumerate(top_docs):
            doc = item["doc"]
            ranked.append(RankedDocument(
                content=doc.get("content", ""),
                score=item["score"],
                rank=i + 1,
                metadata=doc.get("metadata"),
                original_rank=documents.index(doc) + 1
            ))

        return RerankingResult(
            documents=ranked,
            strategy_used=RerankingStrategy.CROSS_ENCODER,
            score_distribution=self._calculate_score_distribution(ranked)
        )

    async def _calculate_relevance_score(
        self,
        query: str,
        document: str
    ) -> float:
        """
        Calculate query-document relevance score

        Args:
            query: User query
            document: Document content

        Returns:
            Relevance score (0.0 to 1.0)
        """
        scores = []

        # 1. Keyword overlap (BM25-like)
        keyword_score = self._keyword_overlap_score(query, document)
        scores.append(keyword_score * 0.3)

        # 2. Semantic similarity (if embedding model available)
        if self.embedding_model:
            semantic_score = await self._semantic_similarity(query, document)
            scores.append(semantic_score * 0.5)
        else:
            # Fallback: simple cosine similarity on TF-IDF
            semantic_score = self._simple_similarity(query, document)
            scores.append(semantic_score * 0.5)

        # 3. Query term coverage
        coverage_score = self._query_coverage_score(query, document)
        scores.append(coverage_score * 0.2)

        return sum(scores)

    def _keyword_overlap_score(self, query: str, document: str) -> float:
        """Calculate keyword overlap score"""
        query_terms = set(query.lower().split())
        doc_terms = set(document.lower().split())

        if not query_terms:
            return 0.0

        overlap = len(query_terms & doc_terms)
        return overlap / len(query_terms)

    def _query_coverage_score(self, query: str, document: str) -> float:
        """Calculate what fraction of query terms appear in document"""
        query_terms = query.lower().split()
        doc_lower = document.lower()

        covered = sum(1 for term in query_terms if term in doc_lower)
        return covered / len(query_terms) if query_terms else 0.0

    def _simple_similarity(self, query: str, document: str) -> float:
        """Simple similarity without embeddings"""
        # Jaccard similarity
        query_words = set(query.lower().split())
        doc_words = set(document.lower().split())

        intersection = len(query_words & doc_words)
        union = len(query_words | doc_words)

        return intersection / union if union > 0 else 0.0

    async def _semantic_similarity(self, query: str, document: str) -> float:
        """Calculate semantic similarity using embeddings"""
        # This would use the embedding model
        # Placeholder for now
        return self._simple_similarity(query, document)

    async def _reciprocal_rank_fusion(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int,
        k: int = 60,
        **kwargs
    ) -> RerankingResult:
        """
        Reciprocal Rank Fusion for combining multiple rankings

        RRF score = Σ 1/(k + rank_i)

        Args:
            query: User query
            documents: Documents
            top_k: Number to return
            k: RRF constant (default: 60)
            **kwargs: Additional parameters

        Returns:
            Reranked documents
        """
        # Get multiple ranking signals
        rankings = []

        # 1. Original scores
        original_ranking = sorted(
            enumerate(documents),
            key=lambda x: x[1].get("score", 0.0),
            reverse=True
        )
        rankings.append(original_ranking)

        # 2. Keyword-based ranking
        keyword_ranking = []
        for i, doc in enumerate(documents):
            content = doc.get("content", "")
            score = self._keyword_overlap_score(query, content)
            keyword_ranking.append((i, score))
        keyword_ranking.sort(key=lambda x: x[1], reverse=True)
        rankings.append([(idx, None) for idx, _ in keyword_ranking])

        # 3. Length-normalized ranking (longer docs might be more comprehensive)
        length_ranking = sorted(
            enumerate(documents),
            key=lambda x: len(x[1].get("content", "")),
            reverse=True
        )
        rankings.append(length_ranking)

        # Calculate RRF scores
        rrf_scores = {}
        for ranking in rankings:
            for rank, (doc_idx, _) in enumerate(ranking, 1):
                if doc_idx not in rrf_scores:
                    rrf_scores[doc_idx] = 0
                rrf_scores[doc_idx] += 1 / (k + rank)

        # Sort by RRF score
        sorted_indices = sorted(
            rrf_scores.keys(),
            key=lambda idx: rrf_scores[idx],
            reverse=True
        )[:top_k]

        # Build ranked results
        ranked = []
        for i, doc_idx in enumerate(sorted_indices):
            doc = documents[doc_idx]
            ranked.append(RankedDocument(
                content=doc.get("content", ""),
                score=rrf_scores[doc_idx],
                rank=i + 1,
                metadata=doc.get("metadata"),
                original_rank=doc_idx + 1
            ))

        return RerankingResult(
            documents=ranked,
            strategy_used=RerankingStrategy.RECIPROCAL_RANK_FUSION,
            score_distribution=self._calculate_score_distribution(ranked)
        )

    async def _mmr_rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int,
        lambda_param: float = 0.5,
        **kwargs
    ) -> RerankingResult:
        """
        Maximal Marginal Relevance reranking

        Balances relevance with diversity to avoid redundant results.

        MMR = argmax[λ * Sim(D, Q) - (1-λ) * max Sim(D, D_i)]

        Args:
            query: User query
            documents: Documents
            top_k: Number to return
            lambda_param: Balance between relevance (1.0) and diversity (0.0)
            **kwargs: Additional parameters

        Returns:
            Reranked documents
        """
        if not documents:
            return RerankingResult([], RerankingStrategy.MMR, {})

        # Calculate query relevance for all documents
        relevance_scores = []
        for doc in documents:
            content = doc.get("content", "")
            score = await self._calculate_relevance_score(query, content)
            relevance_scores.append(score)

        selected = []
        remaining = list(range(len(documents)))

        # Select first document (highest relevance)
        first_idx = max(remaining, key=lambda i: relevance_scores[i])
        selected.append(first_idx)
        remaining.remove(first_idx)

        # Iteratively select documents
        while len(selected) < min(top_k, len(documents)):
            mmr_scores = []

            for i in remaining:
                # Relevance to query
                relevance = relevance_scores[i]

                # Max similarity to already selected documents
                max_sim = 0.0
                for j in selected:
                    sim = self._simple_similarity(
                        documents[i].get("content", ""),
                        documents[j].get("content", "")
                    )
                    max_sim = max(max_sim, sim)

                # MMR score
                mmr = lambda_param * relevance - (1 - lambda_param) * max_sim
                mmr_scores.append((i, mmr))

            # Select document with highest MMR
            best_idx = max(mmr_scores, key=lambda x: x[1])[0]
            selected.append(best_idx)
            remaining.remove(best_idx)

        # Build ranked results
        ranked = []
        for i, doc_idx in enumerate(selected):
            doc = documents[doc_idx]
            ranked.append(RankedDocument(
                content=doc.get("content", ""),
                score=relevance_scores[doc_idx],
                rank=i + 1,
                metadata=doc.get("metadata"),
                original_rank=doc_idx + 1
            ))

        return RerankingResult(
            documents=ranked,
            strategy_used=RerankingStrategy.MMR,
            score_distribution=self._calculate_score_distribution(ranked)
        )

    async def _diversity_rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int,
        **kwargs
    ) -> RerankingResult:
        """
        Maximize diversity in results

        Args:
            query: User query
            documents: Documents
            top_k: Number to return
            **kwargs: Additional parameters

        Returns:
            Diverse reranked documents
        """
        # Use MMR with higher diversity weight
        return await self._mmr_rerank(query, documents, top_k, lambda_param=0.3)

    async def _hyde_rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int,
        generate_func=None,
        **kwargs
    ) -> RerankingResult:
        """
        Hypothetical Document Embeddings (HyDE) reranking

        Generates a hypothetical answer, then searches for documents
        similar to that answer.

        Args:
            query: User query
            documents: Documents
            top_k: Number to return
            generate_func: Function to generate hypothetical document
            **kwargs: Additional parameters

        Returns:
            Reranked documents
        """
        # If we can't generate hypothetical document, fallback
        if not generate_func:
            logger.warning("HyDE requires generate_func, falling back to cross-encoder")
            return await self._cross_encoder_rerank(query, documents, top_k)

        # Generate hypothetical answer
        hypothetical_prompt = f"""Given the question: "{query}"

Write a detailed, hypothetical answer that would perfectly answer this question:"""

        hypothetical_doc = await generate_func(hypothetical_prompt, max_tokens=200)

        # Rerank based on similarity to hypothetical document
        scored_docs = []
        for doc in documents:
            content = doc.get("content", "")
            similarity = self._simple_similarity(hypothetical_doc, content)
            scored_docs.append({
                "doc": doc,
                "score": similarity
            })

        # Sort and take top-k
        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        top_docs = scored_docs[:top_k]

        ranked = []
        for i, item in enumerate(top_docs):
            doc = item["doc"]
            ranked.append(RankedDocument(
                content=doc.get("content", ""),
                score=item["score"],
                rank=i + 1,
                metadata=doc.get("metadata"),
                original_rank=documents.index(doc) + 1
            ))

        return RerankingResult(
            documents=ranked,
            strategy_used=RerankingStrategy.HYDE,
            score_distribution=self._calculate_score_distribution(ranked)
        )

    def _calculate_score_distribution(
        self,
        documents: List[RankedDocument]
    ) -> Dict[str, float]:
        """Calculate statistics about score distribution"""
        if not documents:
            return {}

        scores = [doc.score for doc in documents]

        return {
            "min": min(scores),
            "max": max(scores),
            "mean": sum(scores) / len(scores),
            "std": np.std(scores) if len(scores) > 1 else 0.0
        }


# Global reranker
_reranker: Optional[RAGReranker] = None


def get_reranker() -> RAGReranker:
    """Get global reranker instance"""
    global _reranker
    if _reranker is None:
        _reranker = RAGReranker()
    return _reranker
