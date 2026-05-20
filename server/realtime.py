import sys
import time
import threading
import queue
import numpy as np
import pyaudio
import webrtcvad
import whisper

# ----------------------------------------------------------------------
# Audio configuration
# ----------------------------------------------------------------------
FORMAT = pyaudio.paInt16        # 16-bit PCM
CHANNELS = 1                    # mono
RATE = 16000                    # 16 kHz – required by webrtcvad
FRAME_DURATION_MS = 30          # VAD works on 10, 20 or 30 ms frames
CHUNK = int(RATE * FRAME_DURATION_MS / 1000)  # samples per frame

# VAD aggressiveness (0=least aggressive, 3=most aggressive)
VAD_MODE = 3

# Minimum speech segment length (seconds) – ignore very short noises
MIN_SPEECH_SEC = 0.5
MIN_SPEECH_FRAMES = int(MIN_SPEECH_SEC * 1000 / FRAME_DURATION_MS)

# Silence padding to add before/after a speech segment (seconds)
PAD_SEC = 0.3
PAD_FRAMES = int(PAD_SEC * 1000 / FRAME_DURATION_MS)

# Whisper model: 'tiny', 'base', 'small', 'medium', 'large'
WHISPER_MODEL = 'base'

# ----------------------------------------------------------------------
# Initialisation
# ----------------------------------------------------------------------
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

# ----------------------------------------------------------------------
# State for speech collection
# ----------------------------------------------------------------------
speech_frames = []          # frames of the current speech segment
in_speech = False           # currently inside a speech region
silence_frames = 0          # consecutive silence frames after speech ended
segment_queue = queue.Queue()  # queue of audio segments ready for transcription

# ----------------------------------------------------------------------
# Transcription worker (runs in background)
# ----------------------------------------------------------------------
def transcribe_worker():
    """Pull audio segments from queue, transcribe, and print."""
    while True:
        audio_bytes, timestamp = segment_queue.get()
        if audio_bytes is None:   # sentinel to stop
            break

        # Convert bytes to numpy float32 array (Whisper expects [-1,1])
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        # Transcribe
        result = model.transcribe(audio_np, language='en', fp16=False)
        text = result['text'].strip()
        if text:
            print(f"[{timestamp:.1f}s] {text}")

# Start the worker thread
worker_thread = threading.Thread(target=transcribe_worker, daemon=True)
worker_thread.start()

# ----------------------------------------------------------------------
# Main capture loop
# ----------------------------------------------------------------------
def collect_frames():
    """Read frames from the microphone and feed them to the VAD state machine."""
    global in_speech, speech_frames, silence_frames

    while True:
        try:
            frame = stream.read(CHUNK, exception_on_overflow=False)
        except OSError:
            continue   # ignore overflows

        is_speech = vad.is_speech(frame, RATE)

        # --------------------------------------------------------------
        # State machine: detect speech onset and offset
        # --------------------------------------------------------------
        if is_speech:
            if not in_speech:
                # Speech just started
                in_speech = True
                speech_frames = []          # new segment
            speech_frames.append(frame)
            silence_frames = 0

        else:  # silence
            if in_speech:
                # We are still inside a speech segment – add silence frames
                speech_frames.append(frame)
                silence_frames += 1

                # If enough silence after speech, end the segment
                if silence_frames >= PAD_FRAMES and len(speech_frames) >= MIN_SPEECH_FRAMES:
                    # Segment ended
                    in_speech = False

                    # Extract complete audio (including silence padding already added)
                    segment_bytes = b''.join(speech_frames)
                    timestamp = time.time()
                    segment_queue.put((segment_bytes, timestamp))

                    speech_frames = []
                    silence_frames = 0

            else:
                # Outside speech – just ignore
                pass

# ----------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------
try:
    collect_frames()
finally:
    # Cleanup
    segment_queue.put((None, None))   # stop worker
    worker_thread.join(timeout=1.0)
    stream.stop_stream()
    stream.close()
    audio.terminate()