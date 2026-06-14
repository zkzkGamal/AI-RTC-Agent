# Development Setup & Installation Guide ⚙️

This document details the environment configuration, package installation steps, run instructions, and testing workflows required to build and run the AI-RTC-Agent workspace.

---

## 📋 System Prerequisites

Ensure your host machine has the following tools installed before beginning configuration:

### 1. Python 3.10 or Higher
Python is required to run the WebRTC server, FastAPI Agent, and FastMCP server.
- **Ubuntu/Debian**: `sudo apt update && sudo apt install python3 python3-pip python3-venv -y`
- **macOS**: `brew install python`
- **Windows**: Download and run the official Python installer (make sure to select "Add Python to PATH").

### 2. Node.js (v18+) & NPM (v9+)
Node is required to compile and serve the Vite React frontend.
- **Ubuntu/Debian**: Use NodeSource or run `sudo apt install nodejs npm -y`
- **macOS**: `brew install node`
- **Windows**: Download and run the official installer from [nodejs.org](https://nodejs.org/).

### 3. FFmpeg
FFmpeg is required by Whisper to read, slice, and transcribe audio files. **The FastMCP server will throw execution errors if FFmpeg is missing.**
- **Ubuntu/Debian**: `sudo apt update && sudo apt install ffmpeg -y`
- **macOS**: `brew install ffmpeg`
- **Windows**: Download compiled binaries from [ffmpeg.org](https://ffmpeg.org/), extract, and add the `bin/` folder to your system Environment `PATH`.

---

## 🚀 Unified Quick Start (Recommended)

The easiest way to run the application is to use our unified orchestrator script, which validates dependencies, sets up config templates, and spins up all 4 microservices:

1. Clone the repository and navigate to the directory:
   ```bash
   git clone <repository_url>
   cd AI-RTC-Agent
   ```

2. Install all Python dependencies inside a local virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Install React frontend modules:
   ```bash
   cd client
   npm install
   cd ..
   ```

4. Launch the application stack:
   ```bash
   ./start.sh
   ```
   *This script runs all 4 microservices concurrently, checks prerequisites, captures and streams stdout/stderr output to log files inside the `logs/` directory (while also echoing to the console), performs `curl` status loops to confirm all services are fully initialized, and automatically opens your default web browser to the React client at `http://localhost:3001`. Press `Ctrl+C` to cleanly shut down all services.*

---

## 📁 Log Files Directory (`logs/`)

When you boot the application using `./start.sh`, the standard outputs and errors of each microservice are piped to files in the `logs/` directory:
- `logs/mcp_app.log`: Output from the FastMCP Server (Port 8005) showing model loading, tool definitions, and OAuth checks.
- `logs/agent.log`: Output from the FastAPI Agent Layer (Port 8001) showing LangGraph routing, memory sessions, and Socket.IO connections.
- `logs/server.log`: Output from the WebRTC Backend Server (Port 8080) showing SDP handshake logs and VAD frame counts.
- `logs/client.log`: Output from the Vite Client Dev Server (Port 3001) showing bundling status and connection listening states.


---

## 🔧 Manual Step-by-Step Execution

If you prefer to run the components individually for debugging or localized development, follow the startup order below. Make sure you activate your python virtual environment in each terminal window.

### Step 1: Start the FastMCP Server (Port 8005)
The FastMCP server serves Whisper speech-to-text, Web Search, and Google OAuth tools.
```bash
cd mcp_app
# 1. Create and configure environment variables
cp .env.example .env
# 2. Add credentials.json and run the OAuth handshake (if using Mail/Calendar tools)
python3 get_token.py
# 3. Start the server
python3 main.py
```
> [!NOTE]
> On startup, the FastMCP server preloads the Whisper `small` model into CPU/GPU memory to eliminate cold-start lag during the first user audio segment.

### Step 2: Start the FastAPI Agent (Port 8001)
The Agent tracks the LangGraph state machine, connects to LLMs, and communicates live tool execution states over Socket.IO.
```bash
cd agent
# 1. Create and configure environment variables
cp .env.example .env
# 2. Run the interactive console or spin up the API server
# Usage: ./runner.sh
# Follow the interactive menus to configure AGENT_MODE and start the API server on Port 8001.
```

### Step 3: Start the WebRTC Backend (Port 8080)
The WebRTC server handles real-time SDP negotiation, ingests raw microphone streams, segments audio based on Voice Activity Detection (VAD), and sends transcripts.
```bash
cd server
python3 main.py
```

### Step 4: Start the React Frontend (Port 3001)
The frontend connects the browser's audio stream to the WebRTC server, connects to the Agent's Socket.IO server, and renders the UI dashboard.
```bash
cd client
npm install
npm run dev
```

---

## ⚙️ Environment Variables Config Reference

### 1. FastMCP Environment File (`mcp_app/.env`)
| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `MAIL_HOST` | `smtp.gmail.com` | Outbound SMTP server address. |
| `MAIL_PORT` | `587` | Outbound SMTP port. |
| `MAIL_USERNAME` | `""` | Outbound sender email address. |
| `MAIL_PASSWORD` | `""` | Gmail App Password (not your primary password). |
| `MAIL_ENCRYPTION` | `tls` | SMTP encryption protocol. |
| `GMAIL_TOKEN_FILE` | `token.json` | Relative path to local Gmail/Calendar OAuth token storage. |
| `GMAIL_SENDER` | `""` | Matches the Gmail account associated with the OAuth token. |

### 2. FastAPI Agent Environment File (`agent/.env`)
| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Base URL of local Ollama installation. |
| `OPENAI_API_KEY` | `""` | OpenAI API developer key (if using OpenAI model). |
| `GOOGLE_API_KEY` | `""` | Google Gemini API developer key (if using Gemini model). |
| `AGENT_MODE` | `hr` | Mode persona selection (`general`, `hr`, `developer`, `research`). |
| `MODEL_TYPE` | `ollama` | Model driver selection (`ollama`, `openai`, `gemini`). |
| `LLM_MODEL` | `qwen3.5:0.8b` | Exact model name/tag to load in chosen driver. |
| `OLLAMA_REASONING`| `False` | Enables/Disables structured reasoning wrappers. |

---

## 🧪 Testing & Code Verification

The repository includes test suites to verify transcription pipelines, voice activity segmentation, and agent tool execution.

### 1. Test the FastMCP Tools Layer
Validates Whisper transcription, SMTP configuration, calendar generation, and rate limits:
```bash
cd mcp_app
pytest tests/ -v
```

### 2. Test the WebRTC VAD Backend
Validates downsampling, PCM-to-WAV conversion, and speech detection logic:
```bash
cd server
pytest tests/ -v
```

### 3. Test the FastAPI Agent
The FastAPI Agent contains an interactive test runner. Execute `./runner.sh`, select the `test` option, and choose which test file to execute.

---

## 🔍 Troubleshooting Tips

### 1. Port is Already in Use (`OSError: [Errno 98] Address already in use`)
If a service was terminated abruptly, its port might remain bound. Find and kill the process:
```bash
# Search for the process binding the port
sudo lsof -i :8080   # Replace with 8001, 8005, or 3001
# Terminate the process
kill -9 <PID>
```

### 2. Whisper Transcription Errors / Slow Speeds
- **Missing ffmpeg**: If you see errors about `ffmpeg` or `ffprobe` not found, verify that `ffmpeg` is successfully installed on your system PATH.
- **CPU Bottlenecks**: Whisper defaults to CPU-based inference if PyTorch was installed without CUDA support. Ensure your host machine has sufficient CPU allocation or update PyTorch to reference CUDA libraries.

### 3. Google OAuth Redirect Failures
- Verify that your Gmail email address is added to the **Test Users** section in the Google Cloud Console.
- If you change the authorized scopes in `get_token.py`, delete the existing `token.json` file inside `mcp_app/` and run `python3 get_token.py` to regenerate the token.
