# FastMCP Server - Core Tools & Services Layer 🛠️

This directory contains the **Model Context Protocol (FastMCP)** server for the `AI-RTC-Agent` workspace. Running on port `8005` over Server-Sent Events (SSE), this microservices layer exposes heavy-duty tools for speech-to-text, calendar event handling, internet search, and email automation, while enforcing structured rate limiting, custom authorization middleware, and standardized outputs.

---

## 🏗️ Architectural Overview

The MCP layer decouples its transport protocol (FastMCP / SSE) from the underlying business and authorization logic using a clean three-tiered layout:

```text
               ┌─────────────────────────────────┐
               │    Python WebRTC Server / API   │
               └────────────────┬────────────────┘
                                │
                      HTTP / SSE Request (with X-API-Key)
                                │
               ┌────────────────▼────────────────┐
               │         MCPApiKeyMiddleware     │  [Core Auth Tier]
               │     (Validates dynamic hash)    │
               └────────────────┬────────────────┘
                                │
               ┌────────────────▼────────────────┐
               │           FastMCP Tools         │  [Tool Definition Tier]
               │     (Exposes tool endpoints)    │
               └────────┬────────────────┬───────┘
                        │                │
          ┌─────────────▼──────┐  ┌──────▼─────────────┐
          │    Service Layer   │  │   Utility Layer    │  [Implementation Tier]
          │   (Audio/Mail/Cal) │  │ (Rate/Error/Parse) │
          └────────────────────┘  └────────────────────┘
```

1.  **Core Auth Tier (`core/`)**: Starlette middleware intercepts HTTP connections, validating dynamic, time-locked timestamp API keys before requests reach the tools.
2.  **Tool Definition Tier (`tools/`)**: Exposes structured interfaces to the WebRTC server, acting as high-level endpoints.
3.  **Implementation Tier (`service/` & `utils/`)**:
    *   **Service Layer**: Singleton classes and core business modules managing heavy resources (Whisper model loading, SMTP formatting, Google client bindings).
    *   **Utility Layer**: Cross-cutting tools ensuring rate limits, custom exceptions, standardized response envelopes, and client retries act uniformly.

---

## 📁 Layout & Structure

```text
mcp/
├── core/
│   ├── ApiKeyGenerator.py    # Deterministic time-based key algorithm
│   └── Middleware.py         # Starlette X-API-Key validator middleware
├── service/
│   ├── AudioService.py       # Decodes incoming base64 and maps transcription
│   ├── CalnderService.py     # Base calendar normalization structures
│   ├── CalendarGoogleService.py  # Google Calendar API interfaces
│   ├── CalendarICSService.py # Local iCalendar (.ics) fallback engine
│   ├── LoadModelService.py   # Shared Whisper model preloader and singleton
│   └── MailService.py        # Outbound SMTP + reply header orchestrator
├── tools/
│   ├── calendar/             # Exposed FastMCP calendar endpoints
│   ├── emails/               # Exposed FastMCP email & reply tools
│   ├── search_web/           # DuckDuckGo search tool
│   └── stt/                  # Whisper STT transcribers
├── utils/
│   ├── auth.py               # Credentials loader and OAuth refreshers
│   ├── exceptions.py         # Domain error hierarchy
│   ├── http_client.py        # Asynchronous custom HTTP agent
│   ├── rate_limiter.py       # Token-Bucket rate limiter
│   └── response_parser.py    # Unified API response parser
├── main.py                   # Application entrypoint & preloading trigger
├── server.py                 # FastMCP setup & Starlette configuration
├── get_token.py              # Local Google OAuth desktop authorization helper
├── requirements.txt          # Production dependencies
└── requirements-dev.txt      # Developer test packages
```

---

## 🔒 Custom Dynamic API Key Authentication

To secure communications between local servers without exposing static long-lived credentials, this project uses a **Dynamic Timestamp-based Zero-Shared-State Authentication Protocol**.

### The Principle of Operation
Both the sender (WebRTC server) and receiver (MCP server) import `api_key_generator`. Because the algorithm is deterministic and locked to a synchronized time clock (UTC), they can generate and validate credentials instantly:

