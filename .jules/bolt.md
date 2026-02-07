## 2025-05-15 - Optimized RAG System with Connection Pooling
**Learning:** Frequent opening and closing of SQLite connections, especially when loading extensions like `sqlite-vec`, adds significant overhead (ms per request).
**Action:** Integrated `SQLiteConnectionPool` to keep connections "hot". Disabled per-acquisition health checks for local SQLite to achieve a 64% speedup.
