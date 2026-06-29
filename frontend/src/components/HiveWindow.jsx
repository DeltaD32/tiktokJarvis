import { useState, useEffect } from 'react'
import { FloatWindow } from './FloatWindow'

const STATUS_META = {
  ready:  { label: 'READY',  color: 'var(--green)',  bg: 'rgba(70,242,176,0.12)', dot: 'var(--green)' },
  busy:   { label: 'BUSY',   color: 'var(--amber)',  bg: 'rgba(255,179,0,0.12)',  dot: 'var(--amber)' },
  error:  { label: 'ERROR',  color: 'var(--red)',    bg: 'rgba(255,90,69,0.12)',   dot: 'var(--red)' },
  idle:   { label: 'IDLE',   color: 'var(--text-dim)', bg: 'rgba(90,100,119,0.12)', dot: 'var(--text-dim)' },
}

export function HiveWindow({ panel, onClose, onFocus, onDragMove, systemState }) {
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchAgents = () => {
    fetch('/api/agents')
      .then(r => r.json())
      .then(data => { setAgents(data || []); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => {
    fetchAgents()
    const interval = setInterval(fetchAgents, 3000)
    return () => clearInterval(interval)
  }, [])

  return (
    <FloatWindow
      title="THE HIVE"
      subtitle="AGENT REGISTRY"
      x={panel.x} y={panel.y} z={panel.z}
      onClose={onClose}
      onFocus={onFocus}
      onDragMove={onDragMove}
      width={312}
      maxHeight="74vh"
    >
      <div className="float-body">
        {loading && <p className="panel-empty">Loading...</p>}
        {!loading && agents.length === 0 && <p className="panel-empty">No agents registered.</p>}
        {agents.map(a => {
          const m = STATUS_META[a.status] || STATUS_META.idle
          return (
            <div key={a.name} className="agent-card">
              <div className="agent-card-top">
                <div className="agent-icon">
                  <div className="agent-dot" style={{
                    background: m.dot,
                    boxShadow: a.status === 'busy' ? `0 0 8px ${m.dot}` : 'none',
                    animation: a.status === 'busy' ? 'jpulse 1.5s ease-in-out infinite' : undefined,
                  }} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6 }}>
                    <div className="agent-name">{a.name}</div>
                    <div className="agent-status-badge" style={{ color: m.color, background: m.bg }}>{m.label}</div>
                  </div>
                  <div className="agent-role">{a.description.slice(0, 60)}...</div>
                  <div className="agent-task">
                    {a.tool_count} tool{a.tool_count !== 'all' && a.tool_count !== 1 ? 's' : ''} available
                    {a.dispatch_count > 0 && (
                      <span style={{ color: 'var(--text-dim)', marginLeft: 6 }}>
                        · {a.dispatch_count}x dispatched
                      </span>
                    )}
                  </div>
                  {a.last_task && a.status === 'busy' && (
                    <div style={{
                      font: "500 10px 'JetBrains Mono', monospace",
                      color: 'var(--amber)',
                      marginTop: 4,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      → {a.last_task.slice(0, 50)}
                    </div>
                  )}
                </div>
              </div>
              <div className="agent-progress">
                <div className="agent-progress-fill" style={{
                  width: a.status === 'busy' ? '40%' : '0%',
                  background: a.status === 'busy' ? m.dot : 'transparent',
                  boxShadow: a.status === 'busy' ? `0 0 8px ${m.dot}` : 'none',
                  transition: 'width 0.5s ease',
                }} />
              </div>
            </div>
          )
        })}
        <div style={{ marginTop: 'auto', paddingTop: 10, borderTop: '1px solid rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 6, height: 6, borderRadius: '50%',
            background: systemState === 'idle' ? 'var(--text-faint)' : 'var(--cyan)',
            boxShadow: systemState === 'idle' ? 'none' : '0 0 8px var(--cyan)',
          }} />
          <div style={{ font: "500 10px 'JetBrains Mono', monospace", color: 'var(--text-dim)' }}>
            {systemState === 'idle' ? 'IAC bus idle' : 'IAC bus active'}
          </div>
          <div style={{ marginLeft: 'auto', font: "500 10px 'JetBrains Mono', monospace", color: 'var(--text-dim)' }}>
            {agents.filter(a => a.status === 'ready').length}/{agents.length} ready
          </div>
        </div>
      </div>
    </FloatWindow>
  )
}