1.  **Generation**: The sender gets the current UTC timestamp, divides it by an epoch sliding window (5 seconds), and generates a deterministic hash (e.g., `S_33758364_A`).
2.  **Transportation**: The key is attached as a request header: `X-API-Key: S_33758364_A`.
3.  **Interception**: `MCPApiKeyMiddleware` extracts the key.
4.  **Verification**:
    *   **Expiration Check**: The middleware extracts the timestamp and compares it with its local time. If the time difference is greater than 1 grace window (5 seconds), the request is rejected as `401 Unauthorized` (preventing replay attacks).
    *   **Hash Check**: The middleware recalculates the expected suffix and prefix for that exact timestamp. If they match, the request is authenticated.

---

## ⚙️ Service Layer Deep Dive (`service/`)

These services handle all business logic, isolated from the FastMCP wrapper:

*   **`LoadModelService`**: A singleton class managing the **OpenAI Whisper `"small"`** model. Running `preload_model()` at boot loads the model parameters into system memory, avoiding a cold-start latency of ~4-5 seconds on the first candidate speech segment.
*   **`AudioService`**: Normalizes audio formats. It accepts raw bytes, base64 strings, or base64 bytes, decodes them to raw WAV formats, and invokes Whisper to produce clean transcriptions.
*   **`MailService`**: Handles email formatting and SMTP transmission. It parses inbox metadata and automatically injects standard reply headers (`In-Reply-To` and `References`) to ensure conversational continuity in the recipient's mail client.
*   **`CalendarServices`**: Implements a dual-provider calendar engine. It attempts to load or create events via Google Calendar API, but automatically compiles and returns an **iCalendar (`.ics`)** byte payload as a fallback if the API is offline.

---

## ⚙️ Utility Layer Deep Dive (`utils/`)

*   **`rate_limiter.py`**: A **Token-Bucket Rate Limiter** shared across all tools to prevent external API threshold penalties.
    *   *Default caps*: Gmail (0.5 calls/sec), DuckDuckGo (1.0 calls/sec), STT (2.0 calls/sec).
    *   *Modes*: Supports a "soft wait" (blocks the routine until the bucket refills) or "hard fail" (raises `RateLimitError` immediately).
*   **`exceptions.py`**: Defines domain errors like `ToolError`, `AuthError`, `RateLimitError`, `ValidationError`, and `ExternalAPIError`.
*   **`response_parser.py`**: Enforces a strict response shape:
    *   `ok(data, message)`: Standard success.
    *   `err(message, code, details)`: Custom error shapes.
    *   `paginated(items, total, page, page_size)`: Handles large lists (e.g. Gmail inbox).
    *   `from_exception(exc)`: Middleware helper to auto-convert Python exceptions into clean JSON errors.

---

## 🛠️ FastMCP Tool Reference

The following tools are registered on the FastMCP instance and are consumable by the WebRTC agent:

### 1. Speech-to-Text
#### `stt(audio_bytes: str | bytes)`
Transcribes audio data using the preloaded Whisper model.
*   **Arguments**: WAV audio segment (raw binary bytes or Base64-encoded string).
*   **Response Shape**:
    ```json
    {
      "status": "ok",
      "timestamp": "2026-05-25T14:46:09Z",
      "data": "The transcribed candidate text output."
    }
    ```

### 2. Email Automation
#### `send_email(subject: str, body: str, to_email: str)`
Delivers an outbound message via SMTP.
*   **Arguments**: Target email address, subject line, plain text body.

#### `list_inbox(limit: int = 10)`
Lists recent inbox items via Gmail API.
*   **Arguments**: Maximum items to return (capped at 50).
*   **Response Shape**: Standard `paginated()` envelope containing message IDs, sender info, dates, and preview snippets.

#### `read_email(email_id: str)`
Retrieves a single email message.
*   **Arguments**: Unique Gmail Message ID.
*   **Response**: Decoded plain text body, subject, date, sender, and recipient lists.

#### `reply_to_email(email_id: str, body: str)`
Constructs a conversational reply using email headers.
*   **Arguments**: Original Gmail Message ID, plain text reply content.

#### `draft_reply(original_subject: str, original_body: str, tone: str = "professional")`
Generates a plain-text draft reply using a local prompt router.

### 3. Calendar Scheduling
#### `create_calendar_event(title: str, date: str, time: str, duration_minutes: int, description: str = "", attendees: list = None)`
Schedules an event in Google Calendar, with automatic ICS fallback.
*   **Arguments**: Event title, ISO date string (`YYYY-MM-DD`), time (`HH:MM`), duration in minutes, description, and list of attendee emails.
*   **Response**:
    ```json
    {
      "status": "ok",
      "data": {
        "provider": "google" | "ics_fallback",
        "google_event": { ... },
        "ics": "BEGIN:VCALENDAR...",
        "fallback_reason": null | "Google Credentials Offline"
      }
    }
    ```

