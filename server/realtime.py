"""server.realtime module."""

import sys
import time
import threading
import queue
import numpy as np
import pyaudio
import webrtcvad
import whisper

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
FRAME_DURATION_MS = 30
CHUNK = int(RATE * FRAME_DURATION_MS / 1000)

VAD_MODE = 3

MIN_SPEECH_SEC = 0.5
MIN_SPEECH_FRAMES = int(MIN_SPEECH_SEC * 1000 / FRAME_DURATION_MS)

PAD_SEC = 0.3
PAD_FRAMES = int(PAD_SEC * 1000 / FRAME_DURATION_MS)

WHISPER_MODEL = 'base'

vad = webrtcvad.Vad(VAD_MODE)
audio = pyaudio.PyAudio()
stream = audio.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=CHUNK
)

print("Loading Whisper model... (this may take a moment)")
model = whisper.load_model(WHISPER_MODEL)
print("Ready! Speak into the microphone. Press Ctrl+C to stop.\n")

speech_frames = []
in_speech = False
silence_frames = 0
segment_queue = queue.Queue()

def transcribe_worker():
    """Pull audio segments from queue, transcribe, and print."""
    while True:
        audio_bytes, timestamp = segment_queue.get()
        if audio_bytes is None:
            break

        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        result = model.transcribe(audio_np, language='en', fp16=False)
        text = result['text'].strip()
        if text:
            print(f"[{timestamp:.1f}s] {text}")

worker_thread = threading.Thread(target=transcribe_worker, daemon=True)
worker_thread.start()

def collect_frames():
    """Read frames from the microphone and feed them to the VAD state machine."""
    global in_speech, speech_frames, silence_frames

    while True:
        try:
            frame = stream.read(CHUNK, exception_on_overflow=False)
        except OSError:
            continue

        is_speech = vad.is_speech(frame, RATE)

        if is_speech:
            if not in_speech:
                in_speech = True
                speech_frames = []
            speech_frames.append(frame)
            silence_frames = 0

        else:
            if in_speech:
                speech_frames.append(frame)
                silence_frames += 1

                if silence_frames >= PAD_FRAMES and len(speech_frames) >= MIN_SPEECH_FRAMES:
                    in_speech = False

                    segment_bytes = b''.join(speech_frames)
                    timestamp = time.time()
                    segment_queue.put((segment_bytes, timestamp))

                    speech_frames = []
                    silence_frames = 0

            else:
                pass

try:
    collect_frames()
finally:
    segment_queue.put((None, None))
    worker_thread.join(timeout=1.0)
    stream.stop_stream()
    stream.close()
    audio.terminate()