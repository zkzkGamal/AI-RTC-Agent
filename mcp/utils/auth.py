"""
Single place to load and validate ALL credentials.
Every tool imports from here — never uses os.getenv() directly.

Usage:
    from tools.utils.auth import credentials
    token = credentials.gmail_token
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv
from utils.exceptions import AuthError
from google.oauth2.credentials import Credentials as GoogleCredentials
from google.auth.transport.requests import Request


load_dotenv()


@dataclass
class Credentials:

    MAIL_HOST: str | None = None
    MAIL_PORT: int | None = None
    MAIL_USERNAME: str | None = None
    MAIL_PASSWORD: str | None = None
    MAIL_ENCRYPTION: bool = True
    
    GOOGLE_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    
    OLLAMA_BASE_URL: str | None = None
    
    GMAIL_TOKEN_FILE: str | None = None
    GMAIL_SENDER: str | None = None
    
    def load_gmail_token(self) -> str:
        """Load Gmail token from file specified in .env. Raises AuthError if missing."""
        token_file = self.GMAIL_TOKEN_FILE
        if not token_file:
            raise AuthError(
                message="GMAIL_TOKEN_FILE not set in .env. Cannot load Gmail token.",
                tool_name="gmail_token",
            )
        try:
            creds = GoogleCredentials.from_authorized_user_file(self.GMAIL_TOKEN_FILE)
            # auto-refresh if expired
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open("token.json", "w") as f:
                    f.write(creds.to_json())

            return creds.token
        except Exception as e:
            raise AuthError(
                message=f"Failed to load Gmail token from '{token_file}': {e}",
                tool_name="gmail_token",
            ) from e
    
    def require(self, *field_names: str) -> None:
        """
        Call this at the top of any tool that needs specific credentials.
        Raises AuthError immediately if any required field is missing.

        Example:
            credentials.require("gmail_token", "gmail_sender")
        """
        for field in field_names:
            value = getattr(self, field, None)
            if not value:
                raise AuthError(
                    message=f"Missing required credential: '{field}'. "
                            f"Check your .env file.",
                    tool_name=field,
                )


def _load() -> Credentials:
    return Credentials(
        MAIL_HOST=os.getenv("MAIL_HOST"),
        MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
        MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
        MAIL_ENCRYPTION=os.getenv("MAIL_ENCRYPTION", "True").lower() in ("true", "1", "yes"),
        
        GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY"),
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
        
        OLLAMA_BASE_URL=os.getenv("OLLAMA_BASE_URL"),
        
        GMAIL_TOKEN_FILE=os.getenv("GMAIL_TOKEN_FILE"),
        GMAIL_SENDER=os.getenv("GMAIL_SENDER"),
    )


# ── Single shared instance ────────────────────────────────────────────────────
# Import this everywhere — credentials are loaded once at startup, not per call.
credentials = _load()