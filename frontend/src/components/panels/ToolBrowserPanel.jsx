import { useState, useEffect } from 'react'
import { HoloPanel } from '../HoloPanel'

export function ToolBrowserPanel({ onClose, message }) {
  const [tools, setTools]           = useState([])
  const [agents, setAgents]         = useState([])
  const [loading, setLoading]       = useState(true)
  const [filter, setFilter]         = useState('')
  const [tab, setTab]               = useState('tools')
  const [selectedAgent, setSelAgent] = useState(null)

  useEffect(() => {
    Promise.all([
      fetch('/api/tools').then(r => r.json()),
      fetch('/api/agents').then(r => r.json()),
    ])
      .then(([t, a]) => { setTools(t); setAgents(a); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const confirmTools = tools.filter(t => t.requires_confirmation)
  const safeTools    = tools.filter(t => !t.requires_confirmation)

  const matches = (item) => {
    if (!filter.trim()) return true
    const q = filter.toLowerCase()
    return item.name.toLowerCase().includes(q) || item.description.toLowerCase().includes(q)
  }

  const ToolRow = ({ t }) => (
    <div className="panel-item" style={{ cursor: 'default' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
        <span className="panel-item-title" style={{ fontFamily: 'monospace', fontSize: 12 }}>{t.name}</span>
        {t.requires_confirmation ? (
          <span className="badge badge-attention" title="Requires user confirmation">CONFIRM</span>
        ) : (
          <span className="badge badge-done" title="Safe — no confirmation needed">SAFE</span>
        )}
      </div>
      <div className="panel-item-meta" style={{ fontSize: 11, lineHeight: 1.4 }}>
        {t.description}
      </div>
      {t.param_count != null && (
        <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>
          {t.param_count} parameter{t.param_count !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  )

  return (
    <HoloPanel title="Tool Browser" message={message} onClose={onClose}>
      {/* Filter bar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input
          className="chat-input"
          style={{ flex: 1, fontSize: 12 }}
          value={filter}
          onChange={e => setFilter(e.target.value)}
          placeholder="Filter by name or description..."
        />
        <button className="icon-btn" onClick={() => setFilter('')} style={{ borderColor: 'var(--text-dim)', color: 'var(--text-dim)' }}>clear</button>
      </div>

      {/* Tab switcher */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
        <button
          className="hb-btn"
          onClick={() => setTab('tools')}
          style={tab === 'tools' ? { borderColor: 'var(--cyan)', color: 'var(--cyan)' } : {}}
        >
          TOOLS ({tools.length})
        </button>
        <button
          className="hb-btn"
          onClick={() => setTab('agents')}
          style={tab === 'agents' ? { borderColor: 'var(--cyan)', color: 'var(--cyan)' } : {}}
        >
          AGENTS ({agents.length})
        </button>
      </div>

      {loading && <p className="panel-empty">Loading...</p>}

      {/* Tools tab */}
      {!loading && tab === 'tools' && (
        <>
          <div style={{ fontSize: 10, letterSpacing: '0.15em', color: 'var(--amber)', marginBottom: 6, fontFamily: 'Orbitron, monospace' }}>
            REQUIRES CONFIRMATION ({confirmTools.filter(matches).length})
          </div>
          {confirmTools.filter(matches).map(t => <ToolRow key={t.name} t={t} />)}

          <div style={{ fontSize: 10, letterSpacing: '0.15em', color: 'var(--green)', marginTop: 16, marginBottom: 6, fontFamily: 'Orbitron, monospace' }}>
            SAFE / READ-ONLY ({safeTools.filter(matches).length})
          </div>
          {safeTools.filter(matches).map(t => <ToolRow key={t.name} t={t} />)}

          {tools.filter(matches).length === 0 && (
            <p className="panel-empty">No tools match "{filter}".</p>
          )}
        </>
      )}

      {/* Agents tab */}
      {!loading && tab === 'agents' && (
        <>
          {!selectedAgent && agents.filter(a => {
            if (!filter.trim()) return true
            const q = filter.toLowerCase()
            return a.name.toLowerCase().includes(q) || a.description.toLowerCase().includes(q)
          }).map(a => (
            <div key={a.name} className="panel-item" onClick={() => setSelAgent(a)} style={{ cursor: 'pointer' }}>
              <div className="panel-item-title" style={{ fontFamily: 'monospace', fontSize: 12 }}>{a.name}</div>
              <div className="panel-item-meta" style={{ fontSize: 11, lineHeight: 1.4 }}>
                {a.description}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>
                {a.tool_count} tool{a.tool_count !== 'all' && a.tool_count !== 1 ? 's' : ''} available
              </div>
            </div>
          ))}

          {selectedAgent && (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: 10, letterSpacing: '0.15em', color: 'var(--cyan)', fontFamily: 'Orbitron, monospace' }}>
                  {selectedAgent.name.toUpperCase()}
                </span>
                <button className="icon-btn" onClick={() => setSelAgent(null)}>back</button>
              </div>
              <div className="panel-item" style={{ cursor: 'default' }}>
                <div className="panel-item-meta" style={{ fontSize: 11, lineHeight: 1.4, marginBottom: 12 }}>
                  {selectedAgent.description}
                </div>
                <div style={{ fontSize: 10, letterSpacing: '0.15em', color: 'var(--text-dim)', marginBottom: 6, fontFamily: 'Orbitron, monospace' }}>
                  TOOL WHITELIST
                </div>
                {selectedAgent.tools ? (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {selectedAgent.tools.map(tn => (
                      <span key={tn} className="badge badge-open" style={{ fontSize: 10, fontFamily: 'monospace' }}>{tn}</span>
                    ))}
                  </div>
                ) : (
                  <span className="badge badge-done">ALL TOOLS</span>
                )}
              </div>
            </>
          )}

          {agents.length === 0 && <p className="panel-empty">No sub-agents registered.</p>}
        </>
      )}
    </HoloPanel>
  )
}