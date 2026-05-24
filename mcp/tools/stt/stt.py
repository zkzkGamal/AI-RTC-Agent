"""
This module provides a tool for converting speech to text using the Whisper model.
The `stt` function takes audio data in bytes format and returns the transcribed text.
The tool is designed to be easy to use and can be integrated into different systems seamlessly.
"""
import os
import base64
import logging
import asyncio
import tempfile

from server import mcp
from utils import ok, err, from_exception
from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

# Lazily load the Whisper model on first access, or preload it during server
# startup for smoother first-request latency.
model = None


def _get_model():
    global model
    if model is None:
        import whisper

        model = whisper.load_model("small")
        logger.info("Whisper model loaded.")
    return model


def preload_model() -> None:
    """Warm the Whisper model during server startup."""
    _get_model()


def _decode_audio(audio_bytes: bytes | str) -> bytes:
    """
    Normalize audio input to raw bytes.
    Handles: raw bytes, base64 string, base64 bytes.
    """
    # String input — try base64 decode first
    if isinstance(audio_bytes, str):
        try:
            return base64.b64decode(audio_bytes)
        except Exception:
            return audio_bytes.encode("utf-8")

    # Bytes that look like base64-encoded WAV (starts with b"UklGR" = "RIFF" in b64)
    if audio_bytes.startswith(b"UklGR"):
        try:
            return base64.b64decode(audio_bytes)
        except Exception:
            return audio_bytes

    # Bytes that don't start with RIFF — might still be base64
    if not audio_bytes.startswith(b"RIFF"):
        try:
            decoded = base64.b64decode(audio_bytes)
            if decoded.startswith(b"RIFF"):
                return decoded
        except Exception:
            pass

    return audio_bytes


def _transcribe_sync(audio_bytes: bytes | str) -> str:
    """
    Sync Whisper transcription — runs in a thread via asyncio.to_thread.
    Raises on failure.
    """
    raw = _decode_audio(audio_bytes)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(raw)
        tmp_path = tmp.name

    try:
        result = _get_model().transcribe(tmp_path, language="en", fp16=False)
        return result["text"].strip()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@mcp.tool()
async def stt(audio_bytes: bytes) -> dict:
    """
    Convert speech to text using the local Whisper model.

    Args:
        audio_bytes: Raw audio bytes or base64-encoded audio.

    Returns:
        Transcribed text.
    """
    try:
        if not audio_bytes:
            return err(message="No audio data provided.", code="VALIDATION_ERROR")

        await rate_limiter.acquire("stt")

        text = await asyncio.to_thread(_transcribe_sync, audio_bytes)

        logger.info(f"STT transcribed: '{text[:80]}{'...' if len(text) > 80 else ''}'")
        return ok(data={"text": text})

    except Exception as e:
        logger.error(f"stt failed: {e}")
        return from_exception(e)
