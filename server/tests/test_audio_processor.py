import os
import shutil
import pytest
import numpy as np
from audio_processor import AudioSession

@pytest.fixture
def temp_output_dir():
    # AudioSession creates "utterances/<session_id>" relative to Cwd
    session_id = "test_session_id"
    yield session_id
    # Clean up output files
    shutil.rmtree(os.path.join("utterances", session_id), ignore_errors=True)

@pytest.mark.asyncio
async def test_audio_session_lockstep_and_vad(temp_output_dir):
    session = AudioSession(session_id=temp_output_dir, sample_rate=48000, silence_threshold=0.2)
    
    # 1. Initially silent
    assert not session._is_speaking
    assert len(session._speech_buffer) == 0

    # 30ms of silence at 48kHz is 1440 samples
    # 1440 samples * 2 bytes = 2880 bytes
    silent_frame = bytes(2880)

    # Feed 10 silent frames (300ms)
    for _ in range(10):
        await session.add_frame(silent_frame, sample_rate=48000)
    
    assert not session._is_speaking
    assert len(session._speech_buffer) == 0

    # 2. Feed speech frames (M_ONSET is 6/10)
    # A speech frame must not be completely zeroed out (since webrtcvad checks energy)
    # We will generate a 1000 Hz sine wave for speech simulation
    t = np.linspace(0, 0.03, 1440, endpoint=False)
    sine_wave = (np.sin(2 * np.pi * 1000 * t) * 10000).astype(np.int16)
    speech_frame = sine_wave.tobytes()

    # Feed 5 speech frames (less than M_ONSET=6)
    # VAD sliding window size is 10.
    for _ in range(5):
        await session.add_frame(speech_frame, sample_rate=48000)
    
    # Not yet speaking due to sliding window onset filter (requires 6/10 active)
    assert not session._is_speaking
    
    # Feed 6th speech frame (now onset should trigger)
    await session.add_frame(speech_frame, sample_rate=48000)
    assert session._is_speaking
    
    # The speech buffer should contain the pre-speech history padding
    # History buffer retains the last 10 frames (10 * 2880 = 28800 bytes)
    # Since we fed 10 silent frames then 6 speech frames, the history at onset contained
    # 4 silent frames + 6 speech frames = 10 frames.
    assert len(session._speech_buffer) >= 28800

    # 3. Transition back to silence
    # Feed 25 silent frames to trigger offset transition
    # Since silence_threshold is 0.2s, 25 frames = 750ms of silence will exceed 0.2s silence threshold!
    for _ in range(25):
        await session.add_frame(silent_frame, sample_rate=48000)
        # Check if saved and reset (occurs when elapsed >= silence_threshold)
        if not session._is_speaking:
            break

    # Should have transitioned back to silence and saved the utterance
    assert not session._is_speaking
    assert session._utterance_count == 1
    assert len(session._speech_buffer) == 0

    # Clean up
    await session.close()
