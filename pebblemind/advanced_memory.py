"""Advanced Long-Term Memory System for PebbleMind"""

import asyncio
import sqlite3
import json
import hashlib
import time
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import pickle


@dataclass
class MemoryEntry:
    """Represents a single memory entry with metadata"""
    id: str
    content: str
    memory_type: str  # episodic, semantic, procedural, factual
    timestamp: float
    importance: float = 1.0  # 0.0 to 1.0, how important is this memory
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


class LongTermMemory:
    """Advanced long-term memory system for PebbleMind"""
    
    def __init__(self, db_path: str = "./data/longterm_memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database for long-term memory storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                timestamp REAL NOT NULL,
                importance REAL DEFAULT 1.0,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                embedding_vector BLOB,
                accessed_count INTEGER DEFAULT 0,
                last_accessed REAL
            )
        """)
        
        # Create indexes for faster queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_type_timestamp ON memories(memory_type, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags ON memories(tags)")
        
        conn.commit()
        conn.close()
    
    async def store_memory(self, entry: MemoryEntry) -> bool:
        """Store a memory entry in the long-term memory system"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert tags and metadata to JSON strings
            tags_json = json.dumps(entry.tags)
            metadata_json = json.dumps(entry.metadata)
            
            cursor.execute("""
                INSERT OR REPLACE INTO memories 
                (id, content, memory_type, timestamp, importance, tags, metadata, accessed_count, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            """, (
                entry.id, entry.content, entry.memory_type, entry.timestamp,
                entry.importance, tags_json, metadata_json, entry.timestamp
            ))
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            print(f"Error storing memory: {e}")
            return False
    
    async def retrieve_memories(self, 
                              query: str = "",
                              memory_type: Optional[str] = None,
                              tags: Optional[List[str]] = None,
                              limit: int = 10,
                              importance_threshold: float = 0.0) -> List[MemoryEntry]:
        """Retrieve relevant memories based on query and filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build SQL query
        sql = "SELECT id, content, memory_type, timestamp, importance, tags, metadata FROM memories WHERE 1=1"
        params = []
        
        if query:
            sql += " AND content LIKE ?"
            params.append(f"%{query}%")
        
        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type)
        
        if tags:
            # Search for memories containing any of the specified tags
            # Use parameterized queries to prevent SQL injection
            for tag in tags:
                sql += " AND tags LIKE ?"
                params.append(f"%{tag}%")
        
        if importance_threshold > 0:
            sql += " AND importance >= ?"
            params.append(importance_threshold)
        
        sql += " ORDER BY importance DESC, timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        memories = []
        for row in rows:
            id, content, memory_type, timestamp, importance, tags_json, metadata_json = row
            tags = json.loads(tags_json)
            metadata = json.loads(metadata_json)
            
            memory = MemoryEntry(
                id=id,
                content=content,
                memory_type=memory_type,
                timestamp=timestamp,
                importance=importance,
                tags=tags,
                metadata=metadata
            )
            memories.append(memory)
        
        return memories
    
    async def update_memory_access(self, memory_id: str):
        """Update the access count and timestamp for a memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE memories 
            SET accessed_count = accessed_count + 1, last_accessed = ?
            WHERE id = ?
        """, (time.time(), memory_id))
        
        conn.commit()
        conn.close()
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory system"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM memories")
        total_memories = cursor.fetchone()[0]
        
        # Get count by type
        cursor.execute("SELECT memory_type, COUNT(*) FROM memories GROUP BY memory_type")
        type_counts = dict(cursor.fetchall())
        
        # Get average importance
        cursor.execute("SELECT AVG(importance) FROM memories")
        avg_importance = cursor.fetchone()[0] or 0.0
        
        # Get oldest and newest memories
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM memories")
        min_time, max_time = cursor.fetchone()
        
        conn.close()
        
        return {
            "total_memories": total_memories,
            "memories_by_type": type_counts,
            "average_importance": avg_importance,
            "oldest_memory": datetime.fromtimestamp(min_time) if min_time else None,
            "newest_memory": datetime.fromtimestamp(max_time) if max_time else None,
            "database_size_mb": self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0
        }
    
    async def consolidate_memories(self, 
                                 consolidation_period: int = 7) -> int:
        """
        Consolidate related memories that occurred within the specified period (days)
        This helps reduce memory fragmentation and improves retrieval
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find similar memories based on content that were created within the consolidation period
        cutoff_time = time.time() - (consolidation_period * 24 * 60 * 60)  # Convert days to seconds
        
        # Simple consolidation: group memories with similar content within time period
        cursor.execute("""
            SELECT id, content, memory_type, timestamp, importance, tags, metadata
            FROM memories 
            WHERE timestamp > ?
            ORDER BY memory_type, timestamp
        """, (cutoff_time,))
        
        rows = cursor.fetchall()
        conn.close()
        
        consolidated_count = 0
        # In a real implementation, we would look for semantically similar memories
        # and potentially merge them, but for efficiency on lightweight devices,
        # we'll just return the count of memories that could be consolidated
        
        for i in range(len(rows) - 1):
            # Simple similarity check - if two memories have overlapping tags
            tags1 = set(json.loads(rows[i][5]))
            tags2 = set(json.loads(rows[i+1][5]))
            
            if tags1 & tags2:  # If there's overlap in tags
                consolidated_count += 1

        return consolidated_count
    
    async def forget_memories(self, 
                            importance_threshold: float = 0.2,
                            age_threshold_days: int = 30,
                            max_to_forget: int = 10) -> int:
        """
        Implement forgetting mechanism to manage memory space
        Removes low-importance memories that are older than the threshold
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate cutoff time
        cutoff_time = time.time() - (age_threshold_days * 24 * 60 * 60)
        
        # Select memories to forget: low importance, old, and less frequently accessed
        cursor.execute("""
            SELECT id FROM memories 
            WHERE importance < ? 
            AND timestamp < ?
            ORDER BY importance ASC, accessed_count ASC, timestamp ASC
            LIMIT ?
        """, (importance_threshold, cutoff_time, max_to_forget))
        
        memories_to_forget = cursor.fetchall()
        
        if memories_to_forget:
            memory_ids = [row[0] for row in memories_to_forget]
            placeholders = ','.join(['?' for _ in memory_ids])
            cursor.execute(f"DELETE FROM memories WHERE id IN ({placeholders})", memory_ids)
            conn.commit()
        
        conn.close()
        return len(memories_to_forget)
    
    async def tag_memory(self, memory_id: str, tags: List[str]) -> bool:
        """Add tags to an existing memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get existing memory
        cursor.execute("SELECT tags FROM memories WHERE id = ?", (memory_id,))
        result = cursor.fetchone()
        
        if result is None:
            conn.close()
            return False
        
        existing_tags = json.loads(result[0])
        updated_tags = list(set(existing_tags + tags))  # Combine and deduplicate
        
        cursor.execute(
            "UPDATE memories SET tags = ? WHERE id = ?",
            (json.dumps(updated_tags), memory_id)
        )
        
        conn.commit()
        conn.close()
        return True


