/**
 * Socket.IO client wrapper for real-time session and tool events.
 */

import { io } from 'socket.io-client';
const AGENT_URL = 'http://localhost:8001';
let socket = null;
export function connectSocket(onConnect, onDisconnect) {
  if (socket) {
    if (socket.connected) {
      onConnect?.(socket.id);
    }
    return socket;
  }
  socket = io(AGENT_URL, {
    autoConnect: true,
    transports: ['websocket']
  });
  socket.on('connect', () => {
    console.log('Socket.IO connected to agent, sid:', socket.id);
    onConnect?.(socket.id);
  });
  socket.on('disconnect', reason => {
    console.log('Socket.IO disconnected from agent, reason:', reason);
    onDisconnect?.(reason);
  });
  return socket;
}
export function joinSession(userId, sessionId) {
  if (!socket) return;
  console.log(`Socket joining session room: ${sessionId} for user: ${userId}`);
  socket.emit('join', {
    user_id: userId,
    session_id: sessionId
  });
}
export function listenToTools(onToolStart, onToolFinished) {
  if (!socket) return;
  socket.off('tool_start');
  socket.off('tool_finished');
  socket.on('tool_start', data => {
    console.log('Tool start event:', data);
    onToolStart?.(data);
  });
  socket.on('tool_finished', data => {
    console.log('Tool finished event:', data);
    onToolFinished?.(data);
  });
}
export function disconnectSocket() {
  if (socket) {
    socket.off('tool_start');
    socket.off('tool_finished');
    socket.disconnect();
    socket = null;
  }
}
