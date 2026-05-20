import sys
from unittest.mock import MagicMock, ANY
from tools.stt.stt import stt

stt_module = sys.modules['tools.stt.stt']

def test_stt_success():
    """Test successful speech-to-text transcription."""
    mock_audio_bytes = b"fake_audio_data"
    
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {'text': '  Hello world!  '}
    
    # Save the original model and swap it with our mock
    orig_model = stt_module.model
    stt_module.model = mock_model
    try:
        result = stt(mock_audio_bytes)
        
        assert result == "Hello world!"
        mock_model.transcribe.assert_called_once_with(ANY, language='en', fp16=False)
    finally:
        stt_module.model = orig_model

def test_stt_empty_result():
    """Test speech-to-text with empty transcription result."""
    mock_audio_bytes = b"empty_audio_data"
    
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {'text': '   '}
    
    # Save the original model and swap it with our mock
    orig_model = stt_module.model
    stt_module.model = mock_model
    try:
        result = stt(mock_audio_bytes)
        
        assert result == ""
        mock_model.transcribe.assert_called_once_with(ANY, language='en', fp16=False)
    finally:
        stt_module.model = orig_model

