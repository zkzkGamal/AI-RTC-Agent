# core/IntentClassifier.py
"""
Intent Classifier
-----------------
Parses the router LLM response into a validated route string.
Supports both AGENT_MODE route sets:
  - general : WEB_SEARCH, EMAIL, CALENDAR, CODE_EXECUTE, CHAT
  - hr      : RECRUITMENT, ONBOARDING, PAYROLL, LEAVE_MANAGEMENT,
              POLICY_LOOKUP, EMAIL, CALENDAR, CHAT
Falls back to CHAT if the response is unrecognised or malformed.
"""
import logging
import environ
import pathlib

logger    = logging.getLogger(__name__)
base_path = pathlib.Path(__file__).parent.parent
_e        = environ.Env()
_e.read_env(str(base_path / ".env"))

AGENT_MODE = _e("AGENT_MODE", default="general")

_ROUTES = {
    "general": {
        "WEB_SEARCH",
        "EMAIL",
        "CALENDAR",
        "CODE_EXECUTE",
        "CHAT",
    },
    "hr": {
        "RECRUITMENT",
        "ONBOARDING",
        "PAYROLL",
        "LEAVE_MANAGEMENT",
        "POLICY_LOOKUP",
        "EMAIL",
        "CALENDAR",
        "CHAT",
    },
}

_VALID_ROUTES = _ROUTES.get(AGENT_MODE, _ROUTES["general"])
_FALLBACK     = "CHAT"


def get_intent(response) -> str:
    """
    Parse and validate the router LLM output into a route string.

    Accepts the raw LLM response object (has .content) or a plain string.
    Always returns an uppercase route string from the valid set for the
    current AGENT_MODE. Falls back to CHAT if unrecognised.
    """
    raw = (
        response.content
        if hasattr(response, "content")
        else str(response)
    ).strip().upper()

    if raw in _VALID_ROUTES:
        logger.info(f"[intent] classified as: {raw!r}")
        return raw

    # Try partial match — handles cases where LLM adds punctuation or a word
    for route in _VALID_ROUTES:
        if route in raw:
            logger.warning(
                f"[intent] fuzzy match {raw!r} → {route!r}"
            )
            return route

    logger.warning(
        f"[intent] unrecognised response {raw!r} → falling back to {_FALLBACK!r}"
    )
    return _FALLBACK