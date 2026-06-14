import { io } from 'socket.io-client';

const AGENT_URL = 'http://localhost:8001';

let socket = null;

/**
 * Initialize Socket.IO connection to the agent server.
 */
export function connectSocket(onConnect, onDisconnect) {
  if (socket) {
    if (socket.connected) {
      onConnect?.(socket.id);
    }
    return socket;
  }

  socket = io(AGENT_URL, {
    autoConnect: true,
    transports: ['websocket'],
  });

  socket.on('connect', () => {
    console.log('Socket.IO connected to agent, sid:', socket.id);
    onConnect?.(socket.id);
  });

  socket.on('disconnect', (reason) => {
    console.log('Socket.IO disconnected from agent, reason:', reason);
    onDisconnect?.(reason);
  });

  return socket;
}

/**
 * Join user and session rooms to receive targeted events.
 */
export function joinSession(userId, sessionId) {
  if (!socket) return;
  console.log(`Socket joining session room: ${sessionId} for user: ${userId}`);
  socket.emit('join', { user_id: userId, session_id: sessionId });
}

/**
 * Register handlers for tool start/finish events.
 */
export function listenToTools(onToolStart, onToolFinished) {
  if (!socket) return;

  // Remove existing listeners first to prevent duplicates
  socket.off('tool_start');
  socket.off('tool_finished');

  socket.on('tool_start', (data) => {
    console.log('Tool start event:', data);
    onToolStart?.(data);
  });

  socket.on('tool_finished', (data) => {
    console.log('Tool finished event:', data);
    onToolFinished?.(data);
  });
}

/**
 * Cleanly disconnect the socket.
 */
export function disconnectSocket() {
  if (socket) {
    socket.off('tool_start');
    socket.off('tool_finished');
    socket.disconnect();
    socket = null;
  }
}
