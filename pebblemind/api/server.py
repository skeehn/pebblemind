"""OpenAI-compatible API server for PebbleMind"""

import asyncio
import logging
import json
import time
from collections import defaultdict
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Request, Depends, WebSocket, WebSocketDisconnect, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

from ..core import PebbleMind
from ..core.streaming import sse_stream, websocket_stream
from ..config import APIConfig

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)

        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > minute_ago
        ]

        # Check rate limit
        if len(self.requests[client_id]) >= self.requests_per_minute:
            return False

        # Add current request
        self.requests[client_id].append(now)
        return True

    def get_retry_after(self, client_id: str) -> int:
        """Get seconds until rate limit resets"""
        if not self.requests[client_id]:
            return 0

        oldest_request = min(self.requests[client_id])
        retry_time = oldest_request + timedelta(minutes=1)
        return int((retry_time - datetime.now()).total_seconds())


rate_limiter = RateLimiter(requests_per_minute=60)


# OpenAI-compatible data models
class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the message author")
    content: str = Field(..., description="Content of the message")


class ChatCompletionRequest(BaseModel):
    model: str = Field(..., description="Model to use for completion")
    messages: List[ChatMessage] = Field(..., description="List of messages")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(0.7, description="Sampling temperature")
    top_p: Optional[float] = Field(0.9, description="Top-p sampling")
    top_k: Optional[int] = Field(40, description="Top-k sampling")
    stream: Optional[bool] = Field(False, description="Stream the response")
    stop: Optional[List[str]] = Field(None, description="Stop sequences")


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "pebblemind"


class ModelList(BaseModel):
    object: str = "list"
    data: List[ModelInfo]


