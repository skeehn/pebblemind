"""Tests for RAG system"""

import pytest
import asyncio
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np

from pebblemind.config import RAGConfig
from pebblemind.rag.system import RAGSystem


@pytest.fixture
def rag_config(tmp_path):
    """Create RAG configuration for testing"""
    db_path = tmp_path / "test_vectors.db"
    return RAGConfig(
        embedding_model="BAAI/bge-small-en-v1.5",
        embedding_dim=384,
        vector_db_path=str(db_path),
        chunk_size=512,
        chunk_overlap=50,
        max_results=5
    )


@pytest.fixture
def mock_sentence_transformer():
    """Create mock SentenceTransformer"""
    mock = MagicMock()
    mock.encode.return_value = np.random.rand(1, 384).astype(np.float32)
    return mock


class TestRAGSystem:
    """Test RAG system functionality"""

    def test_initialization(self, rag_config):
        """Test RAG system initialization"""
        rag = RAGSystem(rag_config)
        assert rag.config == rag_config
        assert rag.embedding_model is None
        assert rag._initialized is False

    @pytest.mark.asyncio
    @patch('pebblemind.rag.system.SentenceTransformer')
    async def test_initialize_with_model(self, mock_st_class, rag_config, mock_sentence_transformer):
        """Test initialization with embedding model"""
        mock_st_class.return_value = mock_sentence_transformer

        rag = RAGSystem(rag_config)
        await rag.initialize()

        assert rag._initialized is True
        assert rag.embedding_model is not None

    @pytest.mark.asyncio
    async def test_initialize_without_sentence_transformers(self, rag_config):
        """Test initialization fails without sentence-transformers"""
        with patch('pebblemind.rag.system.SentenceTransformer', None):
            rag = RAGSystem(rag_config)
            with pytest.raises(ImportError, match="sentence-transformers not installed"):
                await rag.initialize()

    def test_chunk_text_basic(self, rag_config):
        """Test basic text chunking"""
        rag = RAGSystem(rag_config)
        text = " ".join([f"word{i}" for i in range(100)])
        chunks = rag._chunk_text(text)

        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_chunk_text_overlap(self, rag_config):
        """Test text chunking with overlap"""
        rag_config.chunk_size = 10
        rag_config.chunk_overlap = 3

        rag = RAGSystem(rag_config)
        text = " ".join([f"word{i}" for i in range(30)])
        chunks = rag._chunk_text(text)

        assert len(chunks) > 1

    def test_generate_document_id(self, rag_config):
        """Test document ID generation"""
        rag = RAGSystem(rag_config)

        id1 = rag._generate_document_id("test content")
        id2 = rag._generate_document_id("test content")
        id3 = rag._generate_document_id("different content")

        assert id1 == id2  # Same content should have same ID
        assert id1 != id3  # Different content should have different ID

    @pytest.mark.asyncio
    @patch('pebblemind.rag.system.SentenceTransformer')
    async def test_add_documents(self, mock_st_class, rag_config, mock_sentence_transformer):
        """Test adding documents to database"""
        mock_st_class.return_value = mock_sentence_transformer

        rag = RAGSystem(rag_config)
        await rag.initialize()

        documents = [
            {"content": "This is test document 1", "metadata": {"source": "test1"}},
            {"content": "This is test document 2", "metadata": {"source": "test2"}},
        ]

        await rag.add_documents(documents)

        # Verify documents were added
        conn = sqlite3.connect(str(rag_config.vector_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        count = cursor.fetchone()[0]
        conn.close()

        assert count > 0

    @pytest.mark.asyncio
    @patch('pebblemind.rag.system.SentenceTransformer')
    async def test_add_empty_document(self, mock_st_class, rag_config, mock_sentence_transformer):
        """Test that empty documents are skipped"""
        mock_st_class.return_value = mock_sentence_transformer

        rag = RAGSystem(rag_config)
        await rag.initialize()

        documents = [
            {"content": "", "metadata": {}},
            {"content": "   ", "metadata": {}},
        ]

        await rag.add_documents(documents)

        conn = sqlite3.connect(str(rag_config.vector_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 0

    @pytest.mark.asyncio
    @patch('pebblemind.rag.system.SentenceTransformer')
    async def test_search(self, mock_st_class, rag_config, mock_sentence_transformer):
        """Test document search"""
        mock_st_class.return_value = mock_sentence_transformer

        rag = RAGSystem(rag_config)
        await rag.initialize()

        # Add test documents
        documents = [
            {"content": "Python is a programming language", "metadata": {"topic": "python"}},
            {"content": "JavaScript is used for web development", "metadata": {"topic": "javascript"}},
        ]
        await rag.add_documents(documents)

        # Search
        results = await rag.search("programming", k=2)

        assert isinstance(results, list)
        assert len(results) <= 2
        if results:
            assert "content" in results[0]
            assert "id" in results[0]

    @pytest.mark.asyncio
    @patch('pebblemind.rag.system.SentenceTransformer')
    async def test_delete_document(self, mock_st_class, rag_config, mock_sentence_transformer):
        """Test document deletion"""
        mock_st_class.return_value = mock_sentence_transformer

        rag = RAGSystem(rag_config)
        await rag.initialize()

        # Add a document
        documents = [{"content": "Test document to delete", "metadata": {}}]
        await rag.add_documents(documents)

        # Get document ID
        doc_id = rag._generate_document_id("Test document to delete")

        # Delete it
        result = await rag.delete_document(doc_id)
        assert result is True

        # Try to delete again (should return False)
        result = await rag.delete_document(doc_id)
        assert result is False

    @pytest.mark.asyncio
    @patch('pebblemind.rag.system.SentenceTransformer')
    async def test_get_stats(self, mock_st_class, rag_config, mock_sentence_transformer):
        """Test getting database statistics"""
        mock_st_class.return_value = mock_sentence_transformer

        rag = RAGSystem(rag_config)
        await rag.initialize()

        # Add some documents
        documents = [
            {"content": "Document 1", "metadata": {}},
            {"content": "Document 2", "metadata": {}},
        ]
        await rag.add_documents(documents)

        stats = await rag.get_stats()

        assert "total_documents" in stats
        assert "database_size_bytes" in stats
        assert "embedding_dimension" in stats
        assert stats["total_documents"] > 0

    @pytest.mark.asyncio
    @patch('pebblemind.rag.system.SentenceTransformer')
    async def test_cleanup(self, mock_st_class, rag_config, mock_sentence_transformer):
        """Test cleanup"""
        mock_st_class.return_value = mock_sentence_transformer

        rag = RAGSystem(rag_config)
        await rag.initialize()

        await rag.cleanup()

        assert rag.embedding_model is None
        assert rag._initialized is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
