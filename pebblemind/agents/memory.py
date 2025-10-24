import time
from dataclasses import dataclass
from typing import List


@dataclass
class MemoryRecord:
    """A single memory entry."""

    timestamp: float
    role: str
    content: str


class AgentMemory:
    """Simple in-memory episodic memory store."""

    def __init__(self) -> None:
        self._entries: List[MemoryRecord] = []

    async def add(self, role: str, content: str) -> None:
        """Add a memory entry."""
        self._entries.append(MemoryRecord(time.time(), role, content))

    async def get_recent(self, limit: int = 50) -> List[MemoryRecord]:
        """Return the most recent memory entries."""
        return self._entries[-limit:]

    async def clear(self) -> None:
        """Clear all memory entries."""
        self._entries.clear()
