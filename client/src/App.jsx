/**
 * App.jsx — Main application shell
 * Orchestrates the WebRTC voice session using services and components.
 */

import { useState, useRef, useCallback, useEffect } from 'react'
import './App.css'

// Services
import { createSession, sendOffer } from './services/api'
import { createConnection, applyAnswer, closeConnection } from './services/webrtc'

// Components
import AudioVisualizer from './components/AudioVisualizer'
import StatusDisplay from './components/StatusDisplay'
import ControlButtons from './components/ControlButtons'

export default function App() {
  // ── State ──
  const [status, setStatus] = useState('idle')
  const [statusMsg, setStatusMsg] = useState('System ready')
  const [sessionId, setSessionId] = useState(null)
  const [error, setError] = useState(null)
  const [transcripts, setTranscripts] = useState([]) // List of { id, timestamp, text }

  // ── Refs ──
  const pcRef = useRef(null)
  const streamRef = useRef(null)
  const timelineEndRef = useRef(null)

  // ── Derived ──
  const isConnected = status === 'connected'
  const isBusy = status === 'creating' || status === 'connecting' || status === 'stopping'

  // ── Auto-scroll to latest transcript ──
  useEffect(() => {
    if (timelineEndRef.current) {
      timelineEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [transcripts])

  // ── Connection state handler ──
  const handleConnectionState = useCallback((state) => {
    if (state === 'connected') {
      setStatus('connected')
      setStatusMsg('Active screening session in progress')
    } else if (state === 'failed' || state === 'closed') {
      setStatus('error')
      setStatusMsg('Connection terminated')
      setError('Interview connection failed or was closed.')
    }
  }, [])

  // ── Message handler (DataChannel) ──
  const handleMessage = useCallback((data) => {
    if (data && data.trim()) {
      const cleanData = data.trim()
      setTranscripts((prev) => {
        const id = Date.now() + '-' + Math.random()
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        return [...prev, { id, timestamp, text: cleanData }]
      })
    }
  }, [])

  // ── Start ──
  const handleStart = useCallback(async () => {
    setError(null)
    setTranscripts([])
    setStatus('creating')
    setStatusMsg('Initializing secure HR session…')

    try {
      // 1. Create server session
      const sid = await createSession()
      setSessionId(sid)
      setStatusMsg('Connecting media devices…')

      // 2. Create WebRTC connection + get microphone
      setStatus('connecting')
      setStatusMsg('Establishing peer-to-peer audio link…')
      const { pc, stream, offer } = await createConnection(handleConnectionState, handleMessage)
      pcRef.current = pc
      streamRef.current = stream

      // 3. Exchange SDP with server
      const answer = await sendOffer(sid, offer)
      await applyAnswer(pc, answer)

    } catch (err) {
      console.error('Start error:', err)
      setError(err.message || 'Media connection failed.')
      setStatus('error')
      setStatusMsg('Initialization failed')
      closeConnection(pcRef.current, streamRef.current)
      pcRef.current = null
      streamRef.current = null
    }
  }, [handleConnectionState, handleMessage])

  // ── Stop ──
  const handleStop = useCallback(() => {
    setStatus('stopping')
    setStatusMsg('Closing interview link…')
    closeConnection(pcRef.current, streamRef.current)
    pcRef.current = null
    streamRef.current = null
    setTimeout(() => {
      setStatus('idle')
      setStatusMsg('System ready')
      setSessionId(null)
      setError(null)
    }, 400)
  }, [])

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand-logo">TalentAcquire™</div>
        <h1>AI Interview Control Center</h1>
        <p>Enterprise Real-Time Candidate Speech Screening & Transcription</p>
      </header>

      <main className="dashboard-layout">
        {/* Left Column: Interactive Controls */}
        <section className="agent-card control-panel">
          <div className="section-header">
            <h2>Audio Integration</h2>
            <span className="badge">WebRTC 48kHz</span>
          </div>
          
          <AudioVisualizer isActive={isConnected} />
          
          <StatusDisplay
            status={status}
            statusMsg={statusMsg}
            sessionId={sessionId}
            error={error}
          />
          
          <ControlButtons
            onStart={handleStart}
            onStop={handleStop}
            isConnected={isConnected}
            isBusy={isBusy}
          />
        </section>

        {/* Right Column: Live Timeline */}
        <section className="agent-card timeline-panel">
          <div className="section-header">
            <h2>Live Interview Transcript</h2>
            <span className="badge status-badge active">
              {isConnected ? 'STREAMING ACTIVE' : 'AWAITING LINK'}
            </span>
          </div>

          <div className="transcripts-timeline">
            {transcripts.length === 0 ? (
              <div className="empty-timeline">
                <div className="pulse-icon">🎙️</div>
                <p>Awaiting speech input...</p>
                <span className="hint">
                  Press <strong>Start</strong> to open connection. Audio will transcribe automatically every 2 seconds of silence.
                </span>
              </div>
            ) : (
              <div className="timeline-list">
                {transcripts.map((t, idx) => (
                  <div key={t.id} className="timeline-item animate-slide-in">
                    <div className="item-header">
                      <div className="speaker-avatar">👤</div>
                      <span className="speaker-name">CANDIDATE</span>
                      <span className="item-time">{t.timestamp}</span>
                      <span className="segment-number">#{idx + 1}</span>
                    </div>
                    <div className="item-content">
                      <p>{t.text}</p>
                    </div>
                  </div>
                ))}
                <div ref={timelineEndRef} />
              </div>
            )}
          </div>
        </section>
      </main>

      <footer className="app-footer">
        TalentAcquire™ Interview Suite v2.4 · Secure TLS · Automated MCP Transcription · GDPR Compliant
      </footer>
    </div>
  )
}
