import sys
from unittest.mock import MagicMock, ANY
import pytest
from tools.stt.stt import stt

stt_module = sys.modules['tools.stt.stt']

@pytest.mark.asyncio
async def test_stt_success():
    """Test successful speech-to-text transcription."""
    mock_audio_bytes = b"fake_audio_data"
    
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {'text': '  Hello world!  '}
    
    # Save the original model and swap it with our mock
    orig_model = stt_module.model
    stt_module.model = mock_model
    try:
        result = await stt(mock_audio_bytes)
        
        assert result["status"] == "ok"
        assert result["data"]["text"] == "Hello world!"
        mock_model.transcribe.assert_called_once_with(ANY, language='en', fp16=False)
    finally:
        stt_module.model = orig_model

@pytest.mark.asyncio
async def test_stt_empty_result():
    """Test speech-to-text with empty transcription result."""
    mock_audio_bytes = b"empty_audio_data"
    
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {'text': '   '}
    
    # Save the original model and swap it with our mock
    orig_model = stt_module.model
    stt_module.model = mock_model
    try:
        result = await stt(mock_audio_bytes)
        
        assert result["status"] == "ok"
        assert result["data"]["text"] == ""
        mock_model.transcribe.assert_called_once_with(ANY, language='en', fp16=False)
    finally:
        stt_module.model = orig_model
