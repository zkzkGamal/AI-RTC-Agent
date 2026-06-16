# Client: TalentAcquire™ AI Interview Assistant (Vite + React)

A premium, state-of-the-art React web interface styled for modern HR recruitment, offering high-fidelity real-time voice streaming to the WebRTC backend, live silence-triggered transcription via WebRTC `DataChannel`, and a historical conversation timeline.

---

## 🎯 Purpose & Core Features

`TalentAcquire™ AI Interview Assistant` is an enterprise-grade HR recruiting dashboard that manages the frontend voice capturing and displaying of candidate interactions:

- **Two-Column HR Dashboard**:
  - **Left Panel (Control Center)**: Features media connection status toggles, candidate credentials, real-time parameters, and interactive visualizers.
  - **Right Panel (Live Interview Timeline)**: Renders a scrollable conversational feed containing historical candidate dialogue blocks.
- **WebRTC Data Channel Integration**: Automatically establishes an out-of-band `'transcript'` `DataChannel` upon starting the connection, receiving back-channel text transcripts dynamically pushed by the backend.
- **CV Upload (HR Mode)**: A **📎 CV** button beside the chat composer uploads a candidate résumé (PDF, Word, or Markdown) to the agent. The file is parsed into a persistent CV memory and the agent immediately reviews it — replies are then grounded in the candidate's CV.
- **Auto-Scrolling Dialog Timeline**: Displays transcripts chronologically without overwriting. Each transcript block includes:
  - Precise timestamp rendering (e.g. `10:32:15 AM`) based on local user time.
  - Segment index badge (e.g. `Segment #1`) for conversational auditing.
  - Distinct candidate avatar icon and visual speaker indicators.
  - Auto-scroll-into-view behavior to keep the latest dialogue block visible.
- **Rich Aesthetics**: Deep dark slate palette (`#060814` to `#0b0f19`) featuring glowing green status indications, glassmorphism panel blur effects (`backdrop-filter`), smooth hover transitions, and clean typography (Inter / Outfit).

---

## 🛠️ Technology Stack

- **Framework:** React 18 (Functional Components & custom hooks)
- **Build System:** Vite 5 (extremely fast bundle execution under 700ms)
- **Styling:** Premium Custom Vanilla CSS (no framework wrappers, custom CSS variables)
- **WebRTC:** Native browser `RTCPeerConnection` API (audio tracks + custom data channels)
- **APIs:** Async Fetch API for session handshakes

---

## 📁 Project Structure

```
client/
├── dist/                          # Production-ready build assets
├── src/
│   ├── components/
│   │   ├── AudioVisualizer.jsx    # Pulsing microphone ring synced with active stream
│   │   ├── ControlButtons.jsx     # Modern Start/Stop buttons with tactile transitions
│   │   └── StatusDisplay.jsx      # Session identity, state monitors, and error logs
│   ├── services/
│   │   ├── api.js                 # API abstraction (createSession, sendOffer)
│   │   └── webrtc.js              # Native RTCPeerConnection & DataChannel setup
│   ├── App.jsx                    # Core layout orchestrator, timeline state, and auto-scroll
│   ├── App.css                    # Modern global CSS styles (glassmorphic dark design)
│   └── main.jsx                   # React entrypoint
├── index.html                     # HTML head structure with font loaders
├── package.json                   # Project dependencies and script maps
├── vite.config.js                 # Vite custom port/proxy configuration
└── README.md                      # This file
```

---

## 🚀 Quick Start

### 1. Install Dependencies
Ensure you have **Node.js 18+** installed:
```bash
cd client
npm install
```

### 2. Run the Development Server
Starts the Vite dev server locally:
```bash
npm run dev
```
By default, the client launches at `http://localhost:3001` (per custom configuration in `vite.config.js`).

> [!NOTE]
> Make sure the Python signaling backend is running on `http://localhost:8080` before clicking **Start Connection**.

### 3. Compile Production Bundle
Validates types and outputs compressed, optimized static assets:
```bash
npm run build
```
*Expected compilation time: ~600-800ms with zero errors.*

---

