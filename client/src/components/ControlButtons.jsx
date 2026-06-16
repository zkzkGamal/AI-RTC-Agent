/**
 * Call control buttons (connect, mute, hang up) for the RTC session.
 */

export default function ControlButtons({
  onStart,
  onStop,
  isConnected,
  isBusy
}) {
  return <div className="btn-row">
      <button id="btn-start" className="btn btn-start" onClick={onStart} disabled={isConnected || isBusy} aria-label="Start voice session">
        🎙 Start
      </button>
      <button id="btn-stop" className="btn btn-stop" onClick={onStop} disabled={!isConnected && !isBusy} aria-label="Stop voice session">
        ⏹ Stop
      </button>
    </div>;
}
