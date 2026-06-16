"""agent.sockets.sio module."""

import socketio
import logging
import contextvars

logger = logging.getLogger(__name__)

active_user_id = contextvars.ContextVar("active_user_id", default=None)
active_session_id = contextvars.ContextVar("active_session_id", default=None)

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

@sio.event
async def connect(sid, environ):
    logger.info(f"Socket connected: {sid}")

@sio.event
async def disconnect(sid):
    logger.info(f"Socket disconnected: {sid}")

@sio.event
async def join(sid, data):
    """
    Client joins a session room or user room to receive targeted events.
    Expected data: {"session_id": "...", "user_id": "..."}
    """
    session_id = data.get("session_id")
    user_id = data.get("user_id")

    if session_id:
        await sio.enter_room(sid, session_id)
        logger.info(f"Socket {sid} joined session room: {session_id}")

    if user_id:
        await sio.enter_room(sid, user_id)
        logger.info(f"Socket {sid} joined user room: {user_id}")
