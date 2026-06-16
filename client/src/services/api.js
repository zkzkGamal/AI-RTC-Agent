/**
 * api.js — API service for communicating with the WebRTC backend (port 8080)
 * and the FastAPI AI Agent backend (port 8001)
 */

const SERVER_URL = 'http://localhost:8080';
const AGENT_URL = 'http://localhost:8001';

// ─── WebRTC (Port 8080) Endpoints ───

/**
 * Create a new voice session on the WebRTC server.
 * @returns {Promise<string>} session_id
 */
export async function createSession() {
  const res = await fetch(`${SERVER_URL}/session`);
  if (!res.ok) throw new Error(`Failed to create WebRTC session: ${res.status}`);
  const data = await res.json();
  return data.session_id;
}

/**
 * Send an SDP offer to the WebRTC server and get back an SDP answer.
 * @param {string} sessionId
 * @param {RTCSessionDescriptionInit} offer
 * @returns {Promise<RTCSessionDescriptionInit>} answer
 */
export async function sendOffer(sessionId, offer) {
  const res = await fetch(`${SERVER_URL}/session/${sessionId}/offer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sdp: offer.sdp, type: offer.type }),
  });
  if (!res.ok) throw new Error(`Offer failed: ${res.status}`);
  return res.json();
}

// ─── FastAPI Agent (Port 8001) Endpoints ───

/**
 * Send a chat message to the FastAPI Agent.
 * @param {string} userId
 * @param {string|null} sessionId
 * @param {string} message
 * @returns {Promise<{session_id: string, user_id: string, response: string, pending_confirmation: any, messages_count: number}>}
 */
export async function sendChatMessage(userId, sessionId, message) {
  const res = await fetch(`${AGENT_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      session_id: sessionId || undefined,
      message,
    }),
  });
  if (!res.ok) throw new Error(`Agent chat failed: ${res.status}`);
  return res.json();
}

/**
 * Upload a candidate CV (PDF / Word / Markdown) to the agent. The file is saved
 * into the global content/ folder, parsed, and its keywords + knowledge are stored
 * as the user's CV memory so the agent can answer based on it.
 * @param {string} userId
 * @param {File} file
 * @returns {Promise<{user_id: string, file_name: string, keywords: string[], summary: string, knowledge: object}>}
 */
export async function uploadCv(userId, file) {
  const form = new FormData();
  form.append('user_id', userId);
  form.append('file', file);
  const res = await fetch(`${AGENT_URL}/api/cv/upload`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    let detail = `CV upload failed: ${res.status}`;
    try {
      const err = await res.json();
      if (err.detail) detail = err.detail;
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json();
}

/**
 * Fetch all sessions belonging to a user ID.
 * @param {string} userId
 * @returns {Promise<{sessions: Array<{session_id: string, user_id: string, pending_confirmation: any}>}>}
 */
export async function getUserSessions(userId) {
  const res = await fetch(`${AGENT_URL}/api/sessions/${userId}`);
  if (!res.ok) throw new Error(`Failed to load sessions: ${res.status}`);
  return res.json();
}

/**
 * Fetch all messages for a specific session ID.
 * @param {string} sessionId
 * @returns {Promise<{messages: Array<{id: number, session_id: string, user_id: string, role: string, content: string, name: string|null, tool_call_id: string|null, created_at: string}>}>}
 */
export async function getSessionMessages(sessionId) {
  const res = await fetch(`${AGENT_URL}/api/sessions/${sessionId}/messages`);
  if (!res.ok) throw new Error(`Failed to load session messages: ${res.status}`);
  return res.json();
}