class APIServer:
    """OpenAI-compatible API server"""

    def __init__(self, config: APIConfig, pebblemind: PebbleMind):
        """Initialize API server with configuration"""
        self.config = config
        self.pebblemind = pebblemind
        self.app = FastAPI(title="PebbleMind API", version="1.0.0")
        self.server = None
        self._setup_routes()
        self._setup_middleware()

    async def verify_api_key(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
        """Verify API key if authentication is enabled"""
        # Skip authentication if no API key is configured
        if not self.config.api_key:
            return True

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if credentials.credentials != self.config.api_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key"
            )

        return True

    async def check_rate_limit(self, request: Request) -> bool:
        """Check rate limit for the request"""
        # Use client IP as identifier
        client_id = request.client.host

        if not rate_limiter.is_allowed(client_id):
            retry_after = rate_limiter.get_retry_after(client_id)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(retry_after)}
            )

        return True

    def _setup_middleware(self):
        """Setup CORS and other middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routes(self):
        """Setup API routes"""

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}

        @self.app.get("/v1/models")
        async def list_models():
            """List available models (OpenAI-compatible)"""
            models = [
                ModelInfo(
                    id="pebblemind-chat",
                    created=int(time.time()),
                    owned_by="pebblemind"
                )
            ]
            return ModelList(data=models)

        @self.app.get("/v1/models/{model_id}")
        async def get_model(model_id: str):
            """Get model information"""
            if model_id == "pebblemind-chat":
                return ModelInfo(
                    id=model_id,
                    created=int(time.time()),
                    owned_by="pebblemind"
                )
            else:
                raise HTTPException(status_code=404, detail="Model not found")

        @self.app.post("/v1/chat/completions")
        async def create_chat_completion(
            request: ChatCompletionRequest,
            raw_request: Request,
            authenticated: bool = Depends(self.verify_api_key),
            rate_limited: bool = Depends(self.check_rate_limit)
        ):
            """Create chat completion (OpenAI-compatible)"""
            try:
                # Extract user message from the conversation
                user_message = ""
                system_prompt = None

                for msg in request.messages:
                    if msg.role == "user":
                        user_message = msg.content
                    elif msg.role == "system":
                        system_prompt = msg.content

                if not user_message:
                    raise HTTPException(status_code=400, detail="No user message found")

                # Prepare generation parameters
                gen_params = {}
                if request.max_tokens:
                    gen_params["max_tokens"] = request.max_tokens
                if request.temperature:
                    gen_params["temperature"] = request.temperature
                if request.top_p:
                    gen_params["top_p"] = request.top_p
                if request.top_k:
                    gen_params["top_k"] = request.top_k

                if request.stream:
                    # Streaming response
                    return StreamingResponse(
                        self._stream_chat_completion(
                            user_message,
                            system_prompt,
                            request.model,
                            raw_request,
                            **gen_params
                        ),
                        media_type="text/plain"
                    )
                else:
                    # Regular response
                    start_time = time.time()

                    response_text = await self.pebblemind.query(
                        user_message,
                        system_prompt=system_prompt,
                        **gen_params
                    )

                    end_time = time.time()

                    # Estimate token usage (rough approximation)
                    prompt_tokens = len(user_message.split()) * 1.3  # Rough token estimation
                    completion_tokens = len(response_text.split()) * 1.3

                    return ChatCompletionResponse(
                        id=f"chatcmpl-{int(time.time())}",
                        created=int(start_time),
                        model=request.model,
                        choices=[
                            ChatCompletionChoice(
                                index=0,
                                message=ChatMessage(role="assistant", content=response_text),
                                finish_reason="stop"
                            )
                        ],
                        usage=ChatCompletionUsage(
                            prompt_tokens=int(prompt_tokens),
                            completion_tokens=int(completion_tokens),
                            total_tokens=int(prompt_tokens + completion_tokens)
                        )
                    )

            except Exception as e:
                logger.error(f"Chat completion failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Internal server error occurred while processing your request"
                )

        @self.app.post("/v1/audio/transcriptions")
        async def create_transcription(
            request: Request,
            authenticated: bool = Depends(self.verify_api_key)
        ):
            """Transcribe audio to text (OpenAI-compatible)"""
            try:
                # Parse multipart form data
                form = await request.form()
                audio_file = form.get("file")
                model = form.get("model", "whisper-1")

                if not audio_file:
                    raise HTTPException(status_code=400, detail="No audio file provided")

                # Validate file type
                allowed_audio_types = {
                    "audio/wav", "audio/wave", "audio/x-wav",
                    "audio/mp3", "audio/mpeg",
                    "audio/ogg", "audio/flac"
                }

                content_type = audio_file.content_type
                if content_type not in allowed_audio_types:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid file type. Allowed types: {', '.join(allowed_audio_types)}"
                    )

                # Validate file size (max 25MB)
                MAX_FILE_SIZE = 25 * 1024 * 1024
                audio_data = await audio_file.read()

                if len(audio_data) > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail="File too large. Maximum size is 25MB"
                    )

                # Process with voice processor
                transcription = await self.pebblemind.voice_processor.speech_to_text(audio_data)

                return {
                    "text": transcription
                }

            except Exception as e:
                logger.error(f"Transcription failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Internal server error occurred during transcription"
                )

        @self.app.post("/v1/audio/speech")
        async def create_speech(
            request: Request,
            authenticated: bool = Depends(self.verify_api_key)
        ):
            """Generate speech from text (OpenAI-compatible)"""
            try:
                # Parse request body
                body = await request.json()
                text = body.get("input", "")
                model = body.get("model", "tts-1")
                voice = body.get("voice", "alloy")

                if not text:
                    raise HTTPException(status_code=400, detail="No text provided")

                # Generate speech
                audio_data = await self.pebblemind.voice_processor.text_to_speech(text)

                # Return audio data
                from fastapi.responses import Response
                return Response(
                    content=audio_data,
                    media_type="audio/wav",
                    headers={"Content-Disposition": "attachment; filename=speech.wav"}
                )

            except Exception as e:
                logger.error(f"Speech generation failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Internal server error occurred during speech generation"
                )

        @self.app.websocket("/ws/chat")
        async def websocket_chat(websocket: WebSocket):
            await websocket.accept()
            try:
                data = await websocket.receive_json()
                message = data.get("message", "")
                system_prompt = data.get("system_prompt")

                gen_params = {}
                for param in ["max_tokens", "temperature", "top_p", "top_k"]:
                    if param in data:
                        gen_params[param] = data[param]

                stop_event = asyncio.Event()

                async def cancel_listener():
                    try:
                        while True:
                            msg = await websocket.receive_json()
                            if msg.get("action") == "cancel":
                                stop_event.set()
                                break
                    except WebSocketDisconnect:
                        stop_event.set()

                listener = asyncio.create_task(cancel_listener())

                generator = self.pebblemind.llm_engine.generate_stream(
                    message,
                    system_prompt=system_prompt,
                    stop_event=stop_event,
                    **gen_params
                )

                await websocket_stream(websocket, generator, stop_event)
                listener.cancel()
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")


    async def _stream_chat_completion(
        self,
        message: str,
        system_prompt: Optional[str],
        model: str,
        raw_request: Request,
        **kwargs
    ):
        """Stream chat completion response"""
        stop_event = asyncio.Event()

        async def disconnect_watcher():
            if await raw_request.is_disconnected():
                stop_event.set()

        watcher_task = asyncio.create_task(disconnect_watcher())

        try:
            generator = self.pebblemind.llm_engine.generate_stream(
                message,
                system_prompt=system_prompt,
                stop_event=stop_event,
                **kwargs
            )
            async for chunk in sse_stream(generator, model, raw_request):
                yield chunk
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            error_data = {"error": {"message": str(e), "type": "internal_error"}}
            yield f"data: {json.dumps(error_data)}\n\n"
        finally:
            watcher_task.cancel()

    async def start(self) -> None:
        """Start the API server"""
        logger.info(f"Starting API server on {self.config.host}:{self.config.port}")

        config = uvicorn.Config(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info"
        )

        self.server = uvicorn.Server(config)

        try:
            await self.server.serve()
        except Exception as e:
            logger.error(f"API server failed: {e}")
            raise

    async def stop(self) -> None:
        """Stop the API server"""
        if self.server:
            logger.info("Stopping API server...")
            await self.server.shutdown()
            self.server = None
