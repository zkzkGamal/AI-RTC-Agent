/**
 * App.jsx — Main application shell
 * Orchestrates the WebRTC voice session and connects transcripts to the FastAPI agent.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import './App.css';

// Services
import { 
  createSession, 
  sendOffer, 
  sendChatMessage, 
  getUserSessions, 
  getSessionMessages 
} from './services/api';
import { createConnection, applyAnswer, closeConnection } from './services/webrtc';
import { 
  connectSocket, 
  joinSession, 
  listenToTools, 
  disconnectSocket 
} from './services/socket';

// Components
import AudioVisualizer from './components/AudioVisualizer';
import StatusDisplay from './components/StatusDisplay';
import ControlButtons from './components/ControlButtons';

// Helper to clean up "Resolved Message:" and surrounding quotes from agent responses
const cleanResolvedMessage = (text) => {
  if (!text) return '';
  let cleaned = text.trim();
  // Remove **Resolved Message:** or Resolved Message: prefix case-insensitively
  cleaned = cleaned.replace(/^(?:\*\*|)?Resolved\s+Message(?:\*\*|)?:\s*/i, '');
  cleaned = cleaned.trim();
  // If wrapped in double or single quotes, strip them
  if ((cleaned.startsWith('"') && cleaned.endsWith('"')) || (cleaned.startsWith("'") && cleaned.endsWith("'"))) {
    cleaned = cleaned.slice(1, -1).trim();
  }
  return cleaned;
};

