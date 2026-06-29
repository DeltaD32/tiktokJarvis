import { useState, useEffect } from 'react'
import { FloatWindow } from './FloatWindow'

export function HiveWindow({ panel, onClose, onFocus, onDragMove, systemState }) {
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/agents')
      .then(r => r.json())
      .then(data => { setAgents(data || []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const statusMeta = (isActive) => {
    if (systemState === 'alert') return { label: 'STANDBY', color: 'var(--text-dim)', bg: 'rgba(90,100,119,0.12)' }
    if (systemState === 'thinking' || systemState === 'busy')
      return { label: 'READY', color: 'var(--amber)', bg: 'rgba(255,179,0,0.12)' }
    return { label: 'IDLE', color: 'var(--text-dim)', bg: 'rgba(90,100,119,0.12)' }
  }

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
          const m = statusMeta()
          const active = systemState === 'thinking' || systemState === 'busy'
          return (
            <div key={a.name} className={`agent-card ${active ? 'active' : ''}`}>
              <div className="agent-card-top">
                <div className="agent-icon">
                  <div className={`agent-dot ${active ? 'active' : ''}`} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6 }}>
                    <div className="agent-name">{a.name}</div>
                    <div className="agent-status-badge" style={{ color: m.color, background: m.bg }}>{m.label}</div>
                  </div>
                  <div className="agent-role">{a.description.slice(0, 60)}...</div>
                  <div className="agent-task">
                    {a.tool_count} tool{a.tool_count !== 'all' && a.tool_count !== 1 ? 's' : ''} available
                  </div>
                </div>
              </div>
              <div className="agent-progress">
                <div className="agent-progress-fill" style={{
                  width: active ? '30%' : '0%',
                  background: active ? 'var(--amber)' : 'transparent',
                  boxShadow: active ? '0 0 8px var(--amber)' : 'none',
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
        </div>
      </div>
    </FloatWindow>
  )
}
