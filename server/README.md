# Server: AI-RTC-Agent Backend (Python & WebRTC)

A high-performance asynchronous Python backend responsible for managing real-time WebRTC audio connections, executing Voice Activity Detection (VAD) in lockstep, automatically segmenting active speech, transcribing audio via FastMCP Whisper STT, and streaming live transcripts back to the client over an out-of-band WebRTC `DataChannel`.

---

## 🎯 Core Features & Capabilities

- **Real-Time WebRTC Media Consumption**: Receives incoming high-fidelity browser microphone audio streams using `aiortc` and aiohttp.
- **Dual-Buffer Lockstep VAD Processing**:
  - Eliminates slow-motion/half-speed audio distortions by synchronizing high-fidelity audio buffers (`_input_buffer_raw` at 48kHz) with downsampled VAD buffers (`_input_buffer_16k` at 16kHz) in perfect 30ms lockstep.
  - Consumes exactly 30ms of VAD audio (`960` bytes) concurrently with 30ms of raw audio (`2880` bytes), preventing any frame overlap, duplicating, or sample shifting.
- **Interleaved Stereo Slicing**: Cleans dual-channel interleaved audio tracks by applying precise slicing (`mono = audio[0][::channels]`), capturing a single clean channel at native pitch and playback speed.
- **2.0s Silence-Triggered Automated Transcription**:
  - The periodic background polling timer has been completely removed.
  - Transcription is strictly triggered upon natural speech completion (detected when the candidate is silent for exactly **2.0 seconds** after active speech).
  - Uses `webrtcvad` (aggressiveness mode 3) inside a sliding window state-machine for highly robust onset (speech start) and offset (speech end) detection.
- **Out-of-band DataChannel Delivery**: Sends live transcriptions directly to the client via an active WebRTC `DataChannel` named `'transcript'`, bypassing standard HTTP request/response latency.
- **Integrated FastMCP Client**: Automatically wraps accumulated speech segments in a valid `.wav` byte stream, encodes it to base64, establishes a Server-Sent Events (SSE) connection to the FastMCP Whisper server at `http://localhost:8005/sse`, invokes the `"stt"` tool, and decodes the result.

---

## 📁 Project Structure

```
server/
├── tests/                 # Server frame-synchronization & VAD test suite
│   ├── test_vad.py        # Validates VAD thresholds and downsampling decimation
│   └── ...
├── utterances/            # Session-isolated directory for saved WAV recordings
│   └── <session_id>/
│       ├── utt_<timestamp>.wav
│       └── ...
├── audio_processor.py     # AudioSession: downsampling, lockstep VAD, MCP client
├── main.py                # aiohttp signaling, CORS handler, and track consumer
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies (pytest, etc.)
└── README.md              # This file
```

---

## 🚀 Quick Start

### 1. Install Dependencies
Make sure you have **Python 3.10+** installed:
```bash
cd server
pip install -r requirements.txt
```

### 2. Start the Server
Run the asynchronous server locally:
```bash
python main.py
```
By default, the server binds to `http://localhost:8080`.

### 3. Run Automated Backend Tests
Ensure the lockstep VAD decimation and state machine remain perfectly calibrated:
```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```
*Expected test output: 100% passing tests.*

---

## ⚙️ Audio Pipeline Architecture

```
Opus-Encoded Mic Stream (Browser)
       ↓ (WebRTC PeerConnection)
av.AudioFrame (48kHz Interleaved Stereo/Mono)
       ↓
Interleaved Slicing: mono = audio[0][::channels] (main.py)
       ↓
AudioSession.add_frame(pcm_bytes) (audio_processor.py)
       ├───> Downsample to 16kHz via 3:1 decimation
       ├───> Append to VAD Buffer (16kHz) & Raw Buffer (48kHz)
       ↓
Lockstep processing loop (30ms chunks: 960 bytes VAD vs 2880 bytes Raw)
       ├───> VAD onset (active frames >= 6/10) → speaking = True
       ├───> VAD offset (active frames <= 1/10) → start 2.0s silence countdown
       ↓
Silence Threshold (2.0s) Reached
       ├───> Wrap raw PCM bytes in a valid WAV header
       ├───> Save WAV segment to disk in 'utterances/<session_id>/'
       ├───> Encode WAV to Base64
       ├───> Connect to FastMCP STT Server (localhost:8005/sse)
       ├───> Call 'stt' tool → Retrieve Whisper text
       └───> Send text over WebRTC 'transcript' DataChannel to browser
```

---

## 🔌 API Endpoints & Protocols

### 1. HTTP Endpoints

#### `GET /session`
Creates a brand-new audio session and allocates disk space.
- **Response:**
  ```json
  {
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
  ```

#### `POST /session/{session_id}/offer`
Negotiates WebRTC connection details by exchanging SDP envelopes.
- **Request:**
  ```json
  {
    "sdp": "v=0\no=...",
    "type": "offer"
  }
  ```
- **Response:**
  ```json
  {
    "sdp": "v=0\no=...",
    "type": "answer"
  }
  ```

### 2. WebRTC Data Channel Protocol
Upon connection, the server listens for data channel handshakes. If a channel named `'transcript'` is opened by the client, it is bound to the user's `AudioSession`. When Whisper transcriptions are completed, they are pushed over this channel:
- **Event**: `onmessage`
- **Data Payload**: `str` (the transcribed text)

---

## ⚙️ Core Configuration Variables

| Parameter | Default Value | Description |
| :--- | :--- | :--- |
| `sample_rate` | `48000` | Target incoming WebRTC PCM audio rate (Hz). |
| `silence_threshold` | `1.0` | Seconds of continuous silence before transcribing. |
| `VAD_SAMPLE_RATE` | `16000` | Sample rate used for VAD analysis (Hz). |
| `VAD_FRAME_DURATION_MS` | `30` | Duration of each VAD classification frame (ms). |
| `VAD_WINDOW_SIZE` | `10` | Number of recent frames stored in the sliding hysteresis window. |
| `M_ONSET` | `6` | Minimum active speech frames in the window to trigger speech onset. |
| `M_OFFSET` | `1` | Maximum active speech frames in the window to start silence countdown. |

---

## 📖 Related Documentation

- [Main Workspace README](../README.md) – System-wide overview
- [Client Frontend README](../client/README.md) – React TalentAcquire UI
- [MCP Server README](../mcp/README.md) – Whisper STT Tool and FastMCP architecture

---

**Version:** 1.0.0  
**Status:** Completed & Fully Tested  
**Last Updated:** May 2026
