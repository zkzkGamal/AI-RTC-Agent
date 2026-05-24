"""
This module provides A simple intent classifier that uses keyword matching to determine the user's intent based on the LLM response.
The `get_intent` function takes the LLM response and classifies it into one of the predefined intents: "math", "email", or "conversation".
If the response does not match any of the predefined intents, it defaults to "conversation".
"""

import logging , environ , pathlib
logger = logging.getLogger(__name__)
base_path = pathlib.Path(__file__).parent.parent
e = environ.Env()
e.read_env(str(base_path / ".env"))

AGENT_MODE = e("AGENT_MODE", default="general")

def get_intent(response: dict) -> str:
    """Classify the intent of the user message."""
    # For simplicity, we'll use keyword-based classification.
    raw = response.content.strip().lower()
    intent = raw if raw in {"toot_call","chat" } else "chat"
    return intent