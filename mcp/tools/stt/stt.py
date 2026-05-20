"""
This module provides a tool for converting speech to text using the Whisper model.
The `stt` function takes audio data in bytes format and returns the transcribed text.
The tool is designed to be easy to use and can be integrated into different systems seamlessly.
"""

from server import mcp
import logging , environ , pathlib
import whisper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

base_path = pathlib.Path(__file__).parent.parent.parent
e = environ.Env()
e.read_env(str(base_path / ".env"))

# Load the whisper model
model = whisper.load_model("small")

@mcp.tool()
def stt(audio_bytes: bytes) -> str:
    """
    Convert speech to text using the whisper model.
    Args:
        audio_bytes (bytes): The audio data in bytes format.
    Returns:
        str: The transcribed text from the audio.
    """
    import tempfile
    import os
    import base64

    # Handle base64 encoding detection and decoding
    raw_data = audio_bytes
    if isinstance(raw_data, str):
        try:
            raw_data = base64.b64decode(raw_data)
        except Exception:
            raw_data = raw_data.encode('utf-8')

    if isinstance(raw_data, bytes):
        if raw_data.startswith(b"UklGR"):
            try:
                raw_data = base64.b64decode(raw_data)
            except Exception:
                pass
        elif not raw_data.startswith(b"RIFF"):
            try:
                decoded = base64.b64decode(raw_data)
                if decoded.startswith(b"RIFF"):
                    raw_data = decoded
            except Exception:
                pass

    # Write the audio bytes to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(raw_data)
        tmp_path = tmp.name

    try:
        # Transcribe the audio file path
        result = model.transcribe(tmp_path, language='en', fp16=False)
        text = result['text'].strip()
    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return text