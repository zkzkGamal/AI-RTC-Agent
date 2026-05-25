"""
This module provides a tool for converting speech to text using the Whisper model.
The `stt` function takes audio data in bytes format and returns the transcribed text.
The tool is designed to be easy to use and can be integrated into different systems seamlessly.
"""
import logging
import asyncio

from server import mcp
from service.AudioService import audio_service

try:
    from mcp.utils import ok, err, from_exception
    from mcp.utils.rate_limiter import rate_limiter
except ModuleNotFoundError:
    from utils import  ok, err, from_exception
    from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)
audio_service_instance = audio_service()


def preload_model() -> None:
    """Warm the shared Whisper model used by the audio service."""
    audio_service_instance.model_service.preload_model()


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

        text = await asyncio.to_thread(audio_service_instance._transcribe_sync, audio_bytes)

        logger.info(f"STT transcribed: '{text[:80]}{'...' if len(text) > 80 else ''}'")
        return ok(data={"text": text})

    except Exception as e:
        logger.error(f"stt failed: {e}")
        return from_exception(e)
