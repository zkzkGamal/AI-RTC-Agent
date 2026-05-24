# AI-RTC-Agent

Real-time voice agent workspace built around four parts:

- `client/` React frontend for the interview UI
- `server/` Python WebRTC backend for audio streaming and VAD
- `mcp/` FastMCP server for transcription, email, and search tools
- `agent/` LLM routing and prompt orchestration layer

The project captures live microphone audio in the browser, streams it to the backend with WebRTC, detects speech boundaries, sends utterances to the MCP server for transcription, and streams transcript text back to the UI.

## Architecture

```text
Browser mic
  -> React client
  -> WebRTC connection
  -> Python server
  -> VAD + utterance segmentation
  -> MCP server
  -> Whisper STT / tool execution
  -> transcript back over DataChannel
  -> client timeline
```

## Workspace Structure

```text
AI-RTC-Agent/
├── agent/      # LLM routing, prompts, and model adapters
├── client/     # React + Vite frontend
├── mcp/        # FastMCP tool server
├── server/     # WebRTC signaling and audio pipeline
├── README.md
├── requirements.txt
└── DEVELOPMENT.md
```

## Main Features

- real-time browser-to-server audio streaming with WebRTC
- silence-based utterance segmentation with VAD
- local Whisper transcription through FastMCP
- MCP email tools for sending, reading, and replying
- DuckDuckGo search tool
- shared response, auth, rate-limit, and exception utilities in the MCP layer
- early agent package for intent routing and model abstraction

## Requirements

### System

- Python `3.10+`
- Node.js `18+`
- `ffmpeg` installed locally for Whisper audio handling

### Python

A root requirements file is included for the Python parts of the workspace:

```bash
pip install -r requirements.txt
```

This installs dependencies for:

- `server/`
- `mcp/`
- `agent/`

### Frontend

```bash
cd client
npm install
```

## Quick Start

Run the stack in this order.

### 1. Start the MCP server

```bash
cd mcp
cp .env.example .env
python main.py
```

Default address:

- `http://localhost:8005`

For Gmail inbox access and email setup, see [mcp/README.md](./mcp/README.md).

### 2. Start the WebRTC backend

```bash
cd server
python main.py
```

Default address:

- `http://localhost:8080`

### 3. Start the React client

```bash
cd client
npm run dev
```

Default address:

- `http://localhost:5173`

### 4. Use the app

1. Open the client in the browser.
2. Start the connection.
3. Allow microphone access.
4. Speak naturally.
5. After silence is detected, the backend sends the utterance to the MCP server.
6. The transcript is returned to the UI timeline.

## Component Notes

### `client/`

- Vite + React app
- opens microphone access
- creates the WebRTC connection
- receives transcripts over a WebRTC DataChannel

More details: [client/README.md](./client/README.md)

### `server/`

- handles session creation and SDP negotiation
- receives browser audio frames
- converts audio to the format used by the VAD pipeline
- segments speech after silence
- calls the MCP server for STT

More details: [server/README.md](./server/README.md)

### `mcp/`

- runs FastMCP over SSE on port `8005`
- exposes `stt`, email, and web search tools
- includes utility modules for auth, HTTP, responses, rate limiting, and exceptions

More details: [mcp/README.md](./mcp/README.md)

### `agent/`

The agent package currently contains:

- prompt loaders
- model mapping for OpenAI, Gemini, and Ollama
- basic routing and conversation node code

It is part of the repo structure, but it is not documented as the main runtime path for the voice stack yet.

More details: [agent/README.md](./agent/README.md)

## Environment Files

This repo uses local `.env` files per module instead of one shared root env:

- `mcp/.env`
- `agent/.env`

If you add server-specific configuration later, keep it local to `server/`.

## Testing

### MCP tests

```bash
cd mcp
pytest tests/ -v
```

### Server tests

```bash
cd server
pytest tests/ -v
```

## Development

For general setup and local development workflow, see [DEVELOPMENT.md](./DEVELOPMENT.md).

## License

MIT. See [LICENSE](./LICENSE).
