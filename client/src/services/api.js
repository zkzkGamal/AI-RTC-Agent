/**
 * HTTP client for the agent REST API (chat, sessions, CV upload).
 */

const SERVER_URL = 'http://localhost:8080';
const AGENT_URL = 'http://localhost:8001';
export async function createSession() {
  const res = await fetch(`${SERVER_URL}/session`);
  if (!res.ok) throw new Error(`Failed to create WebRTC session: ${res.status}`);
  const data = await res.json();
  return data.session_id;
}
export async function sendOffer(sessionId, offer) {
  const res = await fetch(`${SERVER_URL}/session/${sessionId}/offer`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      sdp: offer.sdp,
      type: offer.type
    })
  });
  if (!res.ok) throw new Error(`Offer failed: ${res.status}`);
  return res.json();
}
export async function sendChatMessage(userId, sessionId, message) {
  const res = await fetch(`${AGENT_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      user_id: userId,
      session_id: sessionId || undefined,
      message
    })
  });
  if (!res.ok) throw new Error(`Agent chat failed: ${res.status}`);
  return res.json();
}
export async function uploadCv(userId, file) {
  const form = new FormData();
  form.append('user_id', userId);
  form.append('file', file);
  const res = await fetch(`${AGENT_URL}/api/cv/upload`, {
    method: 'POST',
    body: form
  });
  if (!res.ok) {
    let detail = `CV upload failed: ${res.status}`;
    try {
      const err = await res.json();
      if (err.detail) detail = err.detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}
export async function getUserSessions(userId) {
  const res = await fetch(`${AGENT_URL}/api/sessions/${userId}`);
  if (!res.ok) throw new Error(`Failed to load sessions: ${res.status}`);
  return res.json();
}
export async function getSessionMessages(sessionId) {
  const res = await fetch(`${AGENT_URL}/api/sessions/${sessionId}/messages`);
  if (!res.ok) throw new Error(`Failed to load session messages: ${res.status}`);
  return res.json();
}
