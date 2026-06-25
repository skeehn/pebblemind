"""OpenAI-compatible API server for PebbleMind"""

import asyncio
import logging
import json
import inspect
import time
from email.parser import BytesParser
from email.policy import default as email_policy
from collections import defaultdict
from typing import Dict, Any, List, Optional, TYPE_CHECKING, Tuple
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Request, Depends, WebSocket, WebSocketDisconnect, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

if TYPE_CHECKING:
    from ..pebblemind_app import PebbleMind

from ..core.streaming import sse_stream, websocket_stream, websocket_internal_error
from ..config import APIConfig

logger = logging.getLogger(__name__)
DISCONNECT_POLL_INTERVAL = 0.05

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

    def __init__(self, config: APIConfig, pebblemind: "PebbleMind"):
        """Initialize API server with configuration"""
        self.config = config
        self.pebblemind = pebblemind
        self.app = FastAPI(title="PebbleMind API", version="1.0.0")
        self.server = None
        self._setup_routes()
        self._setup_middleware()

    def _validate_api_key(self, provided_api_key: Optional[str]) -> bool:
        """Validate a provided API key if authentication is enabled."""
        if not self.config.api_key:
            return True

        if not provided_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if provided_api_key != self.config.api_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key"
            )

        return True

    def _check_client_rate_limit(self, client_id: str) -> bool:
        """Check rate limit for a client identifier."""
        if not rate_limiter.is_allowed(client_id):
            retry_after = rate_limiter.get_retry_after(client_id)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(retry_after)}
            )

        return True

    async def verify_api_key(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
        """Verify API key if authentication is enabled"""
        provided_api_key = credentials.credentials if credentials else None
        return self._validate_api_key(provided_api_key)

    async def check_rate_limit(self, request: Request) -> bool:
        """Check rate limit for the request"""
        # Use client IP as identifier
        client_id = request.client.host

        return self._check_client_rate_limit(client_id)

    async def verify_websocket_api_key(self, websocket: WebSocket) -> bool:
        """Verify API key for a WebSocket connection."""
        provided_api_key = None

        authorization = websocket.headers.get("authorization")
        if authorization and authorization.startswith("Bearer "):
            provided_api_key = authorization[7:]

        if not provided_api_key:
            provided_api_key = websocket.query_params.get("api_key")

        try:
            return self._validate_api_key(provided_api_key)
        except HTTPException as exc:
            close_code = 4401 if exc.status_code == status.HTTP_401_UNAUTHORIZED else 4403
            await websocket.close(code=close_code, reason=exc.detail)
            return False

    async def check_websocket_rate_limit(self, websocket: WebSocket) -> bool:
        """Check rate limit for a WebSocket connection."""
        client_id = websocket.client.host if websocket.client else "unknown"

        try:
            return self._check_client_rate_limit(client_id)
        except HTTPException as exc:
            await websocket.close(code=4429, reason=exc.detail)
            return False

    async def _prepare_stream_inputs(self, message: str) -> Tuple[str, List[str]]:
        """Prepare streaming inputs using the default PebbleMind query-preparation settings."""
        prepare_inputs = self._get_pebblemind_hook("prepare_generation_inputs")
        if prepare_inputs is None:
            return message, []

        prepared = prepare_inputs(
            message,
            use_rag=True,
            enhance_reasoning=True,
            reasoning_type="analytical",
            use_memory=True,
        )
        if inspect.isawaitable(prepared):
            return await prepared
        return prepared

    async def _finalize_stream_interaction(
        self,
        message: str,
        response: str,
        start_time: float,
    ) -> None:
        """Apply PebbleMind post-generation side effects for completed streams."""
        finalize_interaction = self._get_pebblemind_hook("finalize_interaction")
        if finalize_interaction is None:
            return

        finalized = finalize_interaction(
            message,
            response,
            use_memory=True,
            learn_from_interaction=True,
            memory_importance=0.6,
            start_time=start_time,
        )
        if inspect.isawaitable(finalized):
            await finalized

    async def _record_stream_error(
        self,
        message: str,
        error: Exception,
        start_time: float,
    ) -> None:
        """Allow PebbleMind to learn from streaming failures."""
        record_interaction_error = self._get_pebblemind_hook("record_interaction_error")
        if record_interaction_error is None:
            return

        recorded = record_interaction_error(
            message,
            error,
            learn_from_interaction=True,
            start_time=start_time,
        )
        if inspect.isawaitable(recorded):
            await recorded

    async def _read_transcription_upload(self, request: Request) -> Tuple[bytes, str]:
        """Read an uploaded transcription file, even when multipart extras are unavailable."""
        try:
            form = await request.form()
            audio_file = form.get("file")
            if not audio_file:
                raise HTTPException(status_code=400, detail="No audio file provided")
            return await audio_file.read(), audio_file.content_type or "application/octet-stream"
        except HTTPException:
            raise
        except AssertionError as exc:
            if "python-multipart" not in str(exc):
                raise
            return await self._read_transcription_upload_without_multipart(request)

    async def _read_transcription_upload_without_multipart(self, request: Request) -> Tuple[bytes, str]:
        """Fallback multipart parsing for basic upload validation without python-multipart."""
        content_type_header = request.headers.get("content-type", "")
        if "multipart/form-data" not in content_type_header.lower():
            raise HTTPException(status_code=400, detail="No audio file provided")

        body = await request.body()
        if not body:
            raise HTTPException(status_code=400, detail="No audio file provided")

        message = BytesParser(policy=email_policy).parsebytes(
            (
                f"Content-Type: {content_type_header}\r\n"
                "MIME-Version: 1.0\r\n\r\n"
            ).encode("utf-8")
            + body
        )

        if not message.is_multipart():
            raise HTTPException(status_code=400, detail="No audio file provided")

        for part in message.iter_parts():
            if part.get_param("name", header="content-disposition") != "file":
                continue

            return part.get_payload(decode=True) or b"", part.get_content_type()

        raise HTTPException(status_code=400, detail="No audio file provided")

    def _get_pebblemind_hook(self, hook_name: str):
        """Return real PebbleMind hooks while ignoring dynamic Mock fallback attributes.

        Some API tests pass plain ``Mock()`` instances as the PebbleMind dependency.
        Direct ``getattr(mock, name)`` access fabricates placeholder attributes even when
        the hook was never defined, so this helper only accepts explicitly provided
        instance hooks or actual class methods.
        """
        instance_hooks = getattr(self.pebblemind, "__dict__", {})
        if hook_name in instance_hooks:
            return instance_hooks[hook_name]
        if hasattr(type(self.pebblemind), hook_name):
            return getattr(self.pebblemind, hook_name)
        return None

    def _setup_middleware(self):
        """Setup CORS and other middleware"""
        # Add security headers middleware
        @self.app.middleware("http")
        async def add_security_headers(request: Request, call_next):
            response = await call_next(request)

            # Strict Transport Security (HTTPS only)
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

            # Content Security Policy
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )

            # Prevent clickjacking
            response.headers["X-Frame-Options"] = "DENY"

            # Prevent MIME type sniffing
            response.headers["X-Content-Type-Options"] = "nosniff"

            # XSS Protection (legacy, but still good to have)
            response.headers["X-XSS-Protection"] = "1; mode=block"

            # Referrer Policy
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

            # Permissions Policy (formerly Feature-Policy)
            response.headers["Permissions-Policy"] = (
                "camera=(), microphone=(), geolocation=(), "
                "payment=(), usb=(), magnetometer=(), "
                "gyroscope=(), accelerometer=()"
            )

            # Remove server header for security
            if "Server" in response.headers:
                del response.headers["Server"]

            return response

        # Add CORS middleware
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
                        media_type="text/event-stream"
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

            except HTTPException:
                raise
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
                audio_data, content_type = await self._read_transcription_upload(request)

                # Validate file type
                allowed_audio_types = {
                    "audio/wav", "audio/wave", "audio/x-wav",
                    "audio/mp3", "audio/mpeg",
                    "audio/ogg", "audio/flac"
                }

                if content_type not in allowed_audio_types:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid file type. Allowed types: {', '.join(allowed_audio_types)}"
                    )

                # Validate file size (max 25MB)
                MAX_FILE_SIZE = 25 * 1024 * 1024
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

            except HTTPException:
                raise
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

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Speech generation failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="Internal server error occurred during speech generation"
                )

        @self.app.websocket("/ws/chat")
        async def websocket_chat(websocket: WebSocket):
            if not await self.verify_websocket_api_key(websocket):
                return

            if not await self.check_websocket_rate_limit(websocket):
                return

            await websocket.accept()
            listener = None
            start_time = time.time()
            try:
                data = await websocket.receive_json()
                message = data.get("message", "").strip()
                system_prompt = data.get("system_prompt")

                if not message:
                    await websocket.send_json(
                        {"error": {"message": "No message provided", "type": "validation_error"}}
                    )
                    return

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

                message, context = await self._prepare_stream_inputs(message)
                accumulated_response: List[str] = []
                stream_error: Optional[Exception] = None
                generator = self.pebblemind.llm_engine.generate_stream(
                    message,
                    context=context,
                    system_prompt=system_prompt,
                    stop_event=stop_event,
                    **gen_params
                )

                async def tracked_generator():
                    nonlocal stream_error
                    try:
                        async for chunk in generator:
                            accumulated_response.append(chunk)
                            yield chunk
                    except Exception as exc:
                        stream_error = exc
                        raise

                await websocket_stream(websocket, tracked_generator(), stop_event)
                if stream_error is not None:
                    await self._record_stream_error(message, stream_error, start_time)
                elif not stop_event.is_set():
                    await self._finalize_stream_interaction(
                        message,
                        "".join(accumulated_response),
                        start_time,
                    )
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")
            except Exception as e:
                logger.error(f"WebSocket chat failed: {e}", exc_info=True)
                await self._record_stream_error(message, e, start_time)
                try:
                    await websocket.send_json(websocket_internal_error(str(e)))
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected while sending error response")
            finally:
                if listener is not None and not listener.done():
                    listener.cancel()
                    try:
                        await listener
                    except asyncio.CancelledError:
                        pass


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
        start_time = time.time()

        async def disconnect_watcher():
            while not stop_event.is_set():
                if await raw_request.is_disconnected():
                    stop_event.set()
                    break
                await asyncio.sleep(DISCONNECT_POLL_INTERVAL)

        watcher_task = asyncio.create_task(disconnect_watcher())

        try:
            message, context = await self._prepare_stream_inputs(message)
            accumulated_response: List[str] = []
            generator = self.pebblemind.llm_engine.generate_stream(
                message,
                context=context,
                system_prompt=system_prompt,
                stop_event=stop_event,
                **kwargs
            )

            async def tracked_generator():
                async for token in generator:
                    accumulated_response.append(token)
                    yield token

            async for chunk in sse_stream(tracked_generator(), model, raw_request):
                yield chunk
            if not stop_event.is_set():
                await self._finalize_stream_interaction(
                    message,
                    "".join(accumulated_response),
                    start_time,
                )
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            await self._record_stream_error(message, e, start_time)
            error_data = {"error": {"message": str(e), "type": "internal_error"}}
            yield f"data: {json.dumps(error_data)}\n\n"
        finally:
            watcher_task.cancel()

    async def start(self) -> None:
        """Start the API server"""
        protocol = "https" if self.config.enable_https else "http"
        logger.info(f"Starting API server on {protocol}://{self.config.host}:{self.config.port}")

        # Prepare SSL configuration
        ssl_keyfile = None
        ssl_certfile = None
        ssl_ca_certs = None

        if self.config.enable_https:
            if not self.config.ssl_cert_path or not self.config.ssl_key_path:
                raise ValueError(
                    "HTTPS enabled but SSL certificate or key path not provided. "
                    "Set ssl_cert_path and ssl_key_path in configuration."
                )

            ssl_certfile = self.config.ssl_cert_path
            ssl_keyfile = self.config.ssl_key_path
            ssl_ca_certs = self.config.ssl_ca_certs

            logger.info(f"HTTPS enabled with certificate: {ssl_certfile}")

        config = uvicorn.Config(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info",
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            ssl_ca_certs=ssl_ca_certs
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


def main() -> None:
    """Console-script entry point: launch the OpenAI-compatible API server.

    Wired to the ``pebblemind-api`` script in pyproject.toml. Boots a local
    PebbleMind instance and serves it over HTTP using the configured APIConfig.
    """
    import asyncio

    from ..config import get_config
    from ..pebblemind_app import quick_start

    pebblemind = quick_start()
    server = APIServer(config=get_config().api, pebblemind=pebblemind)
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("API server stopped")


if __name__ == "__main__":
    main()
