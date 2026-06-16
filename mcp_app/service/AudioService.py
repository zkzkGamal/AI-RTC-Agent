"""
Audio processing service for handling audio data in various formats.
This service provides methods to decode audio input, transcribe it using the Whisper model, and manage model loading and rate limiting. It is designed to be used by tools that require speech-to-text functionality, allowing them to easily convert audio data into text for further processing. 
The service handles different audio input formats, including raw bytes and base64-encoded strings, ensuring flexibility in how audio data can be provided to the system.
"""
import base64
import logging
import os
import tempfile

from service.LoadModelService import load_model_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class audio_service:
    """
    This service provides methods to decode audio input, transcribe it using the Whisper model, and manage model loading and rate limiting. It is designed to be used by tools that require speech-to-text functionality, allowing them to easily convert audio data into text for further processing. 
    The service handles different audio input formats, including raw bytes and base64-encoded strings, ensuring flexibility in how audio data can be provided to the system.
    """
    def __init__(self):
        """
        How to use:
        1. Call preload_model during server startup to warm the Whisper model for faster first requests.
        2. Call stt with audio data in bytes or base64 string format to get the transcribed text.
        3. The stt method will handle decoding the audio input and transcribing it using the Whisper model, returning the resulting text or raising an error if transcription fails.
        args:
            audio_bytes: Audio data in bytes format or base64-encoded string.
        returns:
            Transcribed text from the audio input.
        """
        self.model_service = load_model_service

    def _decode_audio(self , audio_bytes: bytes | str) -> bytes:
        """
        Normalize audio input to raw bytes.
        Handles: raw bytes, base64 string, base64 bytes.
        """
        try:
            if isinstance(audio_bytes, str):
                try:
                    return base64.b64decode(audio_bytes)
                except Exception:
                    return audio_bytes.encode("utf-8")

            if audio_bytes.startswith(b"UklGR"):
                try:
                    return base64.b64decode(audio_bytes)
                except Exception:
                    return audio_bytes

            if not audio_bytes.startswith(b"RIFF"):
                try:
                    decoded = base64.b64decode(audio_bytes)
                    if decoded.startswith(b"RIFF"):
                        return decoded
                except Exception:
                    pass

            return audio_bytes
        except Exception as e:
            logger.error(f"Failed to decode audio: {e}")
            raise ValueError(f"Could not decode audio due to: {e}")

    def _transcribe_sync(self , audio_bytes: bytes | str) -> str:
        """
        Sync Whisper transcription — runs in a thread via asyncio.to_thread.
        Raises on failure.
        """
        raw = self._decode_audio(audio_bytes)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(raw)
            tmp_path = tmp.name

        try:
            result = self.model_service.get_model().transcribe(tmp_path, language="en", fp16=False)
            return result["text"].strip()
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
