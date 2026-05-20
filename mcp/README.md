# MCP: Model Context Protocol Server (FastMCP & Whisper STT)

A robust Model Context Protocol (MCP) server built with **FastMCP** that exposes a high-fidelity Speech-to-Text (STT) tool. It uses OpenAI's **Whisper "small" model** to perform real-time, high-precision voice transcriptions from local WAV files or memory streams.

---

## 🎯 Features & Architectural Highlights

- **FastMCP Integration**: Exposes tools over standard Server-Sent Events (SSE) interfaces, adhering strictly to the Model Context Protocol specifications.
- **Whisper "small" Model Integration**: Performs offline, high-accuracy conversational transcriptions on incoming speech utterances.
- **Base64 Auto-Decoding Layer**:
  - FastMCP's Pydantic validation handles binary `bytes` arguments by converting the incoming JSON-RPC base64 string into a `bytes` object containing base64 ASCII character bytes (e.g. `b"UklGR..."`) rather than raw binary data.
  - The tool features a pre-processing safety layer that detects base64 headers (e.g., matching the base64 equivalent `b"UklGR"` of a WAV file's `RIFF` prefix, or dynamically validating decoded binary starts with `b"RIFF"`), auto-decoding them to raw binary bytes.
  - This prevents ffmpeg decoder errors (such as `Invalid data found when processing input`) and ensures seamless execution.
- **Isolated, Fast Mock Testing**:
  - Contains unit tests in `mcp/tests/test_audio_tools.py` that mock the Whisper model for lightning-fast continuous integration.
  - Solves the pytest import-shadowing issue (Whisper loading on module-level import) by accessing the loaded module via `sys.modules['tools.stt.stt']` and swapping out the global `model` variable for a `MagicMock`.

---

## 📁 Project Structure

```
mcp/
├── tests/
│   ├── test_audio_tools.py    # Unit tests with module-patched Whisper mocks
│   └── ...
├── tools/
│   └── stt/
│       ├── __init__.py
│       └── stt.py             # STT tool definition & base64 decoding safety layer
├── server.py                  # FastMCP instance initialisation
├── main.py                    # Entry point to run FastMCP over SSE (port 8005)
└── README.md                  # This file
```

---

## 🚀 Quick Start

### 1. Install System Prerequisites
Ensure you have **FFmpeg** installed on your system (Whisper depends on it for audio processing).
- **Ubuntu/Debian**: `sudo apt update && sudo apt install ffmpeg`

### 2. Install Project Dependencies
Use `pip` to install requirements inside the Python environment:
```bash
cd mcp
pip install -r requirements.txt
```

### 3. Start the FastMCP Server
Launches the server on port `8005` (exposing SSE endpoints at `http://localhost:8005/sse`):
```bash
python main.py
```

### 4. Run the Unit Test Suite
Verify that the STT tools and base64 parsing behave correctly:
```bash
python -m pytest tests/ -v
```
*Expected output: All tests passing in milliseconds without executing any local Whisper model inference.*

---

## 🛠️ Tool Specifications

### `stt`

Converts incoming raw or base64-encoded WAV audio bytes into transcribed plain text.

#### Parameters:
- `audio_bytes` (`bytes`): Raw or base64-encoded audio bytes representing a standard WAV file.

#### Return Value:
- `str`: The transcribed text output from Whisper, trimmed of excessive whitespace.

---

## 🧪 Testing Methodology & Mocking

Because `whisper.load_model("small")` executes at the module level when `stt.py` is imported, traditional pytest patches fail because the model has already been allocated in memory.

Our testing suite uses an advanced import-patching pattern:
```python
import sys
from unittest.mock import MagicMock
from tools.stt.stt import stt

# Retrieve the already-loaded module reference
stt_module = sys.modules['tools.stt.stt']

def test_stt_success():
    # 1. Instantiate the mock model
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {'text': 'Hello world!'}
    
    # 2. Swap out the global model variable
    orig_model = stt_module.model
    stt_module.model = mock_model
    
    try:
        # 3. Execute the tool
        result = stt(b"fake_audio_data")
        assert result == "Hello world!"
    finally:
        # 4. Restore the original model
        stt_module.model = orig_model
```

---

## 📖 Related Documentation

- [Main Workspace README](../README.md) – Global architecture
- [Client Frontend README](../client/README.md) – React TalentAcquire UI
- [Server Backend README](../server/README.md) – WebRTC Signaling & VAD

---

**Version:** 1.0.0  
**Status:** Completed & Fully Tested  
**Last Updated:** May 2026
