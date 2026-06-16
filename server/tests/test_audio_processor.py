"""Tests for audio_processor."""

import os
import shutil
import pytest
import numpy as np
from audio_processor import AudioSession

@pytest.fixture
def temp_output_dir():
    session_id = "test_session_id"
    yield session_id
    shutil.rmtree(os.path.join("utterances", session_id), ignore_errors=True)

@pytest.mark.asyncio
async def test_audio_session_lockstep_and_vad(temp_output_dir):
    session = AudioSession(session_id=temp_output_dir, sample_rate=48000, silence_threshold=0.2)

    assert not session._is_speaking
    assert len(session._speech_buffer) == 0

    silent_frame = bytes(2880)

    for _ in range(10):
        await session.add_frame(silent_frame, sample_rate=48000)

    assert not session._is_speaking
    assert len(session._speech_buffer) == 0

    t = np.linspace(0, 0.03, 1440, endpoint=False)
    sine_wave = (np.sin(2 * np.pi * 1000 * t) * 10000).astype(np.int16)
    speech_frame = sine_wave.tobytes()

    for _ in range(5):
        await session.add_frame(speech_frame, sample_rate=48000)

    assert not session._is_speaking

    await session.add_frame(speech_frame, sample_rate=48000)
    assert session._is_speaking

    assert len(session._speech_buffer) >= 28800

    for _ in range(25):
        await session.add_frame(silent_frame, sample_rate=48000)
        if not session._is_speaking:
            break

    assert not session._is_speaking
    assert session._utterance_count == 1
    assert len(session._speech_buffer) == 0

    await session.close()