## 🔌 Architecture & Flow

### Component & Data Relationship

```
App.jsx (Main Layout + Timeline Log State)
  ├── services/api.js              → REST Session & Offer Handshakes
  ├── services/webrtc.js           → WebRTC Connection & DataChannel Listener
  ├── components/AudioVisualizer   → Displays pulsing ring if connection is active
  ├── components/StatusDisplay     → Shows UUID, state badges, and diagnostic logs
  └── components/ControlButtons    → Manages interactive start/stop hooks
```

### Sequence Flow

```
1. Client clicks "Start Connection"
2. api.createSession()                 → GET /session  → returns session_id (UUID)
3. webrtc.createConnection()           → Asks mic permission & constructs RTCPeerConnection
4. webrtc.js establishes DataChannel   → Creates channel named 'transcript'
5. api.sendOffer(session_id, offer)    → POST /session/{id}/offer → receives SDP answer
6. webrtc.applyAnswer(answer)          → Audio begins streaming (48kHz mono PCM)
7. Candidate Speaks                    → Backend detects VAD speech and 2.0s silence boundary
8. Backend transcribes via FastMCP     → Sends WAV bytes to Whisper STT tool
9. Backend sends text to DataChannel   → `transcript` data channel receives payload
10. App.jsx callback triggers          → Appends new block with timestamp, triggers auto-scroll
11. Client clicks "Stop Connection"    → Tears down tracks and closes peer connection
```

---

## ⚙️ Services API

### `services/api.js`

| Function | Endpoint | Description |
| :--- | :--- | :--- |
| `createSession()` | `GET /session` | Initializes a unique session on the signaling backend, returning a UUID. |
| `sendOffer(id, offer)` | `POST /session/{id}/offer` | Sends the local WebRTC Session Description Protocol (SDP) offer and returns the server's answering SDP. |
| `sendChatMessage(userId, sessionId, message)` | `POST /api/chat` | Sends a text turn to the FastAPI agent (Port 8001) and returns its response + any pending HIL confirmation. |
| `uploadCv(userId, file)` | `POST /api/cv/upload` | Uploads a candidate CV (PDF / Word / Markdown) to the agent's `content/` folder, parses it, and stores per-user CV memory. |

### `services/webrtc.js`

| Function | Parameters | Description |
| :--- | :--- | :--- |
| `createConnection(onStateChange, onMessage)` | `onStateChange: fn`, `onMessage: fn` | Captures microphone audio at a requested rate, initializes the `RTCPeerConnection`, hooks up the `'transcript'` `DataChannel`, registers message event listeners, and builds the local SDP offer. |
| `applyAnswer(pc, answer)` | `pc: RTCPeerConnection`, `answer: SDP` | Sets the remote description, initiating the media stream. |
| `closeConnection(pc, stream)` | `pc: RTCPeerConnection`, `stream: MediaStream` | Safely stops all microphone tracks, closes the peer connection, and clears memory. |

---

## 🎨 Enterprise Styling Details

- **Responsive Dashboard Grid**: Tailored side-by-side workspace ensuring no layout shifting when transcripts are dynamically loaded.
- **Glassmorphism Base Card**: Uses smooth, backdropped gradients (`rgba(255, 255, 255, 0.03)` with a `24px` backdrop blur) coupled with thin borders to mimic sleek high-end macOS cards.
- **Micro-Animations**:
  - Fade-and-slide keyframe entries for dialogue bubbles to mimic natural chat feeds.
  - Hover glow borders on button modules.
  - Pulsing animated rings around the candidate avatar indicating real-time mic streaming.
- **Tailored CSS Scrollbars**: Sleek, thin scrollbar rails designed directly in `App.css` to match the dark slate aesthetic.

---

## 📖 Related Documentation

- [Main Workspace README](../README.md) – End-to-end overview
- [Server Backend README](../server/README.md) – VAD processing & WebRTC server
- [MCP Server README](../mcp/README.md) – FastMCP Whisper transcription tool

---

**Version:** 1.0.0  
**Status:** Completed & Integrated  
**Last Updated:** May 2026
