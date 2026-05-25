"""
audio_processor.py
Handles per-session audio buffering, VAD (Voice Activity Detection),
and saving speech utterances as WAV files.

Architecture inspired by the VoiceModule pattern:
  - Continuously receive PCM frames
  - Run VAD on every frame
  - When speech → accumulate in buffer
  - When silence ≥ threshold after speech → save utterance as WAV, reset, continue loop
  - On session close → flush any remaining audio
"""

import os
import time
import wave
import logging
import asyncio
import numpy as np
import io
import base64

import webrtcvad
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

logger = logging.getLogger(__name__)

# ─── Constants ──────────────────────────────────────────────────────
# webrtcvad supports 8kHz, 16kHz, 32kHz, 48kHz
# We use 16kHz for VAD (proven reliable), downsample from input rate
VAD_SAMPLE_RATE = 16000
VAD_FRAME_DURATION_MS = 30                                         # 30ms frames (matches VoiceModule)
VAD_FRAME_BYTES = int(VAD_SAMPLE_RATE * VAD_FRAME_DURATION_MS / 1000) * 2  # 480 samples × 2 bytes = 960 bytes

# VAD Hysteresis / Smoothing configuration
VAD_WINDOW_SIZE = 10  # Sliding window size of last 10 frames (300ms)
M_ONSET = 6           # Require at least 6/10 active frames to trigger speech onset
M_OFFSET = 1          # Require <= 1/10 active frames to trigger silence/offset countdown


