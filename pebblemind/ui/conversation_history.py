"""Conversation history management with search and resume capabilities"""

import asyncio
import json
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Chat message"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str
    metadata: Dict[str, Any] = None


@dataclass
class Conversation:
    """Conversation session"""
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[Message]
    metadata: Dict[str, Any] = None


class ConversationHistory:
    """
    Conversation history manager with persistence and search.

    Features:
    - Save and load conversations
    - Search by content or metadata
    - Resume previous conversations
    - Export/import conversations
    - Conversation statistics
    """

    def __init__(self, db_path: Path):
        """
        Initialize conversation history

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._initialized = False

    async def initialize(self):
        """Initialize database"""
        if self._initialized:
            return

        # Create database directory
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect to database
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        # Create tables
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT
            )
        """)

        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for search
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_updated
            ON conversations(updated_at DESC)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation
            ON messages(conversation_id)
        """)

        self._conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                conversation_id,
                content,
                content='messages',
                content_rowid='id'
            )
        """)

        # Triggers to keep FTS table in sync
        self._conn.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
                INSERT INTO messages_fts(rowid, conversation_id, content)
                VALUES (new.id, new.conversation_id, new.content);
            END
        """)

        self._conn.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
                DELETE FROM messages_fts WHERE rowid = old.id;
            END
        """)

        self._conn.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
                UPDATE messages_fts SET content = new.content
                WHERE rowid = new.id;
            END
        """)

        self._conn.commit()
        self._initialized = True
        logger.info("Conversation history initialized")

    async def create_conversation(
        self,
        title: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create new conversation

        Args:
            title: Conversation title
            metadata: Optional metadata

        Returns:
            Conversation ID
        """
        import uuid
        conversation_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        self._conn.execute(
            """
            INSERT INTO conversations (id, title, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                title,
                now,
                now,
                json.dumps(metadata) if metadata else None
            )
        )
        self._conn.commit()

        logger.debug(f"Created conversation: {conversation_id}")
        return conversation_id

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add message to conversation

        Args:
            conversation_id: Conversation ID
            role: Message role (user/assistant)
            content: Message content
            metadata: Optional metadata
        """
        timestamp = datetime.now().isoformat()

        self._conn.execute(
            """
            INSERT INTO messages (conversation_id, role, content, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                role,
                content,
                timestamp,
                json.dumps(metadata) if metadata else None
            )
        )

        # Update conversation timestamp
        self._conn.execute(
            """
            UPDATE conversations SET updated_at = ? WHERE id = ?
            """,
            (timestamp, conversation_id)
        )

        self._conn.commit()

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get conversation by ID

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation object or None
        """
        # Get conversation
        row = self._conn.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (conversation_id,)
        ).fetchone()

        if not row:
            return None

        # Get messages
        message_rows = self._conn.execute(
            """
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
            """,
            (conversation_id,)
        ).fetchall()

        messages = [
            Message(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg["timestamp"],
                metadata=json.loads(msg["metadata"]) if msg["metadata"] else None
            )
            for msg in message_rows
        ]

        return Conversation(
            id=row["id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            messages=messages,
            metadata=json.loads(row["metadata"]) if row["metadata"] else None
        )

    async def list_conversations(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List recent conversations

        Args:
            limit: Maximum conversations to return
            offset: Offset for pagination

        Returns:
            List of conversation summaries
        """
        rows = self._conn.execute(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            GROUP BY c.id
            ORDER BY c.updated_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        ).fetchall()

        return [
            {
                "id": row["id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "message_count": row["message_count"]
            }
            for row in rows
        ]

    async def search_conversations(
        self,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search conversations by content

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching conversations
        """
        rows = self._conn.execute(
            """
            SELECT DISTINCT c.id, c.title, c.created_at, c.updated_at,
                   snippet(messages_fts, 1, '<mark>', '</mark>', '...', 50) as snippet
            FROM conversations c
            JOIN messages_fts ON c.id = messages_fts.conversation_id
            WHERE messages_fts MATCH ?
            ORDER BY c.updated_at DESC
            LIMIT ?
            """,
            (query, limit)
        ).fetchall()

        return [
            {
                "id": row["id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "snippet": row["snippet"]
            }
            for row in rows
        ]

    async def delete_conversation(self, conversation_id: str):
        """Delete conversation"""
        self._conn.execute(
            "DELETE FROM conversations WHERE id = ?",
            (conversation_id,)
        )
        self._conn.commit()
        logger.debug(f"Deleted conversation: {conversation_id}")

    async def export_conversation(
        self,
        conversation_id: str,
        output_path: Path
    ):
        """
        Export conversation to JSON

        Args:
            conversation_id: Conversation ID
            output_path: Output file path
        """
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation not found: {conversation_id}")

        with open(output_path, 'w') as f:
            json.dump(asdict(conversation), f, indent=2)

        logger.info(f"Exported conversation to {output_path}")

    async def import_conversation(self, input_path: Path) -> str:
        """
        Import conversation from JSON

        Args:
            input_path: Input file path

        Returns:
            Imported conversation ID
        """
        with open(input_path, 'r') as f:
            data = json.load(f)

        # Create conversation
        conversation_id = await self.create_conversation(
            title=data["title"],
            metadata=data.get("metadata")
        )

        # Add messages
        for msg_data in data["messages"]:
            await self.add_message(
                conversation_id,
                msg_data["role"],
                msg_data["content"],
                msg_data.get("metadata")
            )

        logger.info(f"Imported conversation from {input_path}")
        return conversation_id

    async def get_stats(self) -> Dict[str, Any]:
        """Get conversation statistics"""
        stats = self._conn.execute("""
            SELECT
                COUNT(DISTINCT c.id) as total_conversations,
                COUNT(m.id) as total_messages,
                AVG(msg_count) as avg_messages_per_conversation
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            LEFT JOIN (
                SELECT conversation_id, COUNT(*) as msg_count
                FROM messages
                GROUP BY conversation_id
            ) counts ON c.id = counts.conversation_id
        """).fetchone()

        return dict(stats)

    async def close(self):
        """Close database connection"""
        if self._conn:
            self._conn.close()
            self._conn = None
            self._initialized = False