export default function App() {
  // ── User context ──
  const [userId, setUserId] = useState(() => localStorage.getItem('userId') || 'candidate_user_1');
  const [isEditingUser, setIsEditingUser] = useState(false);
  const [userInputVal, setUserInputVal] = useState(userId);

  // ── Session & Chat State ──
  const [agentSessionId, setAgentSessionId] = useState(null);
  const [sessionsList, setSessionsList] = useState([]);
  const [messages, setMessages] = useState([]);
  const [isAgentThinking, setIsAgentThinking] = useState(false);
  const [runningTool, setRunningTool] = useState(null);
  const [sessionPendingConfirmation, setSessionPendingConfirmation] = useState(null);

  // ── WebRTC Transport State ──
  const [status, setStatus] = useState('idle');
  const [statusMsg, setStatusMsg] = useState('System ready');
  const [webrtcSessionId, setWebrtcSessionId] = useState(null);
  const [error, setError] = useState(null);

  // ── Text input state ──
  const [typedMessage, setTypedMessage] = useState('');
  const [feedbackText, setFeedbackText] = useState('');

  // ── Refs ──
  const pcRef = useRef(null);
  const streamRef = useRef(null);
  const timelineEndRef = useRef(null);
  const agentSessionIdRef = useRef(agentSessionId);
  const sessionsListRef = useRef(sessionsList);

  useEffect(() => {
    agentSessionIdRef.current = agentSessionId;
  }, [agentSessionId]);

  useEffect(() => {
    sessionsListRef.current = sessionsList;
  }, [sessionsList]);

  // ── Derived ──
  const isConnected = status === 'connected';
  const isBusy = status === 'creating' || status === 'connecting' || status === 'stopping';

  // ── Auto-scroll to latest message ──
  useEffect(() => {
    if (timelineEndRef.current) {
      timelineEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isAgentThinking, runningTool, sessionPendingConfirmation]);

  // ── Load session list from backend ──
  const loadSessionsList = useCallback(async (uid) => {
    try {
      const data = await getUserSessions(uid);
      setSessionsList(data.sessions || []);
    } catch (err) {
      console.error('Failed to load user sessions list:', err);
    }
  }, []);

  // On userId change, reload sessions
  useEffect(() => {
    loadSessionsList(userId);
  }, [userId, loadSessionsList]);

  // ── Load messages and setup sockets on session selection ──
  useEffect(() => {
    if (!agentSessionId) {
      setMessages([]);
      setSessionPendingConfirmation(null);
      return;
    }

    const loadSessionDetails = async () => {
      try {
        const data = await getSessionMessages(agentSessionId);
        const filtered = data.messages
          .filter((m) => (m.role === 'human' || m.role === 'ai') && m.content && m.content.trim())
          .map((m) => ({
            id: m.id || (Math.random() * 100000),
            sender: m.role === 'human' ? 'candidate' : 'agent',
            text: m.role === 'human' ? m.content : cleanResolvedMessage(m.content),
            timestamp: m.timestamp ? new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '',
          }));
        setMessages(filtered);

        // Find the matching session to pre-populate pending confirmation
        const currentSession = sessionsListRef.current.find(s => s.session_id === agentSessionId);
        if (currentSession) {
          setSessionPendingConfirmation(currentSession.pending_confirmation);
        } else {
          // Fallback fetch
          const listData = await getUserSessions(userId);
          const matched = listData.sessions.find(s => s.session_id === agentSessionId);
          if (matched) setSessionPendingConfirmation(matched.pending_confirmation);
        }
      } catch (err) {
        console.error('Failed to load session details:', err);
        setError(`Failed to load session messages: ${err.message}`);
      }
    };

    loadSessionDetails();

    // Connect socket for real-time status updates
    connectSocket(
      (sid) => {
        joinSession(userId, agentSessionId);
      },
      (reason) => {
        console.log('Socket disconnected:', reason);
      }
    );

    listenToTools(
      (startData) => {
        setRunningTool({
          name: startData.tool_name,
          arguments: startData.arguments || {}
        });
      },
      (finishedData) => {
        setRunningTool(null);
      }
    );

    return () => {
      disconnectSocket();
      setRunningTool(null);
    };
  }, [agentSessionId, userId]);

  // ── Helper: Send chat message to agent server ──
  const sendMessageToAgent = useCallback(async (text) => {
    if (!text || !text.trim()) return;
    const cleanText = text.trim();

    // 1. Add candidate message visually
    const tempCandId = 'cand-' + Date.now();
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMessages((prev) => [...prev, { id: tempCandId, sender: 'candidate', text: cleanText, timestamp }]);
    setError(null);
    setIsAgentThinking(true);

    // Mute microphone tracks so we don't capture audio while agent is thinking
    if (streamRef.current) {
      streamRef.current.getAudioTracks().forEach((track) => {
        track.enabled = false;
        console.log(`Muted microphone track: ${track.label}`);
      });
    }

    const currentSessionId = agentSessionIdRef.current;

    try {
      // 2. Call FastAPI agent chat
      const chatRes = await sendChatMessage(userId, currentSessionId, cleanText);
      setIsAgentThinking(false);

      // 3. Update agentSessionId if new session was created
      if (chatRes.session_id && chatRes.session_id !== currentSessionId) {
        setAgentSessionId(chatRes.session_id);
        await loadSessionsList(userId);
      } else {
        await loadSessionsList(userId);
      }

      setSessionPendingConfirmation(chatRes.pending_confirmation);

      // 4. Add agent response message
      const agentMsgId = 'agent-' + Date.now();
      const agentTimestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setMessages((prev) => [...prev, {
        id: agentMsgId,
        sender: 'agent',
        text: cleanResolvedMessage(chatRes.response),
        timestamp: agentTimestamp
      }]);

    } catch (err) {
      console.error('Agent chat error:', err);
      setIsAgentThinking(false);
      setError(`Agent response failed: ${err.message}`);
    } finally {
      // Unmute microphone tracks when agent is finished
      if (streamRef.current) {
        streamRef.current.getAudioTracks().forEach((track) => {
          track.enabled = true;
          console.log(`Unmuted microphone track: ${track.label}`);
        });
      }
    }
  }, [userId, loadSessionsList]);

  // ── Text Form Composer Submission ──
  const handleSendText = (e) => {
    e.preventDefault();
    if (!typedMessage.trim()) return;
    sendMessageToAgent(typedMessage);
    setTypedMessage('');
  };

  // ── WebRTC Connection State Handler ──
  const handleConnectionState = useCallback((state) => {
    if (state === 'connected') {
      setStatus('connected');
      setStatusMsg('Active screening session in progress');
    } else if (state === 'failed' || state === 'closed') {
      setStatus('error');
      setStatusMsg('Connection terminated');
      setError('Interview connection failed or was closed.');
    }
  }, []);

  // ── WebRTC Audio Transcription Handler (via DataChannel) ──
  const handleMessage = useCallback((data) => {
    if (data && data.trim()) {
      let cleanText = data.trim();
      try {
        const parsed = JSON.parse(cleanText);
        if (parsed && parsed.status === 'ok' && parsed.data && typeof parsed.data.text === 'string') {
          cleanText = parsed.data.text;
        } else if (parsed && parsed.status === 'error' && parsed.message) {
          console.error('STT error from server:', parsed.message);
          return;
        }
      } catch (e) {
        // Not a JSON string or parsing failed, fallback to raw string
      }
      if (cleanText.trim()) {
        sendMessageToAgent(cleanText);
      }
    }
  }, [sendMessageToAgent]);

  // ── Start WebRTC session ──
  const handleStart = useCallback(async () => {
    setError(null);
    setStatus('creating');
    setStatusMsg('Initializing secure HR session…');

    try {
      // 1. Create WebRTC server session on port 8080
      const sid = await createSession();
      setWebrtcSessionId(sid);
      setStatusMsg('Connecting media devices…');

      // 2. Create local connection & offer
      setStatus('connecting');
      setStatusMsg('Establishing peer-to-peer audio link…');
      const { pc, stream, offer } = await createConnection(handleConnectionState, handleMessage);
      pcRef.current = pc;
      streamRef.current = stream;

      // 3. Apply SDP Answer
      const answer = await sendOffer(sid, offer);
      await applyAnswer(pc, answer);

    } catch (err) {
      console.error('Start error:', err);
      setError(err.message || 'Media connection failed.');
      setStatus('error');
      setStatusMsg('Initialization failed');
      closeConnection(pcRef.current, streamRef.current);
      pcRef.current = null;
      streamRef.current = null;
    }
  }, [handleConnectionState, handleMessage]);

  // ── Stop WebRTC session ──
  const handleStop = useCallback(() => {
    setStatus('stopping');
    setStatusMsg('Closing interview link…');
    closeConnection(pcRef.current, streamRef.current);
    pcRef.current = null;
    streamRef.current = null;
    setTimeout(() => {
      setStatus('idle');
      setStatusMsg('System ready');
      setWebrtcSessionId(null);
    }, 400);
  }, []);

  // ── Start New Chat Session ──
  const handleNewChat = () => {
    setAgentSessionId(null);
    setMessages([]);
    setSessionPendingConfirmation(null);
    setError(null);
  };

  // ── Save/Switch User ID Context ──
  const handleSaveUserId = (e) => {
    e.preventDefault();
    const cleanId = userInputVal.trim();
    if (cleanId) {
      setUserId(cleanId);
      localStorage.setItem('userId', cleanId);
      setIsEditingUser(false);
      handleNewChat();
    }
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand-logo">TalentAcquire™</div>
        <h1>AI Interview Control Center</h1>
        <p>Enterprise Real-Time Candidate Speech Screening & Multi-Agent Assistant</p>
      </header>

      <main className="dashboard-layout">
        {/* Left Column: Interactive Controls & Sessions History */}
        <div className="left-panel-column">
          {/* Section 1: User Context settings */}
          <section className="agent-card settings-panel">
            <div className="section-header">
              <h2>Candidate Context</h2>
              <span className="badge">HR Suite</span>
            </div>
            
            <div className="user-settings">
              {isEditingUser ? (
                <form onSubmit={handleSaveUserId} className="user-id-form">
                  <input 
                    type="text" 
                    value={userInputVal} 
                    onChange={(e) => setUserInputVal(e.target.value)}
                    placeholder="Enter User ID..."
                    className="text-input font-mono"
                    maxLength={30}
                    autoFocus
                  />
                  <button type="submit" className="btn btn-primary-sm">Save</button>
                  <button type="button" className="btn btn-secondary-sm" onClick={() => setIsEditingUser(false)}>Cancel</button>
                </form>
              ) : (
                <div className="user-id-display">
                  <span className="label">User ID:</span>
                  <span className="value font-mono">{userId}</span>
                  <button 
                    className="edit-btn" 
                    onClick={() => {
                      setUserInputVal(userId);
                      setIsEditingUser(true);
                    }}
                    title="Change User ID"
                  >
                    ✏️
                  </button>
                </div>
              )}
            </div>
          </section>

          {/* Section 2: Audio & WebRTC Controls */}
          <section className="agent-card control-panel">
            <div className="section-header">
              <h2>Audio Stream</h2>
              <span className="badge">WebRTC 48kHz</span>
            </div>
            
            <AudioVisualizer isActive={isConnected && !isAgentThinking} />
            
            <StatusDisplay
              status={status}
              statusMsg={statusMsg}
              sessionId={webrtcSessionId}
              error={error}
            />
            
            <ControlButtons
              onStart={handleStart}
              onStop={handleStop}
              isConnected={isConnected}
              isBusy={isBusy}
            />
          </section>

          {/* Section 3: Conversation History */}
          <section className="agent-card history-panel">
            <div className="section-header">
              <h2>Conversation History</h2>
              <button className="new-chat-btn" onClick={handleNewChat} title="Start New Conversation">
                ➕ New
              </button>
            </div>

            <div className="sessions-list">
              {sessionsList.length === 0 ? (
                <div className="empty-sessions">
                  <p>No past sessions found</p>
                </div>
              ) : (
                sessionsList.map((s) => (
                  <div 
                    key={s.session_id} 
                    className={`session-item font-mono ${agentSessionId === s.session_id ? 'active' : ''}`}
                    onClick={() => setAgentSessionId(s.session_id)}
                  >
                    <div className="session-item-title">
                      🔑 {s.session_id.substring(0, 8)}...
                      {s.pending_confirmation && <span className="warning-dot" title="Requires confirmation">⚠️</span>}
                    </div>
                    <div className="session-item-date">
                      {s.created_at ? new Date(s.created_at + 'Z').toLocaleDateString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      }) : ''}
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>

        {/* Right Column: Live Chat Timeline & TextComposer */}
        <section className="agent-card timeline-panel flex-grow-timeline">
          <div className="section-header">
            <h2>Live Timeline & Agent Dialogue</h2>
            <span className={`badge status-badge ${isConnected && !isAgentThinking ? 'active' : ''}`}>
              {isConnected 
                ? (isAgentThinking ? '🔇 MIC MUTED (AGENT RESPONDING)' : '🎙️ MIC ACTIVE (SPEAK NOW)') 
                : '🔇 MIC INACTIVE'}
            </span>
          </div>

          <div className="transcripts-timeline">
            {messages.length === 0 ? (
              <div className="empty-timeline">
                <div className="pulse-icon">🎙️</div>
                <p>Awaiting dialogue...</p>
                <span className="hint">
                  Press <strong>Start</strong> above to speak. Your voice will transcribe automatically. Or type a message below.
                </span>
              </div>
            ) : (
              <div className="timeline-list">
                {messages.map((m) => (
                  <div key={m.id} className={`timeline-item bubble-${m.sender} animate-slide-in`}>
                    <div className="item-header">
                      <div className="speaker-avatar">
                        {m.sender === 'candidate' ? '👤' : '🤖'}
                      </div>
                      <span className="speaker-name">
                        {m.sender === 'candidate' ? 'CANDIDATE' : 'HR AGENT'}
                      </span>
                      <span className="item-time">{m.timestamp}</span>
                    </div>
                    <div className="item-content">
                      <p>{m.text}</p>
                    </div>
                  </div>
                ))}

                {/* Agent Activity and Thinking Indicator */}
                {isAgentThinking && (
                  <div className="timeline-item bubble-agent animate-slide-in">
                    <div className="item-header">
                      <div className="speaker-avatar">🤖</div>
                      <span className="speaker-name">HR AGENT</span>
                      <span className="item-time">Now</span>
                    </div>
                    <div className="item-content thinking-content">
                      <div className="thinking-row">
                        <div className="thinking-dots">
                          <span className="dot" />
                          <span className="dot" />
                          <span className="dot" />
                        </div>
                        {runningTool && (
                          <div className="running-tool-badge font-mono animate-pulse">
                            ⚙️ Running tool: <strong className="tool-name-highlight">{runningTool.name}</strong>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Human-in-the-Loop Confirmation Interface */}
                {sessionPendingConfirmation && (
                  <div className="hil-confirmation-card animate-slide-in">
                    <div className="card-header">
                      <span className="warning-icon">⚠️</span>
                      <h3>Human-In-The-Loop Confirmation Required</h3>
                    </div>
                    <p className="card-desc">
                      The Agent requested permission to run a restricted tool. Please review arguments before executing:
                    </p>

                    <div className="tool-details-block">
                      <div className="row">
                        <span className="field-label">Tool:</span>
                        <span className="field-value font-mono highlight-text">{sessionPendingConfirmation.tool_name}</span>
                      </div>
                      <div className="row flex-col">
                        <span className="field-label">Arguments:</span>
                        <pre className="arguments-json font-mono">
                          {JSON.stringify(sessionPendingConfirmation.arguments, null, 2)}
                        </pre>
                      </div>
                    </div>

                    <div className="hil-actions-row">
                      <button className="btn btn-approve" onClick={handleApproveTool}>
                        ✓ Approve
                      </button>
                      <button className="btn btn-reject" onClick={handleRejectTool}>
                        ✗ Reject
                      </button>
                    </div>

                    <div className="hil-feedback-section">
                      <label htmlFor="hil-feedback-input" className="feedback-label">
                        Request Modifications (e.g. "change recipient to info@company.com"):
                      </label>
                      <div className="feedback-input-row">
                        <input
                          id="hil-feedback-input"
                          type="text"
                          value={feedbackText}
                          onChange={(e) => setFeedbackText(e.target.value)}
                          placeholder="Type changes and submit..."
                          className="text-input"
                        />
                        <button 
                          className="btn btn-submit-feedback" 
                          onClick={() => {
                            handleModifyTool(feedbackText);
                            setFeedbackText('');
                          }}
                          disabled={!feedbackText.trim()}
                        >
                          Submit
                        </button>
                      </div>
                    </div>
                  </div>
                )}
                
                <div ref={timelineEndRef} />
              </div>
            )}
          </div>

          {/* Text Input Fallback Composer */}
          <form onSubmit={handleSendText} className="chat-composer-form">
            <input
              type="text"
              value={typedMessage}
              onChange={(e) => setTypedMessage(e.target.value)}
              placeholder={sessionPendingConfirmation ? "Please confirm or reject the pending action..." : "Type candidate response..."}
              className="chat-composer-input"
              disabled={isAgentThinking}
            />
            <button 
              type="submit" 
              className="chat-composer-submit"
              disabled={isAgentThinking || !typedMessage.trim()}
            >
              Send
            </button>
          </form>
        </section>
      </main>

      <footer className="app-footer">
        TalentAcquire™ Interview Suite v3.0 · WebRTC Audio · FastAPI memory · Event-Driven Tool sockets · GDPR Compliant
      </footer>
    </div>
  );
}
