# TalentAcquire™ AI Interview Assistant: Real-Time Voice Agent & STT Pipeline

[![Continuous Integration](https://github.com/zkzkGamal/AI-RTC-Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/zkzkGamal/AI-RTC-Agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](#server-python-setup)
[![Node Version](https://img.shields.io/badge/Node-18%2B-green.svg)](#client-react-setup)
[![FastMCP](https://img.shields.io/badge/MCP-FastMCP-orange.svg)](#mcp-speech-to-text-server)

An enterprise-grade real-time voice streaming and AI conversational transcription system. It establishes high-fidelity **WebRTC** media channels between a **React (Vite)** frontend and a **Python (aiortc)** signaling backend, performs local sliding-window **Voice Activity Detection (VAD)**, transcribes speech boundaries using a **FastMCP Whisper STT Server**, and streams conversational transcripts back to a premium HR interview dashboard over an out-of-band WebRTC **DataChannel**.

---

## 🎯 System Architecture

The following block diagram illustrates the asynchronous lockstep pipeline, from browser capture to Whisper transcription and back-channel streaming:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CLIENT: React Frontend                          │
│                                                                        │
│   ┌─────────────────────────┐             ┌────────────────────────┐   │
│   │   User Media Capture    │             │   TalentAcquire™ UI    │   │
│   │   (48kHz Stereo/Mono)   │             │   Dialogue Timeline    │   │
│   └────────────┬────────────┘             └───────────▲────────────┘   │
└────────────────┼──────────────────────────────────────┼────────────────┘
                 │ (WebRTC Audio Stream)                │ (Out-of-band DataChannel)
                 │                                      │
┌────────────────┼──────────────────────────────────────┼────────────────┐
│                ▼        SERVER: WebRTC Backend        │                │
│   ┌─────────────────────────┐             ┌───────────┴────────────┐   │
│   │  _consume_audio_track   │             │    send_transcript     │   │
│   │   Slices Mono Channel   │             │   Pushes Text to DC    │   │
│   └────────────┬────────────┘             └───────────▲────────────┘   │
│                │ (Interleaved-Safe Bytes)             │                │
│                ▼                                      │                │
│   ┌─────────────────────────┐                         │                │
│   │  AudioSession.add_frame │                         │                │
│   │    16kHz VAD / 48kHz    │                         │                │
│   │  Lockstep Synchronizer  │                         │                │
│   └────────────┬────────────┘                         │                │
│                │ (2.0s Silence Offset Detected)       │                │
│                ▼                                      │                │
│   ┌─────────────────────────┐             ┌───────────┴────────────┐   │
│   │   WAV Header Builder    │             │   _transcribe_and_send │   │
│   │   Saves .wav to Disk    │             │   MCP SSE SSE Client   │   │
│   └────────────┬────────────┘             └───────────▲────────────┘   │
└────────────────┼──────────────────────────────────────┼────────────────┘
                 │ (Base64 WAV Payload)                 │
                 ▼                                      │
┌───────────────────────────────────────────────────────┼────────────────┐
│             MCP: FastMCP Speech-to-Text Server        │                │
│                                                       │                │
│   ┌─────────────────────────┐             ┌───────────┴────────────┐   │
│   │  Base64 Auto-Decoding   │────────────>│ Whisper "small" Model  │   │
│   │  Pre-Processor Bypass   │             │   Transcribe Engine    │   │
│   └─────────────────────────┘             └────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Technical Highlights & Algorithmic Solutions

### 1. Dual-Buffer Lockstep VAD Synchronization
To prevent **half-speed, distorted, or slow-motion audio playback**, the system processes high-fidelity audio and downsampled VAD frames in perfect synchronization:
- **Downsampling (3:1 Decimation)**: Raw incoming 48kHz audio is decimated to 16kHz for analysis.
- **Perfect Lockstep Alignment**: Accumulates 30ms VAD frames (`960` bytes) and raw 48kHz frames (`2880` bytes) concurrently. The VAD consumes exactly 30ms of downsampled data as the raw recorder consumes exactly 30ms of high-fidelity data. This eliminates frame mismatch, overlap, and speed duplication.

### 2. Interleaved Stereo Slicing
WebRTC browsers often stream dual-channel interleaved audio (`[L1, R1, L2, R2...]`). Manual extraction of one channel without considering the channel stride results in playing back dual-channel information at half-speed. The backend implements correct strided stereo-to-mono extraction:
```python
# Extract one channel cleanly based on channel count
mono_samples = audio_array[0][::channel_count]
pcm_bytes = mono_samples.tobytes()
```
This preserves the original pitch and native playback speed.

### 3. Base64 Auto-Decoding Bypass in FastMCP
FastMCP's Pydantic validation handles binary `bytes` arguments by converting JSON-RPC base64 strings into ASCII characters contained in a `bytes` object (e.g., `b"UklGR..."` representing the base64 characters) rather than decoded binary.
The STT server implements an auto-decoding bypass that detects base64 patterns (like matching `b"UklGR"` or decoding strings to check for the WAV `RIFF` signature), resolving FFmpeg decoder errors (`Invalid data found when processing input`).

### 4. 2.0s Silence-Triggered Automated Transcription
Rather than relying on resource-intensive periodic background timers, the transcription pipeline is entirely **reactive**. When the candidate completes a sentence, the VAD state machine starts a countdown. If silence is maintained for **2.0 seconds**, the audio buffer is saved, packaged into a WAV, and transcribed via the FastMCP STT client.

---

## 🎨 Enterprise HR Recruitment Dashboard (TalentAcquire™)
The React client is structured as a premium **HR Interview Assistant Dashboard**:
- **Control Panel**: Hosts candidate metadata, interactive audio-responsive pulsing ring visualizers, connection switches, and signaling status indicators.
- **Scrollable Timeline**: Keeps a permanent conversational transcript record (rather than overwriting). Each speech block is rendered with a candidate avatar, speaker name, dialogue index, and exact local timestamp (e.g. `10:32:15 AM`).
- **Modern Glassmorphic styling**: Uses clean dark themes (`#060814` to `#0b0f19`), responsive css-grid alignment, slide-in animation entries, and modern custom scrollbars.

---

## 📁 Repository Structure

```
AI-RTC-Agent/
├── .github/workflows/         # Continuous Integration Pipelines
│   └── ci.yml                # Parallel build and test GitHub Action
├── client/                    # React (Vite) Frontend
│   ├── src/
│   │   ├── components/       # Visualizer, status displays, and controls
│   │   ├── services/         # WebRTC and API connection adapters
│   │   ├── App.jsx           # Core orchestrator and timeline log
│   │   └── App.css           # Slate dark theme glassmorphism styling
│   └── package.json          # Node scripts and dependencies
├── server/                    # Python WebRTC & Media Backend
│   ├── tests/                # VAD & synchronization unit tests
│   ├── audio_processor.py    # AudioSession: lockstep VAD, MCP Client, and VAD hysteresis
│   ├── main.py               # signaling, track consumer, and WebRTC server
│   └── requirements-dev.txt  # Python requirements and testing setup
├── mcp/                       # Model Context Protocol STT Server
│   ├── tests/                # Module-patched FastMCP unit tests
│   ├── tools/stt/stt.py      # Whisper STT tool & base64 decoder
│   ├── server.py             # FastMCP application setup
│   ├── main.py               # Run FastMCP via SSE transport on port 8005
│   └── requirements-dev.txt  # MCP developer & test tools
└── README.md                  # This file
```

---

## 🚀 Quick Start Instructions

To run the full stack locally, follow these instructions. Open three separate terminal windows:

### Window 1: Start the FastMCP Whisper Server
Make sure you have `ffmpeg` installed on your system.
```bash
cd mcp
pip install -r requirements-dev.txt
python main.py
```
*The server will start on port `8005`, exposing SSE endpoints at `http://localhost:8005/sse`.*

### Window 2: Start the WebRTC Signaling Backend
```bash
cd server
pip install -r requirements-dev.txt
python main.py
```
*The server starts on port `8080`, listening for session and SDP exchange requests.*

### Window 3: Start the React Client App
```bash
cd client
npm install
npm run dev
```
*The client dev server starts on `http://localhost:5173` (or `http://localhost:3000`).*

### Usage Flow:
1. Open the React app in your browser (`http://localhost:5173`).
2. Click **Start Connection** and accept the microphone prompt.
3. Speak naturally. The pulsing rings around the candidate avatar will ripple.
4. Stop speaking. After exactly **2.0 seconds of silence**, the segment is transcribed and appended to the **Live Interview Transcript** timeline with its timestamp.

---

## 🧪 Testing & CI/CD Pipeline

The repository includes comprehensive unit testing frameworks that run concurrently on every push or pull request via **GitHub Actions**.

### 1. WebRTC Backend Tests
Verifies correct lockstep decimation, sliding VAD windows, and state machine integrity:
```bash
cd server
python -m pytest tests/ -v
```

### 2. MCP Server Tests
Verifies the Whisper `stt` tool using direct module-level patching (`sys.modules`) to mock the neural network engine, ensuring fast unit tests that run without GPU hardware:
```bash
cd mcp
python -m pytest tests/ -v
```

---

## ⚙️ Configuration Variables (`.env`)

Configure settings by creating `.env` files in `server/` and `mcp/` directories:

```bash
# Server Settings
SERVER_HOST=0.0.0.0
SERVER_PORT=8080
LOG_LEVEL=INFO

# Audio & VAD Settings
AUDIO_SAMPLE_RATE=48000
SILENCE_THRESHOLD=2.0
VAD_AGGRESSIVENESS=3

# Client Config
VITE_SERVER_URL=http://localhost:8080
```

---

## 🗺️ Project Roadmap

- [x] **WebRTC Audio Streaming** — High-fidelity mono channel streaming.
- [x] **Lockstep Frame VAD Sync** — Zero slow-motion or sample duplicates.
- [x] **React HR Dashboard** — Premium TalentAcquire™ visual timeline.
- [x] **FastMCP Whisper STT** — Silence-triggered reactive transcription.
- [x] **GitHub Actions CI** — Multi-job validation suite.
- [ ] **Multi-Speaker Diarization** — Separating interviewer vs. candidate.
- [ ] **LLM Orchestrator** — Live evaluation and real-time response generation.
- [ ] **Outbound Audio (TTS)** — Streaming synthesized voice responses back to browser WebRTC audio tracks.

---

**Last Updated:** May 2026  
**Status:** Main Production Integrations Complete & Verified  
**Author:** [zkzkGamal](https://github.com/zkzkGamal)  
**License:** MIT  
