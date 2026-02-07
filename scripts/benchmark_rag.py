import asyncio
import time
import sqlite3
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np

# Ensure we can import pebblemind
import sys
import logging
sys.path.append(os.getcwd())

# Disable logging for benchmark
logging.getLogger("pebblemind.rag.system").setLevel(logging.ERROR)

from pebblemind.rag.system import RAGSystem
from pebblemind.config import RAGConfig

class LegacyRAGSystem(RAGSystem):
    """Simulates RAGSystem before pool integration and security fix"""
    async def search(self, query: str, k: int = 5) -> list:
        # Generate query embedding
        _ = self.embedding_model.encode([query])[0]

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        results = []

        # Simulating fallback search
        cursor.execute("SELECT id, content, metadata FROM documents LIMIT ?", (k,))
        for row in cursor.fetchall():
            doc_id, content, metadata = row
            results.append({
                "id": doc_id,
                "content": content,
                "metadata": eval(metadata) if metadata else {},
                "score": 0.5,
            })
        conn.close()
        return results

async def benchmark():
    db_path = "perf_test.db"
    config = RAGConfig(
        embedding_model="test",
        embedding_dim=384,
        vector_db_path=db_path
    )

    if Path(db_path).exists():
        Path(db_path).unlink()

    # Setup
    with patch('pebblemind.rag.system.SentenceTransformer') as mock_st_class:
        mock_st = MagicMock()
        mock_st.encode.return_value = np.random.rand(1, 384).astype(np.float32)
        mock_st_class.return_value = mock_st

        rag = RAGSystem(config)
        await rag.initialize()

        legacy_rag = LegacyRAGSystem(config)
        await legacy_rag.initialize()

        # Add dummy documents
        docs = [{"content": f"Document {i}", "metadata": {"id": i}} for i in range(100)]
        await rag.add_documents(docs)

        iterations = 500
        print(f"Running {iterations} searches...")

        # Benchmark New (with pool)
        await rag.search("warmup")
        start = time.perf_counter()
        for i in range(iterations):
            await rag.search(f"query {i}")
        pool_time = time.perf_counter() - start

        # Benchmark Legacy (without pool)
        await legacy_rag.search("warmup")
        start = time.perf_counter()
        for i in range(iterations):
            await legacy_rag.search(f"query {i}")
        legacy_time = time.perf_counter() - start

        print(f"\nNew RAG (Pool + Security Fix): {pool_time:.4f}s ({pool_time/iterations*1000:.4f}ms/op)")
        print(f"Legacy RAG (No Pool + eval): {legacy_time:.4f}s ({legacy_time/iterations*1000:.4f}ms/op)")

        improvement = (legacy_time - pool_time) / legacy_time * 100
        print(f"\nImprovement: {improvement:.2f}%")

        await rag.cleanup()
        await legacy_rag.cleanup()

    if Path(db_path).exists():
        Path(db_path).unlink()

if __name__ == "__main__":
    asyncio.run(benchmark())
