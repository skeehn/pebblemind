"""RAG System using BGE-small embeddings and sqlite-vec"""

import asyncio
import logging
import sqlite3
import hashlib
import json
import ast
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from ..config import RAGConfig
from ..performance.connection_pool import ConnectionPool

logger = logging.getLogger(__name__)
FALLBACK_SEARCH_MIN_TERM_LENGTH = 3


class RAGSystem:
    """Retrieval-Augmented Generation system with vector search"""

    def __init__(self, config: RAGConfig):
        """Initialize RAG system with configuration"""
        self.config = config
        self.db_path = Path(config.vector_db_path)
        self.embedding_model = None
        self.pool = None
        self._initialized = False

        # Verify sqlite-vec is available
        try:
            import sqlite_vec
            self.sqlite_vec_available = True
        except ImportError:
            logger.warning("sqlite-vec not available. Install it for vector search capabilities.")
            self.sqlite_vec_available = False

    async def initialize(self) -> None:
        """Initialize the RAG system"""
        if self._initialized:
            return

        try:
            logger.info("Initializing RAG system...")

            # Initialize embedding model
            await self._setup_embedding_model()

            # Setup database
            await self._setup_database()

            # Initialize connection pool
            def create_conn():
                conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
                conn.row_factory = sqlite3.Row
                if self.sqlite_vec_available:
                    conn.enable_load_extension(True)
                    import sqlite_vec
                    sqlite_vec.load(conn)
                    conn.enable_load_extension(False)
                return conn

            self.pool = ConnectionPool(
                create_connection=create_conn,
                close_connection=lambda c: c.close(),
                health_check=None,  # SQLite connections are local and fast to recreate if needed
                min_size=1,
                max_size=5
            )
            await self.pool.start()

            self._initialized = True
            logger.info("RAG system initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {e}")
            raise

    async def _setup_embedding_model(self) -> None:
        """Setup BGE-small embedding model"""
        if SentenceTransformer is None:
            raise ImportError("sentence-transformers not installed. Install with: pip install sentence-transformers")

        try:
            logger.info(f"Loading embedding model: {self.config.embedding_model}")

            # Load BGE-small model with optimizations
            self.embedding_model = SentenceTransformer(
                self.config.embedding_model,
                device="cpu",  # Force CPU usage for consistency
                cache_folder="./cache/embeddings"
            )

            # Verify embedding dimension
            test_embedding = self.embedding_model.encode(["test"])
            actual_dim = test_embedding.shape[1]

            if actual_dim != self.config.embedding_dim:
                logger.warning(f"Embedding dimension mismatch. Expected {self.config.embedding_dim}, got {actual_dim}")
                self.config.embedding_dim = actual_dim

            logger.info(f"Embedding model loaded with dimension: {self.config.embedding_dim}")

        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    async def _setup_database(self) -> None:
        """Setup SQLite database with vector extensions"""
        try:
            # Create database directory if it doesn't exist
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Connect to database
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Enable vector extension if available
            if self.sqlite_vec_available:
                conn.enable_load_extension(True)
                import sqlite_vec
                sqlite_vec.load(conn)
                conn.enable_load_extension(False)

                # Create vector table
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS documents (
                        id TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        metadata TEXT,
                        embedding BLOB
                    )
                """)

                # Create vector index
                cursor.execute(f"""
                    CREATE VIRTUAL TABLE IF NOT EXISTS documents_vec USING vec0(
                        id TEXT PRIMARY KEY,
                        embedding float[{self.config.embedding_dim}]
                    )
                """)
            else:
                # Fallback to regular table without vector search
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        metadata TEXT,
                        embedding BLOB
                    )
                """)

            conn.commit()
            conn.close()

            logger.info(f"Database setup complete at: {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to setup database: {e}")
            raise

    def _generate_document_id(self, content: str) -> str:
        """Generate unique document ID from content"""
        return hashlib.md5(content.encode()).hexdigest()

    def _parse_metadata(self, metadata_str: str) -> Dict[str, Any]:
        """Safely parse metadata from string (handles JSON and legacy str(dict) format)"""
        if not metadata_str:
            return {}
        try:
            return json.loads(metadata_str)
        except json.JSONDecodeError:
            try:
                # Fallback for legacy format
                result = ast.literal_eval(metadata_str)
                return result if isinstance(result, dict) else {}
            except (ValueError, SyntaxError):
                return {}

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks for embedding"""
        words = text.split()
        chunks = []

        for i in range(0, len(words), self.config.chunk_size - self.config.chunk_overlap):
            chunk = " ".join(words[i:i + self.config.chunk_size])
            chunks.append(chunk)

            # Add overlap for next chunk
            if i + self.config.chunk_size < len(words):
                overlap_start = max(0, i + self.config.chunk_size - self.config.chunk_overlap)
                if overlap_start < len(words):
                    overlap_chunk = " ".join(words[overlap_start:i + self.config.chunk_size])
                    if len(overlap_chunk.split()) >= self.config.chunk_overlap:
                        chunks.append(overlap_chunk)

        return list(set(chunks))  # Remove duplicates

    def _extract_search_terms(self, query: str) -> List[str]:
        """Extract normalized terms for fallback text search.

        Short tokenized words below the minimum length are dropped, but if that
        would remove everything and the original query is non-empty, the raw
        lowercased query is preserved so fallback search can still attempt a match.
        Empty queries return an empty term list.
        """
        terms = [
            term
            for term in re.findall(r"\b\w+\b", query.lower())
            if len(term) >= FALLBACK_SEARCH_MIN_TERM_LENGTH
        ]

        if not terms and query.strip():
            terms = [query.strip().lower()]

        return list(dict.fromkeys(terms))

    async def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Add documents to the vector database"""
        if not self._initialized:
            await self.initialize()

        try:
            logger.info(f"Adding {len(documents)} documents to RAG system")

            async with self.pool.acquire() as conn:
                cursor = conn.cursor()

                for doc in documents:
                    content = doc.get("content", "")
                    metadata = doc.get("metadata", {})

                    # Skip empty documents
                    if not content.strip():
                        continue

                    # Chunk the document
                    chunks = self._chunk_text(content)

                    for chunk in chunks:
                        # Generate embedding
                        embedding = self.embedding_model.encode([chunk])[0]

                        # Generate document ID
                        doc_id = self._generate_document_id(chunk)

                        # Store in database
                        if self.sqlite_vec_available:
                            # Use vector extension
                            cursor.execute("""
                                INSERT OR REPLACE INTO documents (id, content, metadata, embedding)
                                VALUES (?, ?, ?, ?)
                            """, (doc_id, chunk, json.dumps(metadata), embedding.tobytes()))

                            cursor.execute("""
                                INSERT OR REPLACE INTO documents_vec (id, embedding)
                                VALUES (?, ?)
                            """, (doc_id, embedding.astype(np.float32)))
                        else:
                            # Store embedding as blob
                            cursor.execute("""
                                INSERT OR REPLACE INTO documents (id, content, metadata, embedding)
                                VALUES (?, ?, ?, ?)
                            """, (doc_id, chunk, json.dumps(metadata), embedding.tobytes()))

                conn.commit()

            logger.info("Documents added successfully")

        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise

    async def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant documents using vector similarity"""
        if not self._initialized:
            await self.initialize()

        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0]

            results = []

            async with self.pool.acquire() as conn:
                cursor = conn.cursor()

                if self.sqlite_vec_available:
                    # Use vector search
                    cursor.execute("""
                        SELECT documents.id, documents.content, documents.metadata,
                               vec_distance_cosine(documents_vec.embedding, ?) as distance
                        FROM documents
                        JOIN documents_vec ON documents.id = documents_vec.id
                        ORDER BY distance
                        LIMIT ?
                    """, (query_embedding.astype(np.float32), k))

                    for row in cursor.fetchall():
                        doc_id, content, metadata, distance = row
                        results.append({
                            "id": doc_id,
                            "content": content,
                            "metadata": self._parse_metadata(metadata),
                            "score": 1.0 - distance if distance is not None else 0.0,
                        })
                else:
                    # Fallback to simple search (no vector similarity)
                    logger.warning("Vector search not available, using basic text search")

                    search_terms = self._extract_search_terms(query)
                    term_count = len(search_terms)
                    if not term_count:
                        return results

                    where_clause = " OR ".join(["LOWER(content) LIKE ?" for _ in search_terms])
                    search_patterns = tuple(f"%{term}%" for term in search_terms)

                    cursor.execute(f"""
                        SELECT id, content, metadata
                        FROM documents
                        WHERE {where_clause}
                    """, search_patterns)

                    ranked_rows = []
                    for row in cursor.fetchall():
                        doc_id, content, metadata = row
                        content_lower = content.lower()
                        match_count = sum(term in content_lower for term in search_terms)
                        ranked_rows.append((match_count, doc_id, content, metadata))

                    for match_count, doc_id, content, metadata in sorted(ranked_rows, reverse=True)[:k]:
                        results.append({
                            "id": doc_id,
                            "content": content,
                            "metadata": self._parse_metadata(metadata),
                            "score": match_count / term_count,
                        })

                return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the database"""
        if not self._initialized:
            await self.initialize()

        try:
            async with self.pool.acquire() as conn:
                cursor = conn.cursor()

                # Delete from both tables
                cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))

                if self.sqlite_vec_available:
                    cursor.execute("DELETE FROM documents_vec WHERE id = ?", (doc_id,))

                deleted = cursor.rowcount > 0
                conn.commit()

                return deleted

        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        if not self._initialized:
            await self.initialize()

        try:
            async with self.pool.acquire() as conn:
                cursor = conn.cursor()

                # Get document count
                cursor.execute("SELECT COUNT(*) FROM documents")
                doc_count = cursor.fetchone()[0]

            # Get database size
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

            return {
                "total_documents": doc_count,
                "database_size_bytes": db_size,
                "database_size_mb": db_size / (1024 * 1024),
                "vector_search_enabled": self.sqlite_vec_available,
                "embedding_dimension": self.config.embedding_dim,
                "embedding_model": self.config.embedding_model,
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}

    async def cleanup(self) -> None:
        """Clean up resources"""
        if self.pool:
            await self.pool.stop()
            self.pool = None

        if self.embedding_model:
            # Clear embedding model from memory
            self.embedding_model = None

        self._initialized = False
        logger.info("RAG system cleaned up")
