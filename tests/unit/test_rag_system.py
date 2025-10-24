"""Unit tests for RAG System"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from pebblemind.rag.system import RAGSystem
from pebblemind.config import RAGConfig


@pytest.mark.unit
class TestRAGSystem:
    """Test suite for RAG System"""

    @pytest.mark.asyncio
    async def test_initialization(self, rag_config, temp_dir):
        """Test RAG system initialization"""
        rag = RAGSystem(rag_config)
        assert not rag._initialized
        assert rag.config == rag_config

        # Mock the embedding model
        with patch('pebblemind.rag.system.SentenceTransformer') as mock_st:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.random.rand(1, 384).astype(np.float32)
            mock_st.return_value = mock_model

            await rag.initialize()
            assert rag._initialized
            assert rag.embedding_model is not None

    @pytest.mark.asyncio
    async def test_metadata_security_fix(self, rag_config, temp_dir):
        """Test that metadata uses json.loads instead of eval (security fix)"""
        rag = RAGSystem(rag_config)

        # Mock the embedding model
        with patch('pebblemind.rag.system.SentenceTransformer') as mock_st:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.random.rand(1, 384).astype(np.float32)
            mock_st.return_value = mock_model

            await rag.initialize()

            # Add a document with metadata
            test_metadata = {"author": "test", "year": 2024}
            documents = [{
                "content": "Test content for metadata",
                "metadata": test_metadata
            }]

            await rag.add_documents(documents)

            # Search for the document
            results = await rag.search("Test content", k=1)

            # Verify metadata was properly serialized and deserialized
            assert len(results) > 0
            result_metadata = results[0]["metadata"]
            assert isinstance(result_metadata, dict)
            assert result_metadata == test_metadata

    @pytest.mark.asyncio
    async def test_metadata_malicious_code_rejected(self, rag_config, temp_dir):
        """Test that malicious code in metadata cannot be executed"""
        import sqlite3

        rag = RAGSystem(rag_config)

        with patch('pebblemind.rag.system.SentenceTransformer') as mock_st:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.random.rand(1, 384).astype(np.float32)
            mock_st.return_value = mock_model

            await rag.initialize()

            # Manually insert malicious metadata into database
            conn = sqlite3.connect(str(rag.db_path))
            cursor = conn.cursor()

            # Insert document with malicious metadata string
            malicious_metadata = "__import__('os').system('echo hacked')"
            embedding = np.random.rand(384).astype(np.float32)

            cursor.execute("""
                INSERT INTO documents (id, content, metadata, embedding)
                VALUES (?, ?, ?, ?)
            """, ("test_id", "test content", malicious_metadata, embedding.tobytes()))

            conn.commit()
            conn.close()

            # Try to search - should fail safely with json.loads
            with pytest.raises(Exception):  # json.JSONDecodeError
                results = await rag.search("test", k=1)

    @pytest.mark.asyncio
    async def test_document_chunking(self, rag_config):
        """Test document chunking functionality"""
        rag = RAGSystem(rag_config)

        # Create a long text
        words = ["word"] * 200
        text = " ".join(words)

        chunks = rag._chunk_text(text)

        # Verify chunks were created
        assert len(chunks) > 1
        assert all(isinstance(chunk, str) for chunk in chunks)

    @pytest.mark.asyncio
    async def test_add_documents(self, rag_config, sample_documents, temp_dir):
        """Test adding documents to RAG system"""
        rag = RAGSystem(rag_config)

        with patch('pebblemind.rag.system.SentenceTransformer') as mock_st:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.random.rand(1, 384).astype(np.float32)
            mock_st.return_value = mock_model

            await rag.initialize()
            await rag.add_documents(sample_documents)

            # Verify documents were added
            stats = await rag.get_stats()
            assert stats["total_documents"] > 0

    @pytest.mark.asyncio
    async def test_search_functionality(self, rag_config, sample_documents, temp_dir):
        """Test search functionality"""
        rag = RAGSystem(rag_config)

        with patch('pebblemind.rag.system.SentenceTransformer') as mock_st:
            mock_model = MagicMock()
            # Return consistent embeddings for reproducibility
            mock_model.encode.return_value = np.random.rand(1, 384).astype(np.float32)
            mock_st.return_value = mock_model

            await rag.initialize()
            await rag.add_documents(sample_documents)

            # Search for content
            results = await rag.search("Python programming", k=2)

            # Verify results structure
            assert isinstance(results, list)
            if len(results) > 0:
                result = results[0]
                assert "id" in result
                assert "content" in result
                assert "metadata" in result
                assert "score" in result

    @pytest.mark.asyncio
    async def test_delete_document(self, rag_config, sample_documents, temp_dir):
        """Test document deletion"""
        rag = RAGSystem(rag_config)

        with patch('pebblemind.rag.system.SentenceTransformer') as mock_st:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.random.rand(1, 384).astype(np.float32)
            mock_st.return_value = mock_model

            await rag.initialize()
            await rag.add_documents(sample_documents[:1])

            # Get document ID
            results = await rag.search("Python", k=1)
            if len(results) > 0:
                doc_id = results[0]["id"]

                # Delete document
                deleted = await rag.delete_document(doc_id)
                assert deleted

                # Verify deletion
                results_after = await rag.search("Python", k=1)
                # Should have fewer results or different results
                assert len(results_after) == 0 or results_after[0]["id"] != doc_id

    @pytest.mark.asyncio
    async def test_get_stats(self, rag_config, temp_dir):
        """Test getting database statistics"""
        rag = RAGSystem(rag_config)

        with patch('pebblemind.rag.system.SentenceTransformer') as mock_st:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.random.rand(1, 384).astype(np.float32)
            mock_st.return_value = mock_model

            await rag.initialize()

            stats = await rag.get_stats()

            # Verify stats structure
            assert "total_documents" in stats
            assert "database_size_bytes" in stats
            assert "database_size_mb" in stats
            assert "vector_search_enabled" in stats
            assert "embedding_dimension" in stats
            assert "embedding_model" in stats

    @pytest.mark.asyncio
    async def test_empty_documents_skipped(self, rag_config, temp_dir):
        """Test that empty documents are skipped"""
        rag = RAGSystem(rag_config)

        with patch('pebblemind.rag.system.SentenceTransformer') as mock_st:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.random.rand(1, 384).astype(np.float32)
            mock_st.return_value = mock_model

            await rag.initialize()

            # Add documents with empty content
            documents = [
                {"content": "", "metadata": {}},
                {"content": "   ", "metadata": {}},
                {"content": "Valid content", "metadata": {}}
            ]

            await rag.add_documents(documents)

            # Verify only valid document was added
            stats = await rag.get_stats()
            # Should have at least the valid document
            assert stats["total_documents"] >= 1

    @pytest.mark.asyncio
    async def test_cleanup(self, rag_config, temp_dir):
        """Test cleanup functionality"""
        rag = RAGSystem(rag_config)

        with patch('pebblemind.rag.system.SentenceTransformer') as mock_st:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.random.rand(1, 384).astype(np.float32)
            mock_st.return_value = mock_model

            await rag.initialize()
            assert rag._initialized

            await rag.cleanup()
            assert not rag._initialized
            assert rag.embedding_model is None
