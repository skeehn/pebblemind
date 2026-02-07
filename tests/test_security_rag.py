import pytest
import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np

from pebblemind.rag.system import RAGSystem
from pebblemind.config import RAGConfig
from pebblemind.performance.connection_pool import ConnectionPool

@pytest.fixture
def rag_system(tmp_path):
    config = RAGConfig(
        embedding_model="test",
        embedding_dim=384,
        vector_db_path=str(tmp_path / "security_test.db")
    )
    rag = RAGSystem(config)
    return rag

@pytest.mark.asyncio
async def test_metadata_security_and_format(rag_system):
    # Mock embedding model
    rag_system.embedding_model = MagicMock()
    rag_system.embedding_model.encode.return_value = np.zeros((1, 384))

    # Setup database and pool
    await rag_system._setup_database()

    def create_conn():
        conn = sqlite3.connect(str(rag_system.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    rag_system.pool = ConnectionPool(
        create_connection=create_conn,
        close_connection=lambda c: c.close(),
        min_size=1,
        max_size=2
    )
    await rag_system.pool.start()
    rag_system._initialized = True

    # 1. Test that malicious metadata is NOT executed
    # We can't easily detect "execution" in this sandbox without side effects,
    # but we can verify it doesn't return the "eval" result.
    malicious_metadata = "__import__('os').getcwd()"
    parsed = rag_system._parse_metadata(malicious_metadata)
    assert parsed == {}
    assert not isinstance(parsed, str) # eval() would return a string path

    # 2. Test that legacy safe format is still supported
    legacy_metadata = "{'source': 'legacy', 'priority': 1}"
    parsed_legacy = rag_system._parse_metadata(legacy_metadata)
    assert parsed_legacy == {'source': 'legacy', 'priority': 1}

    # 3. Test that add_documents stores as JSON
    test_doc = [{"content": "Test content", "metadata": {"key": "value"}}]
    await rag_system.add_documents(test_doc)

    # Verify raw storage in DB
    conn = sqlite3.connect(str(rag_system.db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT metadata FROM documents LIMIT 1")
    raw_metadata = cursor.fetchone()[0]
    conn.close()

    # It should be valid JSON (double quotes)
    assert '"key": "value"' in raw_metadata
    json.loads(raw_metadata) # Should not raise

    # 4. Test that search correctly parses both formats
    # (We already added a JSON doc)
    results = await rag_system.search("Test")
    assert results[0]["metadata"] == {"key": "value"}

    await rag_system.cleanup()

if __name__ == "__main__":
    pytest.main([__file__])
