import asyncio
import json
from typing import AsyncGenerator, Optional

from fastapi import Request, WebSocket, WebSocketDisconnect


async def sse_stream(
    generator: AsyncGenerator[str, None],
    model: str,
    request: Optional[Request] = None,
):
    """Convert a token generator to Server-Sent Events.

    Args:
        generator: Async generator yielding string tokens.
        model: Model name used for metadata in the stream.
        request: Optional Request object to detect client disconnects.
    """
    try:
        async for token in generator:
            data = {
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [
                    {"index": 0, "delta": {"content": token}, "finish_reason": None}
                ],
            }
            yield f"data: {json.dumps(data)}\n\n"
            # Allow cancellation if client disconnects
            if request and await request.is_disconnected():
                break
    except asyncio.CancelledError:
        # Gracefully exit on cancellation
        pass
    finally:
        final_data = {
            "object": "chat.completion.chunk",
            "model": model,
            "choices": [
                {"index": 0, "delta": {}, "finish_reason": "stop"}
            ],
        }
        yield f"data: {json.dumps(final_data)}\n\n"
        yield "data: [DONE]\n\n"


async def websocket_stream(
    websocket: WebSocket,
    generator: AsyncGenerator[str, None],
    stop_event: Optional[asyncio.Event] = None,
) -> None:
    """Stream tokens over a WebSocket connection.

    Args:
        websocket: Active WebSocket connection.
        generator: Async generator yielding string tokens.
        stop_event: Optional event to signal cancellation.
    """
    try:
        async for token in generator:
            await websocket.send_json({"token": token})
            # Backpressure/cancellation handling
            if stop_event and stop_event.is_set():
                break
    except WebSocketDisconnect:
        if stop_event:
            stop_event.set()
    except Exception as e:
        await websocket.send_json(
            {"error": {"message": str(e), "type": "internal_error"}}
        )
    finally:
        try:
            await websocket.send_json({"event": "done"})
        except WebSocketDisconnect:
            if stop_event:
                stop_event.set()
