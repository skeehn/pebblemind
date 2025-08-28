"""Voice Processor using whisper.cpp and Piper TTS"""

import asyncio
import logging
import io
import subprocess
import tempfile
import os
from typing import Optional, Dict, Any
from pathlib import Path
import numpy as np
import soundfile as sf

from ..config import VoiceConfig

logger = logging.getLogger(__name__)


class VoiceProcessor:
    """Voice processing with speech-to-text and text-to-speech"""

    def __init__(self, config: VoiceConfig):
        """Initialize voice processor with configuration"""
        self.config = config
        self._whisper_path: Optional[str] = None
        self._piper_path: Optional[str] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize voice processing components"""
        if self._initialized:
            return

        try:
            logger.info("Initializing voice processor...")

            # Find or download whisper.cpp
            await self._setup_whisper()

            # Find or download Piper TTS
            await self._setup_piper()

            self._initialized = True
            logger.info("Voice processor initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize voice processor: {e}")
            raise

    async def _setup_whisper(self) -> None:
        """Setup whisper.cpp for speech-to-text"""
        try:
            # Try to find existing whisper installation
            whisper_path = self._find_whisper_executable()

            if not whisper_path:
                # Download and build whisper.cpp
                whisper_path = await self._download_whisper()

            self._whisper_path = whisper_path
            logger.info(f"Whisper.cpp ready at: {whisper_path}")

        except Exception as e:
            logger.warning(f"Failed to setup whisper.cpp: {e}. STT will be unavailable.")
            self._whisper_path = None

    async def _setup_piper(self) -> None:
        """Setup Piper TTS for text-to-speech"""
        try:
            # Try to find existing Piper installation
            piper_path = self._find_piper_executable()

            if not piper_path:
                # Download Piper
                piper_path = await self._download_piper()

            self._piper_path = piper_path
            logger.info(f"Piper TTS ready at: {piper_path}")

        except Exception as e:
            logger.warning(f"Failed to setup Piper TTS: {e}. TTS will be unavailable.")
            self._piper_path = None

    def _find_whisper_executable(self) -> Optional[str]:
        """Find existing whisper executable"""
        # Check common locations
        common_paths = [
            "/usr/local/bin/whisper-cpp",
            "/usr/bin/whisper-cpp",
            "./whisper.cpp/main",
            "./models/whisper/main",
        ]

        for path in common_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path

        return None

    def _find_piper_executable(self) -> Optional[str]:
        """Find existing Piper executable"""
        # Check common locations
        common_paths = [
            "/usr/local/bin/piper",
            "/usr/bin/piper",
            "./piper/piper",
            "./models/piper/piper",
        ]

        for path in common_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path

        return None

    async def _download_whisper(self) -> str:
        """Download and build whisper.cpp"""
        logger.info("Downloading whisper.cpp...")

        # Create models directory
        models_dir = Path("./models")
        models_dir.mkdir(exist_ok=True)

        whisper_dir = models_dir / "whisper.cpp"

        # Clone whisper.cpp repository
        if not whisper_dir.exists():
            process = await asyncio.create_subprocess_exec(
                "git", "clone", "https://github.com/ggerganov/whisper.cpp.git",
                str(whisper_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()

            if process.returncode != 0:
                raise RuntimeError("Failed to clone whisper.cpp repository")

        # Build whisper.cpp
        build_process = await asyncio.create_subprocess_exec(
            "make", "-C", str(whisper_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await build_process.communicate()

        if build_process.returncode != 0:
            raise RuntimeError("Failed to build whisper.cpp")

        executable_path = whisper_dir / "main"
        if not executable_path.exists():
            raise RuntimeError("whisper.cpp executable not found after build")

        return str(executable_path)

    async def _download_piper(self) -> str:
        """Download Piper TTS"""
        logger.info("Downloading Piper TTS...")

        # Create models directory
        models_dir = Path("./models")
        models_dir.mkdir(exist_ok=True)

        piper_dir = models_dir / "piper"

        # Download Piper binary (platform-specific)
        import platform
        system = platform.system().lower()
        machine = platform.machine().lower()

        if system == "linux":
            if "x86_64" in machine:
                piper_url = "https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz"
            elif "arm" in machine:
                piper_url = "https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_arm64.tar.gz"
            else:
                raise RuntimeError(f"Unsupported architecture: {machine}")
        elif system == "darwin":  # macOS
            if "arm64" in machine:
                piper_url = "https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_arm64.tar.gz"
            else:
                piper_url = "https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_x86_64.tar.gz"
        elif system == "windows":
            piper_url = "https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_windows_amd64.zip"
        else:
            raise RuntimeError(f"Unsupported platform: {system}")

        # Download and extract Piper
        import urllib.request
        import tarfile
        import zipfile

        archive_path = piper_dir / "piper.tar.gz"
        piper_dir.mkdir(exist_ok=True)

        # Download archive
        urllib.request.urlretrieve(piper_url, archive_path)

        # Extract archive
        if piper_url.endswith(".tar.gz"):
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(piper_dir)
        elif piper_url.endswith(".zip"):
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall(piper_dir)

        # Find executable
        executable_path = piper_dir / "piper" / "piper"
        if not executable_path.exists():
            # Try alternative path
            executable_path = piper_dir / "piper.exe"

        if not executable_path.exists():
            raise RuntimeError("Piper executable not found after extraction")

        return str(executable_path)

    async def speech_to_text(self, audio_data: bytes) -> str:
        """Convert speech audio to text using whisper.cpp"""
        if not self._initialized or not self._whisper_path:
            raise RuntimeError("Whisper not initialized")

        try:
            # Create temporary WAV file from audio data
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                # Convert raw audio bytes to WAV format
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                sf.write(temp_audio.name, audio_array, self.config.sample_rate)

                temp_audio_path = temp_audio.name

            try:
                # Run whisper.cpp for transcription
                process = await asyncio.create_subprocess_exec(
                    self._whisper_path,
                    "-m", f"models/ggml-{self.config.stt_model}.bin",
                    "-f", temp_audio_path,
                    "-t", str(self.config.stt_threads),
                    "--language", "en",
                    "--output-format", "txt",
                    "--no-timestamps",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    error_msg = stderr.decode().strip()
                    raise RuntimeError(f"Whisper transcription failed: {error_msg}")

                # Extract transcription from output
                transcription = stdout.decode().strip()

                return transcription

            finally:
                # Clean up temporary file
                os.unlink(temp_audio_path)

        except Exception as e:
            logger.error(f"Speech-to-text failed: {e}")
            raise

    async def text_to_speech(self, text: str) -> bytes:
        """Convert text to speech using Piper TTS"""
        if not self._initialized or not self._piper_path:
            raise RuntimeError("Piper TTS not initialized")

        try:
            # Create temporary output file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_output:
                temp_output_path = temp_output.name

            try:
                # Run Piper TTS
                process = await asyncio.create_subprocess_exec(
                    self._piper_path,
                    "--model", f"models/piper/{self.config.tts_model}.onnx",
                    "--output_file", temp_output_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    stdin=asyncio.subprocess.PIPE
                )

                # Send text to Piper
                await process.communicate(input=text.encode())

                if process.returncode != 0:
                    raise RuntimeError("Piper TTS synthesis failed")

                # Read generated audio file
                with open(temp_output_path, "rb") as f:
                    audio_data = f.read()

                return audio_data

            finally:
                # Clean up temporary file
                if os.path.exists(temp_output_path):
                    os.unlink(temp_output_path)

        except Exception as e:
            logger.error(f"Text-to-speech failed: {e}")
            raise

    async def get_status(self) -> Dict[str, Any]:
        """Get voice processor status"""
        return {
            "initialized": self._initialized,
            "whisper_available": self._whisper_path is not None,
            "piper_available": self._piper_path is not None,
            "whisper_path": self._whisper_path,
            "piper_path": self._piper_path,
            "config": self.config.model_dump()
        }
