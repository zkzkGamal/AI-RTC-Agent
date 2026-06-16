"""FastAPI application package for the agent HTTP/WebSocket API."""

from .routes import register_routes

__all__ = ["register_routes"]
