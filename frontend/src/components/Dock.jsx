export function Dock({ state, panels, onToggle, onMinimize, heartbeatActive, onToggleHeartbeat, noticeCount, onOpenNotices }) {
  const anyOpen = Object.values(panels).some(p => p.open)

  const dockStyle = (open) => ({
    background: open ? 'rgba(var(--accent-rgb), 0.07)' : 'rgba(8,12,18,0.6)',
    border: open ? '1px solid rgba(var(--accent-rgb), 0.4)' : '1px solid var(--border)',
  })

  return (
    <div className="dock">
      {/* Heartbeat toggle */}
      <div
        className="dock-pill"
        style={dockStyle(heartbeatActive)}
        onClick={onToggleHeartbeat}
      >
        <div className="dock-mic-bars">
          <div className="dock-mic-bar" style={{ animation: heartbeatActive ? 'jeq 0.55s ease-in-out infinite' : 'none', opacity: heartbeatActive ? 1 : 0.3 }} />
          <div className="dock-mic-bar" style={{ animation: heartbeatActive ? 'jeq 0.7s ease-in-out infinite' : 'none', animationDelay: '0.1s', opacity: heartbeatActive ? 1 : 0.3 }} />
          <div className="dock-mic-bar" style={{ animation: heartbeatActive ? 'jeq 0.62s ease-in-out infinite' : 'none', animationDelay: '0.2s', opacity: heartbeatActive ? 1 : 0.3 }} />
        </div>
        <div>
          <div className="dock-label">HEARTBEAT</div>
          <div className="dock-value">{heartbeatActive ? 'ON' : 'OFF'}</div>
        </div>
      </div>

      <div className="dock-divider" />

      {/* THE HIVE */}
      <div
        className="dock-pill"
        style={dockStyle(panels.hive?.open)}
        onClick={() => onToggle('hive')}
      >
        <div>
          <div className="dock-label">THE HIVE</div>
          <div className="dock-value">Agent Registry</div>
        </div>
      </div>

      {/* THE STREAM */}
      <div
        className="dock-pill"
        style={dockStyle(panels.stream?.open)}
        onClick={() => onToggle('stream')}
      >
        <div>
          <div className="dock-label">THE STREAM</div>
          <div className="dock-value">{state === 'idle' ? 'IDLE' : state.toUpperCase()}</div>
        </div>
        <div className="dock-progress" style={{ width: 100 }}>
          <div className="dock-progress-fill" style={{
            width: state === 'thinking' ? '12%' : state === 'busy' ? '50%' : state === 'alert' ? '80%' : state === 'complete' ? '100%' : '0%'
          }} />
        </div>
      </div>

      {/* SANDBOX */}
      <div
        className="dock-pill"
        style={dockStyle(panels.sandbox?.open)}
        onClick={() => onToggle('sandbox')}
      >
        <div>
          <div className="dock-label">SANDBOX</div>
          <div className="dock-value">Code & Tools</div>
        </div>
      </div>

      {/* NOTICES */}
      {noticeCount > 0 && (
        <div
          className="dock-pill"
          style={{ ...dockStyle(false), borderColor: 'rgba(255,90,69,0.4)', color: 'var(--red)' }}
          onClick={onOpenNotices}
        >
          <div>
            <div className="dock-label" style={{ color: 'var(--red)' }}>NOTICES</div>
            <div className="dock-value" style={{ color: 'var(--red)' }}>{noticeCount} new</div>
          </div>
        </div>
      )}

      {/* MINIMIZE ALL */}
      {anyOpen && (
        <div className="dock-pill" onClick={onMinimize}>
          <div className="dock-value" style={{ fontSize: 9, letterSpacing: '0.12em' }}>MINIMIZE ALL</div>
        </div>
      )}
    </div>
  )
}
