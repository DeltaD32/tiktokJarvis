import { useState, useEffect } from 'react'
import { FloatWindow } from './FloatWindow'

export function SandboxWindow({ panel, onClose, onFocus, onDragMove, toolStatus, conversation }) {
  const [tab, setTab] = useState('terminal')
  const [tools, setTools] = useState([])
  const [agents, setAgents] = useState([])

  useEffect(() => {
    fetch('/api/tools').then(r => r.json()).then(setTools).catch(() => {})
    fetch('/api/agents').then(r => r.json()).then(setAgents).catch(() => {})
  }, [])

  const confirmTools = tools.filter(t => t.requires_confirmation)
  const safeTools = tools.filter(t => !t.requires_confirmation)

  const tabStyle = (name) => ({
    color: tab === name ? 'var(--text)' : 'var(--text-dim)',
    borderBottom: tab === name ? '2px solid var(--accent)' : '2px solid transparent',
  })

  return (
    <FloatWindow
      title="SANDBOX"
      x={panel.x} y={panel.y} z={panel.z}
      onClose={onClose}
      onFocus={onFocus}
      onDragMove={onDragMove}
      width={430}
      height="min(560px, 72vh)"
    >
      {/* Tabs */}
      <div className="sandbox-tabs">
        <button className={`sandbox-tab ${tab === 'terminal' ? 'active' : ''}`} onClick={() => setTab('terminal')}>terminal</button>
        <button className={`sandbox-tab ${tab === 'tools' ? 'active' : ''}`} onClick={() => setTab('tools')}>tools</button>
        <button className={`sandbox-tab ${tab === 'agents' ? 'active' : ''}`} onClick={() => setTab('agents')}>agents</button>
      </div>

      {/* Terminal tab */}
      {tab === 'terminal' && (
        <div className="float-body" style={{ padding: '14px 16px' }}>
          {toolStatus ? (
            <div className="term-line" style={{ color: 'var(--amber)' }}>{toolStatus}</div>
          ) : (
            <div className="term-line" style={{ color: 'var(--text-dim)' }}>
              $ awaiting command...{<span style={{ animation: 'jblink 1s steps(1) infinite', color: 'var(--accent)' }}>▍</span>}
            </div>
          )}
          {conversation.slice(-10).map((msg, i) => (
            <div key={i} className="term-line" style={{
              color: msg.role === 'user' ? 'var(--cyan)' : 'var(--text-3)',
              marginTop: 4,
            }}>
              {msg.role === 'user' ? '$ ' : '> '}{msg.content.slice(0, 120)}
              {msg.content.length > 120 ? '...' : ''}
            </div>
          ))}
        </div>
      )}

      {/* Tools tab */}
      {tab === 'tools' && (
        <div className="float-body">
          <div style={{ fontSize: 10, letterSpacing: '0.15em', color: 'var(--amber)', marginBottom: 6, font: "600 10px 'JetBrains Mono', monospace" }}>
            REQUIRES CONFIRMATION ({confirmTools.length})
          </div>
          {confirmTools.map(t => (
            <div key={t.name} className="panel-item">
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="panel-item-title" style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>{t.name}</span>
                <span className="badge badge-alert">CONFIRM</span>
              </div>
              <div className="panel-item-meta" style={{ fontSize: 10, marginTop: 4 }}>{t.description.slice(0, 80)}...</div>
            </div>
          ))}
          <div style={{ fontSize: 10, letterSpacing: '0.15em', color: 'var(--green)', marginTop: 16, marginBottom: 6, font: "600 10px 'JetBrains Mono', monospace" }}>
            SAFE / READ-ONLY ({safeTools.length})
          </div>
          {safeTools.map(t => (
            <div key={t.name} className="panel-item">
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="panel-item-title" style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>{t.name}</span>
                <span className="badge badge-done">SAFE</span>
              </div>
              <div className="panel-item-meta" style={{ fontSize: 10, marginTop: 4 }}>{t.description.slice(0, 80)}...</div>
            </div>
          ))}
        </div>
      )}

      {/* Agents tab */}
      {tab === 'agents' && (
        <div className="float-body">
          {agents.map(a => (
            <div key={a.name} className="panel-item">
              <div className="panel-item-title" style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>{a.name}</div>
              <div className="panel-item-meta" style={{ fontSize: 10, lineHeight: 1.4, marginTop: 4 }}>
                {a.description.slice(0, 100)}...
              </div>
              <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {a.tools ? a.tools.slice(0, 8).map(tn => (
                  <span key={tn} className="badge badge-open" style={{ fontSize: 9 }}>{tn}</span>
                )) : <span className="badge badge-done">ALL TOOLS</span>}
                {a.tools && a.tools.length > 8 && <span className="badge badge-info">+{a.tools.length - 8} more</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </FloatWindow>
  )
}
