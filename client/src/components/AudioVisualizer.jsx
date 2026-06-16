/**
 * Canvas-based visualizer that renders live microphone audio levels.
 */

const MicIcon = () => <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 1a4 4 0 0 1 4 4v7a4 4 0 0 1-8 0V5a4 4 0 0 1 4-4zm0 2a2 2 0 0 0-2 2v7a2 2 0 0 0 4 0V5a2 2 0 0 0-2-2zm6 8a1 1 0 0 1 1 1 7 7 0 0 1-6 6.92V21h2a1 1 0 0 1 0 2H9a1 1 0 0 1 0-2h2v-2.08A7 7 0 0 1 5 12a1 1 0 0 1 2 0 5 5 0 0 0 10 0 1 1 0 0 1 1-1z" />
  </svg>;
export default function AudioVisualizer({
  isActive
}) {
  return <div className={`visualizer ${isActive ? 'active' : ''}`}>
      <div className="ring ring-1" />
      <div className="ring ring-2" />
      <div className="ring ring-3" />
      <div className="visualizer-core">
        <MicIcon />
      </div>
    </div>;
}