class AudioSession:
    """
    Manages one user's audio stream:
    - Receives raw PCM frames (e.g. 48 kHz, 16-bit, mono)
    - Downsamples to 16 kHz for VAD
    - Uses a sliding window VAD state machine for robust speech detection
    - Automatically includes pre-speech padding (look-back) and post-speech tail
    - Saves each utterance to utterances/<session_id>/utt_<timestamp>.wav
    - After saving, resets and continues listening (loop)
    """

    def __init__(self, session_id: str, sample_rate: int = 48000, silence_threshold: float = 2.0):
        self.session_id = session_id
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold   # seconds of silence before saving

        # VAD: aggressiveness 3 = most aggressive filtering (matches VoiceModule)
        self.vad = webrtcvad.Vad(3)

        # ── Input stream buffers (lockstep processing) ──
        self._input_buffer_16k = bytearray()
        self._input_buffer_raw = bytearray()

        # ── VAD State & Hysteresis Window ──
        self._is_speaking = False
        self._silence_frames_count = 0
        self._vad_window = []  # List of 0s and 1s representing recent frame speech flags
        self._history_buffer_raw = bytearray()  # Ring buffer for pre-speech padding (look-back)

        # ── Output ──
        self._speech_buffer = bytearray()            # Raw PCM accumulated during active speech
        self._utterance_count = 0

        self._output_dir = os.path.join("utterances", session_id)
        os.makedirs(self._output_dir, exist_ok=True)

        self.datachannel = None

        logger.info(f"[{self.session_id}] AudioSession created  →  {self._output_dir}")

    # ─── Public API ─────────────────────────────────────────────────

    async def add_frame(self, pcm_bytes: bytes, sample_rate: int) -> None:
        """
        Called for every audio frame from the WebRTC track.
        pcm_bytes:   raw 16-bit little-endian mono PCM at `sample_rate`
        sample_rate: typically 48000
        """
        if not pcm_bytes or len(pcm_bytes) < 2:
            return

        # Update sample rate dynamically if it changes
        if self.sample_rate != sample_rate:
            logger.info(f"[{self.session_id}] Dynamic sample rate updated: {self.sample_rate} -> {sample_rate}")
            self.sample_rate = sample_rate

        # ── Downsample from source_rate to 16kHz for VAD ──
        pcm_16k = self._decimate(pcm_bytes, sample_rate)

        # ── Append to incoming stream buffers ──
        self._input_buffer_16k.extend(pcm_16k)
        self._input_buffer_raw.extend(pcm_bytes)

        # Calculate exact ratio and raw block size for lockstep processing
        ratio = sample_rate // VAD_SAMPLE_RATE
        if ratio < 1:
            ratio = 1
        raw_frame_bytes = VAD_FRAME_BYTES * ratio

        # ── Process lockstep VAD & raw frames in 30ms chunks ──
        while len(self._input_buffer_16k) >= VAD_FRAME_BYTES and len(self._input_buffer_raw) >= raw_frame_bytes:
            chunk_16k = bytes(self._input_buffer_16k[:VAD_FRAME_BYTES])
            del self._input_buffer_16k[:VAD_FRAME_BYTES]

            chunk_raw = bytes(self._input_buffer_raw[:raw_frame_bytes])
            del self._input_buffer_raw[:raw_frame_bytes]

            try:
                is_speech = self.vad.is_speech(chunk_16k, VAD_SAMPLE_RATE)
            except Exception as e:
                logger.warning(f"[{self.session_id}] VAD error: {e}")
                is_speech = False

            # Update VAD sliding window
            self._vad_window.append(1 if is_speech else 0)
            if len(self._vad_window) > VAD_WINDOW_SIZE:
                self._vad_window.pop(0)

            active_count = sum(self._vad_window)

            # ── VAD Hysteresis State Machine ──
            if not self._is_speaking:
                # Accumulate pre-speech raw history (look-back padding)
                self._history_buffer_raw.extend(chunk_raw)
                max_history_bytes = raw_frame_bytes * VAD_WINDOW_SIZE
                if len(self._history_buffer_raw) > max_history_bytes:
                    del self._history_buffer_raw[:-max_history_bytes]

                # Transition to Speaking if enough frames in sliding window are active
                if active_count >= M_ONSET:
                    self._is_speaking = True
                    self._speech_buffer.extend(self._history_buffer_raw)
                    self._history_buffer_raw.clear()
                    self._silence_frames_count = 0
                    logger.info(f"[{self.session_id}] 🎙️  Speech onset detected ({active_count}/{VAD_WINDOW_SIZE} active)")

            else:
                # Actively speaking - append raw chunk
                self._speech_buffer.extend(chunk_raw)

                # Transition to silence countdown when window is mostly silent
                if active_count <= M_OFFSET:
                    self._silence_frames_count += 1
                    elapsed = self._silence_frames_count * VAD_FRAME_DURATION_MS / 1000.0
                    if elapsed >= self.silence_threshold:
                        # Silence threshold reached - save utterance
                        await self._save_utterance()
                        self._reset_buffers()
                        logger.info(f"[{self.session_id}] 🔇  Silence detected ({elapsed:.2f}s) → saved & reset")
                else:
                    # Voice activity detected, reset silence counter
                    self._silence_frames_count = 0

    async def close(self) -> None:
        """Flush remaining audio on session end."""
        if self._speech_buffer:
            logger.info(f"[{self.session_id}] Flushing remaining audio on close")
            await self._save_utterance()
        self._reset_buffers()
        logger.info(f"[{self.session_id}] AudioSession closed (total utterances: {self._utterance_count})")

    # ─── Private helpers ────────────────────────────────────────────

    def _decimate(self, pcm_bytes: bytes, source_rate: int) -> bytes:
        """
        Downsample by keeping every Nth sample.
        48kHz → 16kHz: N=3. If source is already 16kHz, pass through.
        """
        ratio = source_rate // VAD_SAMPLE_RATE
        if ratio <= 1:
            return pcm_bytes

        samples = np.frombuffer(pcm_bytes, dtype=np.int16)
        decimated = samples[::ratio]
        return decimated.tobytes()

    async def _save_utterance(self) -> None:
        """Save the speech buffer as a WAV file."""
        if not self._speech_buffer:
            return

        self._utterance_count += 1
        timestamp = int(time.time() * 1000)
        filename = os.path.join(self._output_dir, f"utt_{timestamp}.wav")
        data = bytes(self._speech_buffer)
        duration = len(data) / (self.sample_rate * 2)  # 2 bytes per sample

        # Write in thread to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._write_wav, filename, data)

        logger.info(
            f"[{self.session_id}] 💾  Utterance #{self._utterance_count} saved → {filename} "
            f"({len(data):,} bytes / {duration:.2f}s)"
        )
        
        # Trigger background final transcription
        asyncio.create_task(self._transcribe_and_send(data))

    def _write_wav(self, filename: str, data: bytes) -> None:
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)                   # 16-bit
            wf.setframerate(self.sample_rate)     # Dynamically matched sample rate
            wf.writeframes(data)

    def _reset_buffers(self) -> None:
        """Reset state to listen for the next utterance."""
        self._speech_buffer = bytearray()
        self._is_speaking = False
        self._silence_frames_count = 0
        self._vad_window.clear()
        self._history_buffer_raw.clear()

    # ─── DataChannel & Live Transcription ───────────────────────────

    def set_datachannel(self, channel) -> None:
        self.datachannel = channel
        logger.info(f"[{self.session_id}] DataChannel bound to AudioSession")

    def send_transcript(self, text: str) -> None:
        if self.datachannel and self.datachannel.readyState == "open":
            try:
                self.datachannel.send(text)
                logger.info(f"[{self.session_id}] Sent transcript over DataChannel")
            except Exception as e:
                logger.error(f"[{self.session_id}] Failed to send transcript: {e}")
        else:
            logger.warning(f"[{self.session_id}] DataChannel is not open, cannot send transcript")



    async def _transcribe_and_send(self, data: bytes) -> None:
        """Helper to send audio bytes to MCP STT tool and forward response via DataChannel."""
        if not data:
            return

        try:
            # 1. Create in-memory WAV file from raw PCM bytes
            wav_io = io.BytesIO()
            with wave.open(wav_io, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(data)
            wav_bytes = wav_io.getvalue()

            # 2. Encode to base64 for JSON serialization
            base64_audio = base64.b64encode(wav_bytes).decode('utf-8')

            # 3. Connect to the MCP Server running on port 8005
            from ApiKeyGenerator import api_key_generator
            generator = api_key_generator()
            api_key = generator.generate_api_key()

            async with sse_client(
                "http://localhost:8005/sse" , headers={"X-API-Key": api_key}
                ) as (read, write):
                async with ClientSession(read, write) as mcp_session:
                    await mcp_session.initialize()
                    
                    # 4. Call the stt tool
                    response = await mcp_session.call_tool("stt", {"audio_bytes": base64_audio})
                    
                    # 5. Extract text and send to frontend
                    if response and response.content:
                        text = response.content[0].text
                        logger.info(f"[{self.session_id}] MCP STT result: '{text}'")
                        self.send_transcript(text)
        except Exception as e:
            logger.error(f"[{self.session_id}] Failed to transcribe audio via MCP STT: {e}")

