import importlib

import pytest

stt_module = importlib.import_module("tools.stt.stt")
from tools.stt.stt import preload_model, stt


@pytest.mark.asyncio
async def test_stt_success(monkeypatch):
    """Test successful speech-to-text transcription."""
    captured = {}

    async def fake_acquire(tool_name: str, hard_fail: bool = False):
        captured["tool_name"] = tool_name

    def fake_transcribe(audio_bytes):
        captured["audio_bytes"] = audio_bytes
        return "Hello world!"

    async def fake_to_thread(func, audio_bytes):
        captured["func"] = func
        return func(audio_bytes)

    monkeypatch.setattr(stt_module.rate_limiter, "acquire", fake_acquire)
    monkeypatch.setattr(stt_module.audio_service_instance, "_transcribe_sync", fake_transcribe)
    monkeypatch.setattr(stt_module.asyncio, "to_thread", fake_to_thread)

    result = await stt(b"fake_audio_data")

    assert result["status"] == "ok"
    assert result["data"]["text"] == "Hello world!"
    assert captured["tool_name"] == "stt"
    assert captured["func"] is fake_transcribe
    assert captured["audio_bytes"] == b"fake_audio_data"


@pytest.mark.asyncio
async def test_stt_empty_result(monkeypatch):
    """Test speech-to-text with empty transcription result."""
    async def fake_acquire(tool_name: str, hard_fail: bool = False):
        return None

    async def fake_to_thread(func, audio_bytes):
        return ""

    monkeypatch.setattr(stt_module.rate_limiter, "acquire", fake_acquire)
    monkeypatch.setattr(stt_module.asyncio, "to_thread", fake_to_thread)

    result = await stt(b"empty_audio_data")

    assert result["status"] == "ok"
    assert result["data"]["text"] == ""


@pytest.mark.asyncio
async def test_stt_no_audio():
    result = await stt(b"")

    assert result["status"] == "error"
    assert result["error"]["code"] == "VALIDATION_ERROR"
    assert result["error"]["message"] == "No audio data provided."


def test_preload_model_uses_shared_model_service(monkeypatch):
    """Test preload_model warms the shared model service once."""
    captured = {"calls": 0}

    def fake_preload():
        captured["calls"] += 1

    monkeypatch.setattr(stt_module.audio_service_instance.model_service, "preload_model", fake_preload)

    preload_model()

    assert captured["calls"] == 1
