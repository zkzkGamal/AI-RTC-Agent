"""
Creates authorization headers for API calls, specifically for Google Calendar API.
This module provides a function to load the latest Google OAuth token and format it into the required headers for authenticated requests.
It is used by the Google Calendar service to ensure all API calls are properly
"""
try:
    from mcp_app.utils.auth import credentials
except ModuleNotFoundError:
    from utils.auth import credentials

def _headers() -> dict:
    """Load fresh token and return auth headers."""
    token = credentials.load_gmail_token()
    return {"Authorization": f"Bearer {token}"}
