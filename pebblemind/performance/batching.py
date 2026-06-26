"""Request batching system for efficient processing of multiple requests"""

import asyncio
import time
from typing import List, Callable, Any, Optional, Dict, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class BatchRequest(Generic[T]):
    """Individual request in a batch"""
    data: T
    future: asyncio.Future
    timestamp: float
    priority: int = 0


class RequestBatcher(Generic[T, R]):
    """
    Intelligent request batching system that groups requests for efficient processing.

    Features:
    - Automatic batching based on time window or size
    - Priority-based scheduling
    - Timeout handling
    - Concurrent batch processing
    - Performance metrics
    """

    def __init__(
        self,
        batch_processor: Callable[[List[T]], Any],
        max_batch_size: int = 32,
        max_wait_ms: int = 50,
        max_concurrent_batches: int = 4,
        enable_priority: bool = False
    ):
        """
        Initialize request batcher

        Args:
            batch_processor: Async function to process a batch of requests
            max_batch_size: Maximum requests per batch
            max_wait_ms: Maximum time to wait before processing batch (ms)
            max_concurrent_batches: Maximum concurrent batch processing
            enable_priority: Enable priority-based scheduling
        """
        self.batch_processor = batch_processor
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self.max_concurrent_batches = max_concurrent_batches
        self.enable_priority = enable_priority

        # Request queue
        self._queue: List[BatchRequest[T]] = []
        self._lock = asyncio.Lock()
        self._processing_semaphore = asyncio.Semaphore(max_concurrent_batches)

        # Background tasks
        self._batch_task: Optional[asyncio.Task] = None
        self._running = False

        # Statistics
        self._stats = {
            "total_requests": 0,
            "total_batches": 0,
            "total_items_processed": 0,
            "avg_batch_size": 0.0,
            "max_batch_size": 0,
            "timeouts": 0,
            "errors": 0,
        }

    async def start(self):
        """Start batch processing"""
        if self._running:
            return

        self._running = True
        self._batch_task = asyncio.create_task(self._batch_loop())
        logger.info(f"Request batcher started (max_batch={self.max_batch_size}, wait={self.max_wait_ms}ms)")

    async def stop(self):
        """Stop batch processing and wait for pending requests"""
        self._running = False

        # Process remaining requests
        if self._queue:
            await self._process_pending()

        # Cancel background task
        if self._batch_task:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass
            self._batch_task = None

        logger.info("Request batcher stopped")

    async def submit(
        self,
        data: T,
        priority: int = 0,
        timeout: Optional[float] = None
    ) -> R:
        """
        Submit request for batched processing

        Args:
            data: Request data
            priority: Request priority (higher = sooner)
            timeout: Timeout in seconds

        Returns:
            Processed result

        Raises:
            TimeoutError: If request times out
            Exception: If processing fails
        """
        if not self._running:
            await self.start()

        # Create request
        future = asyncio.Future()
        request = BatchRequest(
            data=data,
            future=future,
            timestamp=time.monotonic(),
            priority=priority if self.enable_priority else 0
        )

        # Add to queue
        async with self._lock:
            self._queue.append(request)
            self._stats["total_requests"] += 1

            # Sort by priority if enabled
            if self.enable_priority:
                self._queue.sort(key=lambda r: (-r.priority, r.timestamp))

            # Trigger immediate processing if batch is full
            if len(self._queue) >= self.max_batch_size:
                asyncio.create_task(self._process_batch())

        # Wait for result with timeout
        try:
            if timeout:
                result = await asyncio.wait_for(future, timeout=timeout)
            else:
                result = await future
            return result
        except asyncio.TimeoutError:
            self._stats["timeouts"] += 1
            raise TimeoutError(f"Request timed out after {timeout}s")

    async def _batch_loop(self):
        """Background loop to process batches periodically"""
        while self._running:
            try:
                # Wait for batch window
                await asyncio.sleep(self.max_wait_ms / 1000.0)

                # Process pending requests
                if self._queue:
                    await self._process_batch()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch loop: {e}")
                await asyncio.sleep(0.1)

    async def _process_batch(self):
        """Process a batch of requests"""
        async with self._lock:
            if not self._queue:
                return

            # Extract batch
            batch_size = min(len(self._queue), self.max_batch_size)
            batch = self._queue[:batch_size]
            self._queue = self._queue[batch_size:]

        if not batch:
            return

        # Process with concurrency limit
        async with self._processing_semaphore:
            try:
                # Extract data
                data_list = [req.data for req in batch]

                # Process batch
                results = await self.batch_processor(data_list)

                # Distribute results
                if len(results) != len(batch):
                    raise ValueError(
                        f"Batch processor returned {len(results)} results "
                        f"for {len(batch)} requests"
                    )

                for request, result in zip(batch, results):
                    if not request.future.done():
                        request.future.set_result(result)

                # Update stats
                self._stats["total_batches"] += 1
                self._stats["total_items_processed"] += len(batch)
                self._stats["max_batch_size"] = max(
                    self._stats["max_batch_size"],
                    len(batch)
                )
                self._stats["avg_batch_size"] = (
                    self._stats["total_items_processed"] /
                    self._stats["total_batches"]
                )

                logger.debug(f"Processed batch of {len(batch)} requests")

            except Exception as e:
                self._stats["errors"] += 1
                logger.error(f"Error processing batch: {e}")

                # Fail all requests in batch
                for request in batch:
                    if not request.future.done():
                        request.future.set_exception(e)

    async def _process_pending(self):
        """Process all pending requests"""
        while self._queue:
            await self._process_batch()

    async def get_stats(self) -> Dict[str, Any]:
        """Get batching statistics"""
        async with self._lock:
            queue_size = len(self._queue)

        return {
            **self._stats,
            "queue_size": queue_size,
            "running": self._running,
        }


class EmbeddingBatcher(RequestBatcher[str, List[float]]):
    """Specialized batcher for embedding requests"""

    def __init__(self, embedding_func: Callable, **kwargs):
        """
        Initialize embedding batcher

        Args:
            embedding_func: Function that takes list of strings and returns embeddings
            **kwargs: Additional arguments for RequestBatcher
        """
        super().__init__(
            batch_processor=embedding_func,
            max_batch_size=kwargs.get('max_batch_size', 32),
            max_wait_ms=kwargs.get('max_wait_ms', 50),
            **{k: v for k, v in kwargs.items() if k not in ['max_batch_size', 'max_wait_ms']}
        )


class InferenceBatcher(RequestBatcher[str, str]):
    """Specialized batcher for LLM inference requests"""

    def __init__(self, inference_func: Callable, **kwargs):
        """
        Initialize inference batcher

        Args:
            inference_func: Function that takes list of prompts and returns responses
            **kwargs: Additional arguments for RequestBatcher
        """
        super().__init__(
            batch_processor=inference_func,
            max_batch_size=kwargs.get('max_batch_size', 8),  # Smaller batches for LLM
            max_wait_ms=kwargs.get('max_wait_ms', 100),
            **{k: v for k, v in kwargs.items() if k not in ['max_batch_size', 'max_wait_ms']}
        )
