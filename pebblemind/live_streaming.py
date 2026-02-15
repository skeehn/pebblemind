"""Live Streaming System for Real-Time Applications

Provides:
- WebSocket streaming for bi-directional communication
- Server-Sent Events (SSE) for server-to-client streaming
- Real-time audio streaming
- Live transcription
- Stream multiplexing
- Low-latency buffering
"""

import asyncio
import logging
import json
import time
from typing import AsyncIterator, Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
from datetime import datetime
import queue
import threading

logger = logging.getLogger(__name__)


@dataclass
class StreamChunk:
    """A chunk of streamed data"""
    content: str
    chunk_id: int
    timestamp: float
    metadata: Dict[str, Any] = None
    is_final: bool = False


@dataclass
class StreamMetrics:
    """Metrics for stream performance"""
    total_chunks: int = 0
    total_bytes: int = 0
    start_time: float = 0
    end_time: float = 0
    avg_chunk_latency_ms: float = 0
    chunks_per_second: float = 0


class StreamBuffer:
    """Low-latency buffer for streaming"""

    def __init__(self, max_size: int = 1000, chunk_size: int = 50):
        self.max_size = max_size
        self.chunk_size = chunk_size
        self.buffer: List[str] = []
        self.chunk_id = 0

    def add(self, text: str) -> Optional[StreamChunk]:
        """
        Add text to buffer and return chunk if ready

        Returns:
            StreamChunk if buffer is full enough, None otherwise
        """
        self.buffer.append(text)

        # Check if we have enough for a chunk
        total_length = sum(len(s) for s in self.buffer)

        if total_length >= self.chunk_size or len(self.buffer) >= self.max_size:
            return self.flush()

        return None

    def flush(self) -> Optional[StreamChunk]:
        """Flush buffer and return chunk"""
        if not self.buffer:
            return None

        content = "".join(self.buffer)
        chunk = StreamChunk(
            content=content,
            chunk_id=self.chunk_id,
            timestamp=time.time()
        )

        self.buffer.clear()
        self.chunk_id += 1

        return chunk


class LiveStreamManager:
    """Manages live streaming sessions"""

    def __init__(self):
        self.active_streams: Dict[str, asyncio.Queue] = {}
        self.stream_metrics: Dict[str, StreamMetrics] = {}

    def create_stream(self, stream_id: str) -> asyncio.Queue:
        """Create a new stream"""
        queue = asyncio.Queue(maxsize=100)
        self.active_streams[stream_id] = queue
        self.stream_metrics[stream_id] = StreamMetrics(start_time=time.time())
        return queue

    def close_stream(self, stream_id: str):
        """Close and cleanup stream"""
        if stream_id in self.active_streams:
            del self.active_streams[stream_id]
        if stream_id in self.stream_metrics:
            metrics = self.stream_metrics[stream_id]
            metrics.end_time = time.time()

    async def send_chunk(self, stream_id: str, chunk: StreamChunk):
        """Send chunk to stream"""
        if stream_id in self.active_streams:
            queue = self.active_streams[stream_id]
            await queue.put(chunk)

            # Update metrics
            metrics = self.stream_metrics[stream_id]
            metrics.total_chunks += 1
            metrics.total_bytes += len(chunk.content)

    async def receive_chunk(self, stream_id: str, timeout: float = 1.0) -> Optional[StreamChunk]:
        """Receive chunk from stream"""
        if stream_id not in self.active_streams:
            return None

        queue = self.active_streams[stream_id]
        try:
            chunk = await asyncio.wait_for(queue.get(), timeout=timeout)
            return chunk
        except asyncio.TimeoutError:
            return None

    def get_metrics(self, stream_id: str) -> Optional[StreamMetrics]:
        """Get stream metrics"""
        return self.stream_metrics.get(stream_id)


class StreamingResponse:
    """Iterator for streaming responses"""

    def __init__(
        self,
        generator: AsyncIterator[str],
        chunk_size: int = 50,
        format: str = "text"
    ):
        self.generator = generator
        self.chunk_size = chunk_size
        self.format = format
        self.buffer = StreamBuffer(chunk_size=chunk_size)
        self.metrics = StreamMetrics(start_time=time.time())

    async def __aiter__(self):
        """Async iteration support"""
        async for text in self.generator:
            # Add to buffer
            chunk = self.buffer.add(text)

            # If chunk ready, yield it
            if chunk:
                self.metrics.total_chunks += 1
                self.metrics.total_bytes += len(chunk.content)
                yield chunk

        # Flush remaining buffer
        chunk = self.buffer.flush()
        if chunk:
            chunk.is_final = True
            self.metrics.end_time = time.time()
            self.metrics.total_chunks += 1
            self.metrics.total_bytes += len(chunk.content)
            yield chunk


