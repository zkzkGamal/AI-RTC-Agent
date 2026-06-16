/**
 * Displays the current connection/agent status to the user.
 */

const DOT_CLASS = {
  idle: 'idle',
  creating: 'connecting',
  connecting: 'connecting',
  connected: 'connected',
  error: 'error',
  stopping: 'connecting'
};
export default function StatusDisplay({
  status,
  statusMsg,
  sessionId,
  error
}) {
  return <div className="status-block">
      {}
      <div className="status-row">
        <span className={`status-dot ${DOT_CLASS[status] || 'idle'}`} />
        <span className="status-label">Status</span>
        <span className="status-value">{statusMsg}</span>
      </div>

      {}
      {sessionId && <div className="status-row" style={{
      alignItems: 'flex-start'
    }}>
          <span className="status-dot" style={{
        marginTop: 5
      }} />
          <span className="status-label">Session</span>
          <span className="session-id">{sessionId}</span>
        </div>}

      {}
      {error && <div className="error-banner" role="alert">
          <span>⚠️</span>
          <span>{error}</span>
        </div>}
    </div>;
}
