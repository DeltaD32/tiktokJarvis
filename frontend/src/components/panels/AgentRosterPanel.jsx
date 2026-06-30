import { useState, useEffect } from 'react'
import { HoloPanel } from '../HoloPanel'

export function AgentRosterPanel({ onClose, message }) {
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchAgents = () => {
    setLoading(true)
    fetch('/api/agents')
      .then(r => r.json())
      .then(data => { setAgents(data || []); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => { fetchAgents() }, [])

  const readyCount = agents.filter(a => a.status === 'ready').length

  return (
    <HoloPanel title={`Agent Roster (${readyCount}/${agents.length} ready)`} message={message} onClose={onClose}>
      <div style={{ display: 'flex', gap: 4, marginBottom: 10 }}>
        <button className="icon-btn" onClick={fetchAgents} style={{ fontSize: 9, opacity: 0.6 }}>refresh</button>
      </div>

      {loading ? (
        <p className="panel-empty">Loading...</p>
      ) : agents.length === 0 ? (
        <p className="panel-empty">No agents registered.</p>
      ) : (
        agents.map(a => (
          <div key={a.name} className="panel-item">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <span style={{
                width: 8, height: 8, borderRadius: '50%', display: 'inline-block', flexShrink: 0,
                background: a.status === 'ready' ? 'var(--green)' : a.status === 'busy' ? 'var(--amber)' : a.status === 'error' ? 'var(--red)' : 'var(--text-faint)',
                boxShadow: a.status === 'busy' ? '0 0 6px var(--amber)' : 'none',
                animation: a.status === 'busy' ? 'jpulse 1.5s ease-in-out infinite' : 'none',
              }} />
              <span className="panel-item-title" style={{ fontSize: 13 }}>{a.name}</span>
              <span className={`badge badge-${a.status === 'ready' ? 'open' : a.status === 'busy' ? 'attention' : 'error'}`}>
                {a.status}
              </span>
              {a.dispatch_count > 0 && (
                <span style={{ fontSize: 9, color: 'var(--text-dim)', fontFamily: "'JetBrains Mono', monospace" }}>
                  {a.dispatch_count} dispatch{a.dispatch_count !== 1 ? 'es' : ''}
                </span>
              )}
            </div>
            <div className="panel-item-meta" style={{ fontSize: 10 }}>
              {a.description?.slice(0, 120)}{a.description?.length > 120 ? '...' : ''}
            </div>
            {a.last_task && (
              <div style={{ fontSize: 9, color: 'var(--amber)', marginTop: 4, fontFamily: "'JetBrains Mono', monospace", opacity: 0.7 }}>
                last: {a.last_task.slice(0, 60)}
              </div>
            )}
          </div>
        ))
      )}
    </HoloPanel>
  )
}
