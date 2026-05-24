# MCP Server

FastMCP server for the `AI-RTC-Agent` workspace. This service exposes local tools for:

- speech-to-text with Whisper
- email sending and inbox actions
- web search with DuckDuckGo
- shared auth, rate limiting, HTTP, and response helpers

The server runs over SSE on port `8005`.

## What Changed

The MCP server is no longer just an STT endpoint. It now includes:

- `stt` for audio transcription
- `send_email` for SMTP email sending
- `list_inbox` for recent Gmail inbox messages
- `read_email` for full Gmail message content
- `reply_to_email` for replying to an email
- `draft_reply` for generating a simple reply draft
- `duckduckgo_search` for web search
- shared utility modules in `utils/` for auth, HTTP, errors, responses, and rate limiting

## Project Layout

```text
mcp/
├── main.py
├── server.py
├── get_token.py
├── .env.example
├── tools/
│   ├── emails/
│   ├── search_web/
│   └── stt/
├── utils/
│   ├── auth.py
│   ├── exceptions.py
│   ├── http_client.py
│   ├── rate_limiter.py
│   └── response_parser.py
└── tests/
```

## Quick Start

### 1. Install system requirements

Whisper needs `ffmpeg` installed on the machine.

```bash
sudo apt update
sudo apt install ffmpeg
```

### 2. Install Python dependencies

```bash
cd mcp
pip install -r requirements-dev.txt
```

### 3. Create your environment file

```bash
cp .env.example .env
```

Then fill in the values you need.

### 4. Start the server

```bash
python main.py
```

The FastMCP server will run on:

- `http://localhost:8005`
- SSE transport enabled through FastMCP

### 5. Run tests

```bash
pytest tests/ -v
```

## Environment Variables

Use `mcp/.env` for local configuration.

```env
MAIL_HOST=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_ENCRYPTION=false

GMAIL_TOKEN_FILE=token.json
GMAIL_SENDER=your-email@gmail.com
GMAIL_API=

OLLAMA_BASE_URL=
GOOGLE_API_KEY=
OPENAI_API_KEY=
```

### Variable notes

- `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD` are used by SMTP tools.
- `MAIL_ENCRYPTION` is treated in code as a boolean.
- Use `true` for SSL-style SMTP.
- Use `false` for STARTTLS on port `587`.
- `GMAIL_TOKEN_FILE` points to the OAuth token file used by Gmail API tools.
- `GMAIL_SENDER` should usually be the same Gmail account you authorized.
- `GMAIL_API` can stay empty unless you want to override the default Gmail API URL.

## Gmail Setup Tutorial

The email tools use two different auth paths:

- SMTP credentials for sending mail
- Gmail OAuth for reading inbox messages with the Gmail API

That means you need both:

1. `credentials.json`
2. `token.json`

### Step 1. Create the Google Cloud project

1. Open the Google Cloud Console.
2. Create a new project, or choose an existing one.
3. Enable the Gmail API for that project.

### Step 2. Configure the OAuth consent screen

1. Go to `APIs & Services` -> `OAuth consent screen`.
2. Choose `External` if this is a personal/test project.
3. Fill in the app name and required fields.
4. Add your Gmail account as a test user if Google asks for it.

### Step 3. Create the OAuth client credentials file

1. Go to `APIs & Services` -> `Credentials`.
2. Click `Create Credentials`.
3. Choose `OAuth client ID`.
4. Select `Desktop app`.
5. Download the JSON file.
6. Rename it to `credentials.json`.
7. Place it inside the `mcp/` folder.

This `credentials.json` file is what you meant by the mail cert. In this project it is the Google OAuth client credentials file used to create the Gmail token.

### Step 4. Generate `token.json`

Run this once from inside `mcp/`:

```bash
python get_token.py
```

What happens:

- a browser window opens
- you sign in with the Gmail account you want to use
- you approve Gmail access
- the script writes `token.json` in the `mcp/` directory

The script requests this scope:

- `https://www.googleapis.com/auth/gmail.modify`

That scope allows inbox listing, reading messages, and related Gmail actions.

### Step 5. Point `.env` to the token

```env
GMAIL_TOKEN_FILE=token.json
GMAIL_SENDER=your-email@gmail.com
```

### Step 6. Configure SMTP for sending mail

For Gmail SMTP you will usually use:

```env
MAIL_HOST=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-google-app-password
MAIL_ENCRYPTION=false
```

Important:

- do not use your normal Gmail password here if the account requires App Passwords
- use a Google App Password for SMTP when needed
- Gmail inbox tools use OAuth `token.json`, not the SMTP password

## Tool Reference

### `stt(audio_bytes)`

Transcribes WAV audio with the local Whisper `small` model.

- accepts raw bytes or base64-encoded audio
- auto-detects base64 payloads
- returns normalized success/error responses

### `send_email(subject, body, to_email)`

Sends email through SMTP.

- requires `MAIL_HOST`, `MAIL_USERNAME`, and `MAIL_PASSWORD`
- rate-limited through the shared limiter

### `list_inbox(limit=10)`

Lists recent Gmail inbox messages.

- uses Gmail API
- requires a valid `token.json`
- maximum limit is capped in code

### `read_email(email_id)`

Fetches a Gmail message by id and returns:

- subject
- from
- to
- date
- snippet
- decoded plain-text body when available

### `reply_to_email(email_id, body)`

Builds a reply from the original message metadata and sends it through SMTP.

### `draft_reply(original_subject, original_body, tone="professional")`

Creates a simple reply draft string.

### `duckduckgo_search(query, max_results=5)`

Runs a DuckDuckGo search and returns structured results:

- title
- url
- snippet

## Shared Utility Layer

The `utils/` package keeps tool behavior consistent.

### `auth.py`

- loads environment variables once
- validates required credentials
- loads and refreshes Gmail OAuth tokens

### `exceptions.py`

Defines custom exceptions:

- `ToolError`
- `AuthError`
- `RateLimitError`
- `ExternalAPIError`
- `ValidationError`

### `response_parser.py`

Standardizes tool outputs through:

- `ok(...)`
- `err(...)`
- `paginated(...)`
- `from_exception(...)`

### `rate_limiter.py`

Implements per-tool token-bucket throttling for:

- `gmail`
- `duckduckgo`
- `stt`
- other named tools

### `http_client.py`

Provides shared async HTTP helpers with:

- timeouts
- retries
- auth and rate-limit error mapping

## Notes for Development

- `main.py` imports `tools` so FastMCP registers the tool modules on startup.
- `server.py` creates the FastMCP app with name `AI-RTC-Agent` on port `8005`.
- `get_token.py` should only be run when you need to create or refresh the first OAuth token locally.
- Whisper model loading happens at module import time in `tools/stt/stt.py`.

## Related Docs

- [Workspace README](../README.md)
- [Server README](../server/README.md)
- [Client README](../client/README.md)