class EnhancedMemoryManager:
    """Manager class that integrates long-term memory with the existing PebbleMind system"""
    
    def __init__(self, config_path: str = "./data/longterm_memory.db"):
        self.long_term_memory = LongTermMemory(config_path)
        
        # Memory types for different purposes
        self.memory_types = {
            "episodic": "Personal experiences and events",
            "semantic": "Facts and concepts",
            "procedural": "How-to information and procedures",
            "factual": "General facts and knowledge"
        }
    
    async def store_conversation_memory(self, 
                                      user_input: str, 
                                      ai_response: str, 
                                      context: str = "",
                                      importance: float = 0.5) -> bool:
        """Store a conversation turn as episodic memory"""
        # Create episodic memory for the user input
        user_memory_id = hashlib.md5(f"{user_input}{time.time()}".encode()).hexdigest()
        user_entry = MemoryEntry(
            id=user_memory_id,
            content=user_input,
            memory_type="episodic",
            timestamp=time.time(),
            importance=importance,
            tags=["conversation", "user_input"],
            metadata={"response_id": hashlib.md5(ai_response.encode()).hexdigest()}
        )
        
        # Create episodic memory for the AI response
        ai_memory_id = hashlib.md5(f"{ai_response}{time.time()}".encode()).hexdigest()
        ai_entry = MemoryEntry(
            id=ai_memory_id,
            content=ai_response,
            memory_type="episodic",
            timestamp=time.time(),
            importance=importance,
            tags=["conversation", "ai_response"],
            metadata={"input_id": user_memory_id}
        )
        
        # Store both memories
        user_saved = await self.long_term_memory.store_memory(user_entry)
        ai_saved = await self.long_term_memory.store_memory(ai_entry)
        
        return user_saved and ai_saved
    
    async def store_factual_memory(self, 
                                 fact: str, 
                                 importance: float = 0.8,
                                 tags: List[str] = None) -> bool:
        """Store a fact in semantic memory"""
        if tags is None:
            tags = ["fact"]
        
        fact_id = hashlib.md5(f"{fact}{time.time()}".encode()).hexdigest()
        fact_entry = MemoryEntry(
            id=fact_id,
            content=fact,
            memory_type="factual",
            timestamp=time.time(),
            importance=importance,
            tags=tags,
            metadata={"category": "fact"}
        )
        
        return await self.long_term_memory.store_memory(fact_entry)
    
    async def retrieve_relevant_context(self, 
                                     query: str, 
                                     max_memories: int = 5,
                                     include_types: List[str] = None) -> List[str]:
        """Retrieve relevant memories to provide as context for LLM"""
        if include_types is None:
            include_types = ["episodic", "semantic", "factual"]
        
        # Retrieve relevant memories
        memories = await self.long_term_memory.retrieve_memories(
            query=query,
            memory_type=None,
            limit=max_memories
        )
        
        # Filter by requested types
        filtered_memories = [
            mem for mem in memories 
            if mem.memory_type in include_types
        ]
        
        # Update access counts
        for mem in filtered_memories:
            await self.long_term_memory.update_memory_access(mem.id)
        
        # Return content as context strings
        return [mem.content for mem in filtered_memories]
    
    async def get_memory_summary(self) -> str:
        """Get a human-readable summary of the memory system"""
        stats = await self.long_term_memory.get_memory_stats()
        
        summary_parts = [
            f"Total Memories: {stats['total_memories']}",
            f"Average Importance: {stats['average_importance']:.2f}",
        ]
        
        if stats['memories_by_type']:
            type_info = ", ".join([f"{mtype}: {count}" for mtype, count in stats['memories_by_type'].items()])
            summary_parts.append(f"By Type: {type_info}")
        
        if stats['oldest_memory']:
            summary_parts.append(f"Oldest: {stats['oldest_memory'].strftime('%Y-%m-%d')}")
        
        if stats['newest_memory']:
            summary_parts.append(f"Newest: {stats['newest_memory'].strftime('%Y-%m-%d')}")
        
        summary_parts.append(f"DB Size: {stats['database_size_mb']:.2f} MB")
        
        return " | ".join(summary_parts)