class WebSocketStreamer:
    """WebSocket streaming handler"""

    def __init__(self):
        self.connections: Dict[str, Any] = {}

    async def handle_connection(
        self,
        websocket,
        client_id: str,
        message_handler: Callable
    ):
        """Handle WebSocket connection"""
        self.connections[client_id] = websocket

        try:
            # Send welcome message
            await websocket.send(json.dumps({
                'type': 'connected',
                'client_id': client_id,
                'timestamp': datetime.now().isoformat()
            }))

            # Handle messages
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)

                    # Process message
                    response = await message_handler(data)

                    # Stream response
                    if isinstance(response, AsyncIterator):
                        async for chunk in response:
                            await websocket.send(json.dumps({
                                'type': 'chunk',
                                'content': chunk.content if isinstance(chunk, StreamChunk) else chunk,
                                'timestamp': datetime.now().isoformat()
                            }))
                    else:
                        await websocket.send(json.dumps({
                            'type': 'response',
                            'content': response,
                            'timestamp': datetime.now().isoformat()
                        }))

                except Exception as e:
                    logger.error(f"Message handling error: {e}")
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'error': str(e)
                    }))

        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            if client_id in self.connections:
                del self.connections[client_id]

    async def broadcast(self, message: Dict[str, Any], exclude: Optional[List[str]] = None):
        """Broadcast message to all connected clients"""
        exclude = exclude or []

        for client_id, websocket in self.connections.items():
            if client_id not in exclude:
                try:
                    await websocket.send(json.dumps(message))
                except Exception as e:
                    logger.error(f"Broadcast error to {client_id}: {e}")


class SSEStreamer:
    """Server-Sent Events (SSE) streaming"""

    @staticmethod
    async def stream_events(generator: AsyncIterator[str]) -> AsyncIterator[str]:
        """
        Convert async generator to SSE format

        Yields SSE-formatted strings
        """
        async for chunk in generator:
            # Format as SSE
            if isinstance(chunk, StreamChunk):
                data = {
                    'content': chunk.content,
                    'chunk_id': chunk.chunk_id,
                    'is_final': chunk.is_final
                }
                sse_data = json.dumps(data)
            else:
                sse_data = json.dumps({'content': chunk})

            yield f"data: {sse_data}\n\n"

    @staticmethod
    async def stream_with_heartbeat(
        generator: AsyncIterator[str],
        heartbeat_interval: float = 15.0
    ) -> AsyncIterator[str]:
        """
        Stream with periodic heartbeat to keep connection alive

        Args:
            generator: Data generator
            heartbeat_interval: Seconds between heartbeats
        """
        last_heartbeat = time.time()

        async for item in generator:
            yield item

            # Send heartbeat if needed
            if time.time() - last_heartbeat > heartbeat_interval:
                yield f": heartbeat\n\n"
                last_heartbeat = time.time()


class AudioStreamer:
    """Real-time audio streaming"""

    def __init__(self, sample_rate: int = 16000, chunk_duration_ms: int = 100):
        self.sample_rate = sample_rate
        self.chunk_duration_ms = chunk_duration_ms
        self.chunk_size = int(sample_rate * chunk_duration_ms / 1000)
        self.buffer = queue.Queue(maxsize=10)

    async def stream_audio(self, audio_data: bytes) -> AsyncIterator[bytes]:
        """
        Stream audio data in chunks

        Args:
            audio_data: Complete audio data

        Yields:
            Audio chunks
        """
        total_length = len(audio_data)
        position = 0

        while position < total_length:
            chunk = audio_data[position:position + self.chunk_size]
            yield chunk
            position += self.chunk_size

            # Small delay for real-time feel
            await asyncio.sleep(self.chunk_duration_ms / 1000)

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        transcriber: Callable
    ) -> AsyncIterator[str]:
        """
        Transcribe streaming audio

        Args:
            audio_stream: Stream of audio chunks
            transcriber: Function to transcribe audio

        Yields:
            Transcribed text chunks
        """
        audio_buffer = bytearray()
        buffer_threshold = self.chunk_size * 5  # Buffer 5 chunks

        async for audio_chunk in audio_stream:
            audio_buffer.extend(audio_chunk)

            # Transcribe when buffer is full enough
            if len(audio_buffer) >= buffer_threshold:
                text = await transcriber(bytes(audio_buffer))
                if text:
                    yield text
                audio_buffer.clear()

        # Transcribe remaining buffer
        if audio_buffer:
            text = await transcriber(bytes(audio_buffer))
            if text:
                yield text


# Demo and examples
async def demo_streaming():
    """Demo streaming capabilities"""
    print("="*60)
    print("LIVE STREAMING DEMO")
    print("="*60 + "\n")

    # Mock text generator
    async def mock_text_generator():
        text = "This is a streaming response that comes in chunks. "
        words = text.split()
        for word in words:
            yield word + " "
            await asyncio.sleep(0.1)

    # Demo streaming response
    print("📡 Streaming Text Response:")
    print("  ", end="", flush=True)

    stream = StreamingResponse(mock_text_generator(), chunk_size=20)
    async for chunk in stream:
        print(chunk.content, end="", flush=True)

    print("\n")

    # Metrics
    metrics = stream.metrics
    duration = metrics.end_time - metrics.start_time if metrics.end_time else 0
    print(f"Streaming Metrics:")
    print(f"  Total chunks: {metrics.total_chunks}")
    print(f"  Total bytes: {metrics.total_bytes}")
    print(f"  Duration: {duration:.2f}s")
    print()

    # Demo SSE
    print("📨 SSE Format Example:")
    async for sse_event in SSEStreamer.stream_events(mock_text_generator()):
        print(f"  {sse_event.strip()}")
        break  # Just show first one


if __name__ == "__main__":
    asyncio.run(demo_streaming())
