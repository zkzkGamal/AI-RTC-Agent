import pytest
import sys
from unittest.mock import MagicMock

from tools.stt.stt import stt

def test_stt_success():
    """Test successful speech-to-text transcription."""
    mock_audio_bytes = b"fake_audio_data"
    
    mock_whisper = MagicMock()
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {'text': '  Hello world!  '}
    mock_whisper.load_model.return_value = mock_model
    
    # Patch sys.modules to inject our mock whisper module
    sys.modules['whisper'] = mock_whisper
    try:
        result = stt(mock_audio_bytes)
        
        assert result == "Hello world!"
        mock_whisper.load_model.assert_called_once_with("base")
        mock_model.transcribe.assert_called_once_with(mock_audio_bytes, language='en', fp16=False)
    finally:
        del sys.modules['whisper']

def test_stt_empty_result():
    """Test speech-to-text with empty transcription result."""
    mock_audio_bytes = b"empty_audio_data"
    
    mock_whisper = MagicMock()
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {'text': '   '}
    mock_whisper.load_model.return_value = mock_model
    
    sys.modules['whisper'] = mock_whisper
    try:
        result = stt(mock_audio_bytes)
        
        assert result == ""
        mock_whisper.load_model.assert_called_once_with("base")
        mock_model.transcribe.assert_called_once_with(mock_audio_bytes, language='en', fp16=False)
    finally:
        del sys.modules['whisper']

