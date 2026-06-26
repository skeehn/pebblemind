"""Connection pooling for efficient resource management"""

import asyncio
import time
from typing import Optional, Dict, Any, Callable, Generic, TypeVar
from dataclasses import dataclass
from datetime import datetime
import logging
import sqlite3
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class PooledConnection(Generic[T]):
    """Wrapper for pooled connection"""
    connection: T
    created_at: float
    last_used: float
    use_count: int = 0
    in_use: bool = False


class ConnectionPool(Generic[T]):
    """
    Generic connection pool with health checks and auto-recovery.

    Features:
    - Min/max pool sizing
    - Connection health checks
    - Auto-reconnection
    - Connection reuse tracking
    - Timeout handling
    - Statistics
    """

    def __init__(
        self,
        create_connection: Callable[[], T],
        close_connection: Callable[[T], None],
        min_size: int = 2,
        max_size: int = 10,
        max_idle_time: float = 300,  # 5 minutes
        max_lifetime: float = 3600,  # 1 hour
        health_check: Optional[Callable[[T], bool]] = None,
        enable_stats: bool = True
    ):
        """
        Initialize connection pool

        Args:
            create_connection: Function to create new connection
            close_connection: Function to close connection
            min_size: Minimum pool size
            max_size: Maximum pool size
            max_idle_time: Maximum idle time before closing (seconds)
            max_lifetime: Maximum connection lifetime (seconds)
            health_check: Optional function to check connection health
            enable_stats: Enable statistics tracking
        """
        self.create_connection = create_connection
        self.close_connection = close_connection
        self.min_size = min_size
        self.max_size = max_size
        self.max_idle_time = max_idle_time
        self.max_lifetime = max_lifetime
        self.health_check = health_check
        self.enable_stats = enable_stats

        # Pool state
        self._pool: Dict[int, PooledConnection[T]] = {}
        self._available: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._next_id = 0

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # Statistics
        self._stats = {
            "connections_created": 0,
            "connections_closed": 0,
            "connections_reused": 0,
            "health_check_failures": 0,
            "wait_timeouts": 0,
            "current_size": 0,
            "current_available": 0,
            "current_in_use": 0,
        }

    async def start(self):
        """Initialize pool with minimum connections"""
        if self._running:
            return

        self._running = True

        # Create initial connections
        for _ in range(self.min_size):
            await self._create_connection()

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info(f"Connection pool started (min={self.min_size}, max={self.max_size})")

    async def stop(self):
        """Close all connections and stop cleanup"""
        self._running = False

        # Stop cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        # Close all connections
        async with self._lock:
            for conn_id, pooled in list(self._pool.items()):
                await self._close_connection(conn_id, pooled)

        logger.info("Connection pool stopped")

    async def _create_connection(self) -> int:
        """Create new connection and add to pool"""
        async with self._lock:
            if len(self._pool) >= self.max_size:
                raise RuntimeError("Connection pool is full")

            conn_id = self._next_id
            self._next_id += 1

            try:
                # Create connection (wrap sync function)
                loop = asyncio.get_event_loop()
                connection = await loop.run_in_executor(None, self.create_connection)

                # Add to pool
                now = time.monotonic()
                pooled = PooledConnection(
                    connection=connection,
                    created_at=now,
                    last_used=now,
                    in_use=False
                )
                self._pool[conn_id] = pooled

                # Mark as available
                await self._available.put(conn_id)

                if self.enable_stats:
                    self._stats["connections_created"] += 1
                    self._stats["current_size"] += 1
                    self._stats["current_available"] += 1

                logger.debug(f"Created connection {conn_id}")
                return conn_id

            except Exception as e:
                logger.error(f"Failed to create connection: {e}")
                raise

    async def _close_connection(self, conn_id: int, pooled: PooledConnection[T]):
        """Close and remove connection from pool"""
        try:
            # Close connection (wrap sync function)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.close_connection, pooled.connection)

            # Remove from pool
            if conn_id in self._pool:
                del self._pool[conn_id]

            if self.enable_stats:
                self._stats["connections_closed"] += 1
                self._stats["current_size"] -= 1
                if not pooled.in_use:
                    self._stats["current_available"] -= 1

            logger.debug(f"Closed connection {conn_id}")

        except Exception as e:
            logger.error(f"Error closing connection {conn_id}: {e}")

    async def _check_health(self, pooled: PooledConnection[T]) -> bool:
        """Check if connection is healthy"""
        if not self.health_check:
            return True

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.health_check, pooled.connection)
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    @asynccontextmanager
    async def acquire(self, timeout: Optional[float] = 10.0):
        """
        Acquire connection from pool

        Args:
            timeout: Maximum time to wait for connection (seconds)

        Yields:
            Connection object

        Raises:
            TimeoutError: If timeout is exceeded
        """
        conn_id = None
        pooled = None
        start_time = time.monotonic()

        try:
            while True:
                # Calculate remaining timeout
                current_time = time.monotonic()
                remaining = timeout - (current_time - start_time) if timeout else None
                if timeout and remaining <= 0:
                    self._stats["wait_timeouts"] += 1
                    raise TimeoutError("Timeout waiting for connection")

                # Wait for available connection
                try:
                    conn_id = await asyncio.wait_for(
                        self._available.get(),
                        timeout=remaining
                    )
                except asyncio.TimeoutError:
                    self._stats["wait_timeouts"] += 1
                    raise TimeoutError("Timeout waiting for connection")

                # Get connection
                async with self._lock:
                    pooled = self._pool.get(conn_id)
                    if not pooled:
                        # Connection was closed, try again
                        continue

                    # Check health
                    if not await self._check_health(pooled):
                        # Connection unhealthy, recreate
                        await self._close_connection(conn_id, pooled)
                        self._stats["health_check_failures"] += 1
                        conn_id = await self._create_connection()
                        pooled = self._pool[conn_id]

                    # Mark as in use
                    pooled.in_use = True
                    pooled.use_count += 1
                    pooled.last_used = time.monotonic()

                    if self.enable_stats:
                        self._stats["current_available"] -= 1
                        self._stats["current_in_use"] += 1
                        self._stats["connections_reused"] += 1

                break

            # Yield connection
            yield pooled.connection

        finally:
            # Return to pool
            if conn_id is not None and pooled is not None:
                async with self._lock:
                    if conn_id in self._pool:
                        pooled.in_use = False
                        pooled.last_used = time.monotonic()
                        await self._available.put(conn_id)

                        if self.enable_stats:
                            self._stats["current_available"] += 1
                            self._stats["current_in_use"] -= 1

    async def _cleanup_loop(self):
        """Background cleanup of idle and old connections"""
        while self._running:
            try:
                await asyncio.sleep(30)  # Run every 30 seconds
                await self._cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup(self):
        """Remove idle or old connections"""
        now = time.monotonic()

        async with self._lock:
            to_close = []

            for conn_id, pooled in self._pool.items():
                if pooled.in_use:
                    continue

                # Check idle time
                idle_time = now - pooled.last_used
                if idle_time > self.max_idle_time and len(self._pool) > self.min_size:
                    to_close.append((conn_id, pooled))
                    continue

                # Check lifetime
                lifetime = now - pooled.created_at
                if lifetime > self.max_lifetime:
                    to_close.append((conn_id, pooled))
                    continue

            # Close connections
            for conn_id, pooled in to_close:
                await self._close_connection(conn_id, pooled)

            # Ensure minimum pool size
            while len(self._pool) < self.min_size:
                await self._create_connection()

        if to_close:
            logger.debug(f"Cleaned up {len(to_close)} connections")

    async def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        async with self._lock:
            return {
                **self._stats,
                "pool_size": len(self._pool),
            }


class SQLiteConnectionPool(ConnectionPool[sqlite3.Connection]):
    """Specialized pool for SQLite connections"""

    def __init__(self, database_path: str, **kwargs):
        """
        Initialize SQLite connection pool

        Args:
            database_path: Path to SQLite database
            **kwargs: Additional arguments for ConnectionPool
        """
        def create_conn():
            conn = sqlite3.connect(database_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn

        def close_conn(conn):
            conn.close()

        def health_check(conn):
            try:
                conn.execute("SELECT 1").fetchone()
                return True
            except Exception:
                return False

        super().__init__(
            create_connection=create_conn,
            close_connection=close_conn,
            health_check=health_check,
            **kwargs
        )
