import { FloatWindow } from './FloatWindow'

export function StreamWindow({ panel, onClose, onFocus, onDragMove, conversation, currentStream, toolStatus, systemState }) {
  const recent = conversation.slice(-20)
  const nodeDot = (type) => ({
    user: 'var(--cyan)',
    assistant: 'var(--green)',
    tool: 'var(--amber)',
  })[type] || 'var(--text-faint)'

  return (
    <FloatWindow
      title="THE STREAM"
      subtitle={systemState === 'idle' ? '— IDLE' : systemState.toUpperCase()}
      x={panel.x} y={panel.y} z={panel.z}
      onClose={onClose}
      onFocus={onFocus}
      onDragMove={onDragMove}
      width={560}
      maxHeight="62vh"
    >
      <div className="float-body" style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
        {recent.length === 0 && !currentStream && !toolStatus && (
          <p className="panel-empty">No activity yet. Send a message to begin.</p>
        )}

        {recent.map((msg, i) => (
          <div key={msg.id || i} className="stream-node">
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 14 }}>
              <div className="stream-node-dot" style={{ borderColor: nodeDot(msg.role) }} />
              {i < recent.length - 1 && <div className="stream-line" />}
            </div>
            <div className="stream-node-content">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="stream-node-title">{msg.role === 'user' ? 'User' : 'Dela'}</span>
                <span className="stream-node-tag" style={{
                  color: msg.role === 'user' ? 'var(--cyan)' : 'var(--green)',
                  background: msg.role === 'user' ? 'rgba(0,240,255,0.12)' : 'rgba(70,242,176,0.12)',
                }}>
                  {msg.role === 'user' ? 'DIRECTIVE' : 'RESPONSE'}
                </span>
              </div>
              <div className="stream-node-text" style={{
                maxHeight: 80,
                overflow: 'hidden',
                whiteSpace: 'pre-wrap',
              }}>
                {msg.content.slice(0, 300)}
                {msg.content.length > 300 ? '...' : ''}
              </div>
            </div>
          </div>
        ))}

        {/* Streaming response */}
        {currentStream && (
          <div className="stream-node">
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 14 }}>
              <div className="stream-node-dot active" />
            </div>
            <div className="stream-node-content">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="stream-node-title">Dela</span>
                <span className="stream-node-tag" style={{ color: 'var(--amber)', background: 'rgba(255,179,0,0.12)' }}>STREAMING</span>
              </div>
              <div className="stream-node-text" style={{ whiteSpace: 'pre-wrap', maxHeight: 100, overflow: 'hidden' }}>
                {currentStream.slice(0, 300)}{currentStream.length > 300 ? '...' : ''}
                <span style={{ animation: 'jblink 1s steps(1) infinite', color: 'var(--accent)' }}>▍</span>
              </div>
            </div>
          </div>
        )}

        {/* Tool status */}
        {toolStatus && (
          <div className="stream-node">
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 14 }}>
              <div className="stream-node-dot active" style={{ borderColor: 'var(--amber)' }} />
            </div>
            <div className="stream-node-content">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="stream-node-title">Tool</span>
                <span className="stream-node-tag" style={{ color: 'var(--amber)', background: 'rgba(255,179,0,0.12)' }}>EXECUTING</span>
              </div>
              <div className="stream-node-text">{toolStatus}</div>
            </div>
          </div>
        )}
      </div>
    </FloatWindow>
  )
}