#### `load_calendar_events(scope: str = "today", ics_content: str = "", include_google: bool = true)`
Aggregates scheduled events from Google Calendar and optional custom `.ics` files.

### 4. Internet Search
#### `duckduckgo_search(query: str, max_results: int = 5)`
Performs an anonymous search using DuckDuckGo.
*   **Response**: List of items containing title, source URL, and text snippet.

---

## 🛠️ Step-by-Step Google OAuth & SMTP Setup Tutorial

To use Gmail and Google Calendar tools, configure a test application in the Google Cloud Console:

### Step 1: Create a Google Cloud Project
1.  Open the [Google Cloud Console](https://console.cloud.google.com/).
2.  Click the Project Dropdown in the top navigation bar and select **New Project**.
3.  Name it `AI-RTC-Agent-MCP` and click **Create**.

### Step 2: Enable Google APIs
1.  Go to **APIs & Services** > **Library**.
2.  Search for **Gmail API** and click **Enable**.
3.  Search for **Google Calendar API** and click **Enable**.

### Step 3: Configure the OAuth Consent Screen
1.  Go to **APIs & Services** > **OAuth consent screen**.
2.  Select **External** for the User Type, and click **Create**.
3.  Provide the mandatory details:
    *   **App name**: `AI RTC Voice Agent`
    *   **User support email**: Your own Gmail address.
    *   **Developer contact info**: Your own Gmail address.
4.  Click **Save and Continue** (skip adding scopes for now).
5.  On the **Test Users** panel, click **+ Add Users** and enter your exact Gmail address.
    > [!IMPORTANT]
    > You must add your email as a Test User, or Google will block your login attempts during setup.
6.  Click **Save and Continue** to finish.

### Step 4: Download Credentials File
1.  Go to **APIs & Services** > **Credentials**.
2.  Click **+ Create Credentials** at the top of the page, and select **OAuth client ID**.
3.  Set the **Application type** to **Desktop app**.
4.  Set the name to `Voice Agent Client`, then click **Create**.
5.  In the confirmation modal, click **Download JSON**.
6.  Rename the downloaded file to exactly **`credentials.json`** and save it inside this `mcp/` directory.

### Step 5: Authorize and Generate `token.json`
With the client credentials in place, generate your access token:
1.  Run the token generator script from this directory:
    ```bash
    python get_token.py
    ```
2.  **What happens**:
    *   A local web browser tab will open, pointing to Google's authentication page.
    *   Log in using the Gmail account you configured as a test user.
    *   Click **Advanced** > **Go to AI RTC Voice Agent (unsafe)** to bypass Google's unverified app warning.
    *   Grant the requested scopes (Gmail Modify and Google Calendar Full Write/Read Access).
    *   A new file named **`token.json`** will be generated inside this `mcp/` folder. This token handles the authorized secure access.

---

## ⚙️ Environment Configuration

Copy `.env.example` to `.env` and configure your settings:
```bash
cp .env.example .env
```

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `MAIL_HOST` | `smtp.gmail.com` | Outbound SMTP server address. |
| `MAIL_PORT` | `587` | Port used for SMTP (587 for STARTTLS, 465 for SSL). |
| `MAIL_USERNAME` | `your-email@gmail.com` | Outbound email sender username. |
| `MAIL_PASSWORD` | `your-app-password` | Gmail App Password (not your primary account password). |
| `MAIL_ENCRYPTION` | `false` | Set to `true` for Port 465 (SSL), `false` for Port 587 (STARTTLS). |
| `GMAIL_TOKEN_FILE` | `token.json` | Relative path to the generated Gmail/Calendar OAuth token. |
| `GMAIL_SENDER` | `your-email@gmail.com` | Matches the Gmail user account associated with the OAuth token. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Base URL for local Ollama LLM integration. |
| `GOOGLE_API_KEY` | `""` | Optional Google Gemini developer API key. |
| `OPENAI_API_KEY` | `""` | Optional OpenAI primary API key. |

---

## 🧪 Testing

To run the complete MCP tools validation suite, execute the following from the `mcp/` directory:
```bash
pytest tests/ -v
```

*Note: The testing logs use a clean progress format defined in `tests/conftest.py` to print live progress details (e.g. `[ RUN ]` / `[ OK ]`) for each unit test.*
