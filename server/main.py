"""
main.py  –  AI-RTC-Agent backend server
Uses aiohttp + aiortc to handle WebRTC audio sessions.
Each user gets an isolated session with its own RTCPeerConnection and AudioSession.

Run:
    python main.py
Listens on 0.0.0.0:8080
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np
import aiohttp_cors
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack

from audio_processor import AudioSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Session Model ──────────────────────────────────────────────────

@dataclass
class Session:
    session_id: str
    pc: Optional[RTCPeerConnection] = None
    audio_session: Optional[AudioSession] = None
    tasks: list = field(default_factory=list)


# In-memory session store { session_id → Session }
_sessions: Dict[str, Session] = {}


# ─── Audio Receive Loop ────────────────────────────────────────────

async def _consume_audio_track(track: MediaStreamTrack, session: Session) -> None:
    """
    Continuously pull frames from the WebRTC audio track,
    convert to raw 16-bit mono PCM bytes, and feed to AudioSession.

    Key fix: use numpy .tobytes() and properly detect int16 vs float32 formats.
    """
    logger.info(f"[{session.session_id}] Audio track consumer started")
    try:
        while True:
            try:
                frame = await track.recv()
            except Exception:
                break

            # av.AudioFrame → numpy array
            audio = frame.to_ndarray()

            # Extract mono channel (Left channel) properly handling both planar and interleaved formats
            channels = len(frame.layout.channels)
            if "p" in frame.format.name:
                # Planar format: shape is (channels, samples)
                mono = audio[0]
            else:
                # Interleaved format: shape is (1, samples * channels)
                # Slice the first channel from the interleaved buffer
                mono = audio[0][::channels]

            # Convert to int16 PCM based on the actual dtype
            if mono.dtype == np.float32 or mono.dtype == np.float64:
                # Float audio: range [-1.0, 1.0] → int16 [-32768, 32767]
                pcm_int16 = (np.clip(mono, -1.0, 1.0) * 32767).astype(np.int16)
            else:
                # Already integer (int16 from Opus/s16 format) — use directly
                pcm_int16 = mono.astype(np.int16)

            # Convert to raw bytes using numpy (fast, correct)
            pcm_bytes = pcm_int16.tobytes()

            sample_rate = frame.sample_rate or 48000
            await session.audio_session.add_frame(pcm_bytes, sample_rate)

    except asyncio.CancelledError:
        pass
    finally:
        logger.info(f"[{session.session_id}] Audio track consumer ended")
        if session.audio_session:
            await session.audio_session.close()


# ─── Session Cleanup ───────────────────────────────────────────────

async def _cleanup_session(session_id: str) -> None:
    session = _sessions.pop(session_id, None)
    if session is None:
        return
    logger.info(f"[{session_id}] Cleaning up session")
    for task in session.tasks:
        task.cancel()
    if session.pc:
        await session.pc.close()


# ─── Routes ────────────────────────────────────────────────────────

async def handle_create_session(request: web.Request) -> web.Response:
    """GET /session → { session_id }"""
    session_id = str(uuid.uuid4())
    _sessions[session_id] = Session(session_id=session_id)
    logger.info(f"[{session_id}] Session created")
    return web.json_response({"session_id": session_id})


async def handle_offer(request: web.Request) -> web.Response:
    """
    POST /session/{session_id}/offer
    Body: { sdp, type }
    Returns: { sdp, type } (answer)
    """
    session_id = request.match_info["session_id"]

    if session_id not in _sessions:
        return web.json_response({"error": "Session not found"}, status=404)

    session = _sessions[session_id]

    try:
        body = await request.json()
        offer = RTCSessionDescription(sdp=body["sdp"], type=body["type"])
    except Exception as exc:
        logger.error(f"[{session_id}] Bad offer: {exc}")
        return web.json_response({"error": "Invalid offer"}, status=400)

    # Create AudioSession and PeerConnection
    session.audio_session = AudioSession(session_id=session_id)
    pc = RTCPeerConnection()
    session.pc = pc

    @pc.on("connectionstatechange")
    async def on_connection_state():
        state = pc.connectionState
        logger.info(f"[{session_id}] Connection state: {state}")
        if state in ("failed", "closed", "disconnected"):
            await _cleanup_session(session_id)

    @pc.on("track")
    def on_track(track: MediaStreamTrack):
        if track.kind == "audio":
            logger.info(f"[{session_id}] Audio track received")
            task = asyncio.ensure_future(_consume_audio_track(track, session))
            session.tasks.append(task)

    @pc.on("datachannel")
    def on_datachannel(channel):
        logger.info(f"[{session_id}] DataChannel '{channel.label}' received")
        if channel.label == "transcript":
            session.audio_session.set_datachannel(channel)

    # SDP negotiation
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    logger.info(f"[{session_id}] SDP answer sent")
    return web.json_response({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type,
    })


# ─── App Factory ───────────────────────────────────────────────────

def create_app() -> web.Application:
    app = web.Application()

    app.router.add_get("/session", handle_create_session)
    app.router.add_post("/session/{session_id}/offer", handle_offer)

    # CORS — allow all origins (restrict in production)
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["GET", "POST", "OPTIONS"],
        )
    })
    for route in list(app.router.routes()):
        cors.add(route)

    return app


# ─── Entry Point ───────────────────────────────────────────────────

if __name__ == "__main__":
    app = create_app()
    logger.info("Starting AI-RTC-Agent server on 0.0.0.0:8080")
    web.run_app(app, host="0.0.0.0", port=8080)
