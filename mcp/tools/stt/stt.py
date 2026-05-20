"""
This module provides a tool for converting speech to text using the Whisper model.
The `stt` function takes audio data in bytes format and returns the transcribed text.
The tool is designed to be easy to use and can be integrated into different systems seamlessly.
"""

from server import mcp
import logging , environ , pathlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

base_path = pathlib.Path(__file__).parent.parent.parent
e = environ.Env()
e.read_env(str(base_path / ".env"))

@mcp.tool()
def stt(audio_bytes: bytes) -> str:
    """
    Convert speech to text using the whisper model.
    Args:
        audio_bytes (bytes): The audio data in bytes format.
    Returns:
        str: The transcribed text from the audio.
    """
    import torch
    import whisper

    # Load the whisper model
    model = whisper.load_model("base")

    # Transcribe the audio
    result = model.transcribe(audio_bytes, language='en', fp16=False)
    text = result['text'].strip()
    return text