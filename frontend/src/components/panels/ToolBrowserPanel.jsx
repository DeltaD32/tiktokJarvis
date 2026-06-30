import { useState, useEffect } from 'react'
import { HoloPanel } from '../HoloPanel'

function ToolAuditor({ tool, onClose }) {
  const [testArgs, setTestArgs] = useState('{}')
  const [result, setResult] = useState(null)
  const [running, setRunning] = useState(false)

  const runAudit = () => {
    setRunning(true)
    setResult(null)
    fetch('/api/audit/tool', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: tool.name,
        description: tool.description || '',
        parameters: tool.parameters || {},
        requires_confirmation: tool.requires_confirmation || false,
      }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.ok) {
          setResult({
            score: data.scores.impact,
            security: data.scores.security,
            usability: data.scores.usability,
            efficiency: data.scores.efficiency,
            overall: data.overall,
            grade: data.grade,
            findings: data.findings.map(f => `${f.severity.toUpperCase()}: ${f.message}${f.suggestion ? ' — ' + f.suggestion : ''}`)
          })
        }
        setRunning(false)
      })
      .catch(() => setRunning(false))
  }

  return (
    <div style={{ padding: '10px 12px', borderRadius: 10, background: 'rgba(0,240,255,0.03)', border: '1px solid rgba(0,240,255,0.15)', marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 10, letterSpacing: '0.15em', color: 'var(--cyan)', fontFamily: "'JetBrains Mono', monospace" }}>
          TOOL AUDITOR — {tool.name}
        </span>
        <button className="icon-btn" onClick={onClose} style={{ fontSize: 9 }}>close</button>
      </div>

      {/* Impact & scores */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 10 }}>
        {result ? (
          <>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: result.overall >= 7 ? 'var(--green)' : result.overall >= 5 ? 'var(--amber)' : 'var(--red)', fontFamily: "'JetBrains Mono', monospace" }}>
                {result.grade}
              </div>
              <div style={{ fontSize: 8, color: 'var(--text-dim)', letterSpacing: '0.1em' }}>GRADE</div>
            </div>
            {['security', 'usability', 'impact', 'efficiency'].map(k => (
              <div key={k} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: result[k] >= 7 ? 'var(--green)' : result[k] >= 4 ? 'var(--amber)' : 'var(--red)', fontFamily: "'JetBrains Mono', monospace" }}>
                  {result[k].toFixed(1)}
                </div>
                <div style={{ fontSize: 7, color: 'var(--text-dim)', letterSpacing: '0.1em' }}>{k.slice(0, 3).toUpperCase()}</div>
              </div>
            ))}
          </>
        ) : (
          <>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: tool.requires_confirmation ? 'var(--red)' : 'var(--green)', fontFamily: "'JetBrains Mono', monospace" }}>
                {tool.requires_confirmation ? 'HIGH' : 'LOW'}
              </div>
              <div style={{ fontSize: 8, color: 'var(--text-dim)', letterSpacing: '0.1em' }}>IMPACT</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--accent)', fontFamily: "'JetBrains Mono', monospace" }}>
                {tool.param_count || 0}
              </div>
              <div style={{ fontSize: 8, color: 'var(--text-dim)', letterSpacing: '0.1em' }}>PARAMS</div>
            </div>
            <div style={{ flex: 1 }} />
            <button className="chip active" onClick={runAudit} disabled={running} style={{ fontSize: 9, alignSelf: 'center' }}>
              {running ? 'Auditing...' : 'Run Audit'}
            </button>
          </>
        )}
      </div>

      {/* Show audit button if not yet run */}
      {!result && (
        <div style={{ flex: 1, display: 'flex', justifyContent: 'flex-end' }}>
          <button className="chip active" onClick={runAudit} disabled={running} style={{ fontSize: 9 }}>
            {running ? 'Auditing...' : 'Run Audit'}
          </button>
        </div>
      )}

      {/* Run audit button moved above */}

      {/* Parameters schema */}
      {tool.parameters?.properties && (
        <div style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 9, letterSpacing: '0.1em', color: 'var(--text-dim)', marginBottom: 4, fontFamily: "'JetBrains Mono', monospace" }}>
            PARAMETERS
          </div>
          {Object.entries(tool.parameters.properties).map(([key, prop]) => (
            <div key={key} style={{ fontSize: 10, padding: '2px 0', display: 'flex', gap: 8 }}>
              <span style={{ color: 'var(--accent)', fontFamily: "'JetBrains Mono', monospace", minWidth: 100 }}>{key}</span>
              <span style={{ color: 'var(--text-dim)' }}>{prop.type}</span>
              {tool.parameters.required?.includes(key) && (
                <span style={{ color: 'var(--red)', fontSize: 8 }}>REQUIRED</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Audit results */}
      {result && (
        <div style={{ padding: '8px 10px', borderRadius: 6, background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border)' }}>
          <div style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--text-dim)', marginBottom: 6, fontFamily: "'JetBrains Mono', monospace" }}>
            FINDINGS ({result.findings.length})
          </div>
          {result.findings.map((f, i) => {
            const sevColor = f.includes('CRITICAL') ? 'var(--red)' : f.includes('HIGH') ? 'var(--amber)' : f.includes('MEDIUM') ? 'var(--accent)' : 'var(--text-dim)'
            return (
              <div key={i} style={{ fontSize: 10, color: 'var(--text)', marginBottom: 3, paddingLeft: 8, borderLeft: `2px solid ${sevColor}` }}>
                {f}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export function ToolBrowserPanel({ onClose, message }) {
  const [tools, setTools]           = useState([])
  const [agents, setAgents]         = useState([])
  const [loading, setLoading]       = useState(true)
  const [filter, setFilter]         = useState('')
  const [tab, setTab]               = useState('tools')
  const [selectedAgent, setSelAgent] = useState(null)
  const [auditingTool, setAuditingTool] = useState(null)
  const [createMode, setCreateMode]  = useState(false)
  const [agentRequest, setAgentRequest] = useState('')
  const [agentPipeline, setAgentPipeline] = useState(null)

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

  const requestAgent = () => {
    if (!agentRequest.trim()) return
    setCreateMode(false)
    setAgentPipeline({
      request: agentRequest,
      stages: [
        { name: 'Plan', status: 'pending', detail: '' },
        { name: 'Build', status: 'pending', detail: '' },
        { name: 'Test', status: 'pending', detail: '' },
        { name: 'Validate', status: 'pending', detail: '' },
        { name: 'Harden', status: 'pending', detail: '' },
        { name: 'Deploy', status: 'pending', detail: '' },
      ]
    })
    setAgentRequest('')

    // Simulate pipeline — in production this dispatches to system_expert
    const stages = ['Plan', 'Build', 'Test', 'Validate', 'Harden', 'Deploy']
    const details = [
      'Analyzing requirements, designing agent spec, selecting tools',
      'Writing agent module, registering with decorator, defining Soul',
      'Running unit tests, validating tool whitelist, checking imports',
      'Security review: input validation, path traversal, env injection',
      'Hardening: adding rate limits, error boundaries, audit logging',
      'Deploying: registering agent, updating roster, broadcasting status'
    ]
    stages.forEach((stage, i) => {
      setTimeout(() => {
        setAgentPipeline(prev => {
          if (!prev) return prev
          const newStages = [...prev.stages]
          newStages[i] = { ...newStages[i], status: 'running', detail: details[i] }
          return { ...prev, stages: newStages }
        })
        setTimeout(() => {
          setAgentPipeline(prev => {
            if (!prev) return prev
            const newStages = [...prev.stages]
            newStages[i] = { ...newStages[i], status: 'done' }
            return { ...prev, stages: newStages }
          })
        }, 1500)
      }, i * 2000)
    })
  }

  const ToolRow = ({ t }) => (
    <div className="panel-item" style={{ cursor: 'pointer' }} onClick={() => setAuditingTool(t)}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
        <span className="panel-item-title" style={{ fontFamily: 'monospace', fontSize: 12 }}>{t.name}</span>
        <div style={{ display: 'flex', gap: 4 }}>
          <span style={{ fontSize: 9, color: 'var(--text-dim)', fontFamily: "'JetBrains Mono', monospace" }}>
            {t.param_count || 0}p
          </span>
          {t.requires_confirmation ? (
            <span className="badge badge-attention" title="Requires user confirmation">CONFIRM</span>
          ) : (
            <span className="badge badge-done" title="Safe — no confirmation needed">SAFE</span>
          )}
        </div>
      </div>
      <div className="panel-item-meta" style={{ fontSize: 11, lineHeight: 1.4 }}>
        {t.description.length > 100 ? t.description.slice(0, 100) + '...' : t.description}
      </div>
    </div>
  )

  return (
    <HoloPanel title={`Tools & Agents (${tools.length}t / ${agents.length}a)`} message={message} onClose={onClose}>
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
        {['tools', 'agents'].map(t => (
          <button key={t} className={`data-btn ${tab === t ? 'active' : ''}`}
            onClick={() => { setTab(t); setAuditingTool(null); setAgentPipeline(null) }}
            style={tab === t ? { borderColor: 'var(--accent)', color: 'var(--accent)' } : {}}
          >
            {t.toUpperCase()} ({t === 'tools' ? tools.length : agents.length})
          </button>
        ))}
      </div>

      {loading && <p className="panel-empty">Loading...</p>}

      {/* ── TOOLS TAB ── */}
      {!loading && tab === 'tools' && (
        <>
          {auditingTool ? (
            <ToolAuditor tool={auditingTool} onClose={() => setAuditingTool(null)} />
          ) : (
            <>
              <div style={{ fontSize: 10, letterSpacing: '0.15em', color: 'var(--amber)', marginBottom: 6, fontFamily: "'JetBrains Mono', monospace" }}>
                REQUIRES CONFIRMATION ({confirmTools.filter(matches).length})
              </div>
              {confirmTools.filter(matches).slice(0, 15).map(t => <ToolRow key={t.name} t={t} />)}

              <div style={{ fontSize: 10, letterSpacing: '0.15em', color: 'var(--green)', marginTop: 16, marginBottom: 6, fontFamily: "'JetBrains Mono', monospace" }}>
                SAFE / READ-ONLY ({safeTools.filter(matches).length})
              </div>
              {safeTools.filter(matches).slice(0, 15).map(t => <ToolRow key={t.name} t={t} />)}

              {tools.filter(matches).length === 0 && (
                <p className="panel-empty">No tools match "{filter}".</p>
              )}
            </>
          )}
        </>
      )}

      {/* ── AGENTS TAB ── */}
      {!loading && tab === 'agents' && (
        <>
          {/* Create Agent button */}
          {!selectedAgent && !agentPipeline && (
            <div style={{ marginBottom: 12 }}>
              <button className="chip active" onClick={() => setCreateMode(!createMode)} style={{ fontSize: 10 }}>
                {createMode ? 'Cancel' : '+ Create Agent'}
              </button>
            </div>
          )}

          {/* Create Agent request form */}
          {createMode && (
            <div style={{ padding: '10px 12px', borderRadius: 10, background: 'rgba(70,242,176,0.03)', border: '1px solid rgba(70,242,176,0.2)', marginBottom: 12 }}>
              <div style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--green)', marginBottom: 6, fontFamily: "'JetBrains Mono', monospace" }}>
                CREATE AGENT
              </div>
              <textarea
                className="chat-input"
                style={{ width: '100%', minHeight: 60, fontSize: 11, resize: 'vertical', marginBottom: 8 }}
                value={agentRequest}
                onChange={e => setAgentRequest(e.target.value)}
                placeholder="Describe the agent you need, e.g.: 'A database migration agent that can run SQL migrations, validate schemas, and rollback on failure...'"
              />
              <button className="chip active" onClick={requestAgent} disabled={!agentRequest.trim()} style={{ fontSize: 9 }}>
                Request Agent
              </button>
            </div>
          )}

          {/* Agent creation pipeline */}
          {agentPipeline && (
            <div style={{ padding: '10px 12px', borderRadius: 10, background: 'rgba(70,242,176,0.03)', border: '1px solid rgba(70,242,176,0.2)', marginBottom: 12 }}>
              <div style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--green)', marginBottom: 8, fontFamily: "'JetBrains Mono', monospace" }}>
                AGENT PIPELINE
              </div>
              <div style={{ fontSize: 10, color: 'var(--text)', marginBottom: 10, fontStyle: 'italic', opacity: 0.7 }}>
                "{agentPipeline.request}"
              </div>
              {agentPipeline.stages.map((stage, i) => (
                <div key={stage.name} style={{
                  display: 'flex', alignItems: 'center', gap: 10, padding: '4px 0',
                  opacity: stage.status === 'pending' ? 0.3 : 1,
                  borderLeft: stage.status === 'running' ? '2px solid var(--accent)' : '2px solid transparent',
                  paddingLeft: stage.status === 'running' ? 8 : 10,
                }}>
                  <span style={{
                    width: 18, height: 18, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 9, fontWeight: 700,
                    background: stage.status === 'done' ? 'rgba(70,242,176,0.2)' : stage.status === 'running' ? 'rgba(0,240,255,0.2)' : 'rgba(255,255,255,0.05)',
                    color: stage.status === 'done' ? 'var(--green)' : stage.status === 'running' ? 'var(--accent)' : 'var(--text-dim)',
                    animation: stage.status === 'running' ? 'jpulse 1.5s ease-in-out infinite' : 'none'
                  }}>
                    {stage.status === 'done' ? '✓' : stage.status === 'running' ? '◉' : (i + 1)}
                  </span>
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 600, color: stage.status === 'running' ? 'var(--accent)' : 'var(--text)' }}>
                      {stage.name}
                    </div>
                    {stage.detail && (
                      <div style={{ fontSize: 9, color: 'var(--text-dim)' }}>{stage.detail}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Agent list */}
          {!selectedAgent && !agentPipeline && agents.filter(a => {
            if (!filter.trim()) return true
            const q = filter.toLowerCase()
            return a.name.toLowerCase().includes(q) || a.description.toLowerCase().includes(q)
          }).map(a => (
            <div key={a.name} className="panel-item" onClick={() => setSelAgent(a)} style={{ cursor: 'pointer' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                <span className="panel-item-title" style={{ fontFamily: 'monospace', fontSize: 12 }}>{a.name}</span>
                <span className={`badge badge-${a.status === 'ready' ? 'done' : 'open'}`}>{a.status}</span>
              </div>
              <div className="panel-item-meta" style={{ fontSize: 11, lineHeight: 1.4 }}>
                {a.description.length > 100 ? a.description.slice(0, 100) + '...' : a.description}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>
                {a.tool_count} tool{a.tool_count !== 'all' && a.tool_count !== 1 ? 's' : ''}
              </div>
            </div>
          ))}

          {selectedAgent && (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: 10, letterSpacing: '0.15em', color: 'var(--cyan)', fontFamily: "'JetBrains Mono', monospace" }}>
                  {selectedAgent.name.toUpperCase()}
                </span>
                <button className="icon-btn" onClick={() => setSelAgent(null)}>back</button>
              </div>
              <div className="panel-item" style={{ cursor: 'default' }}>
                <div className="panel-item-meta" style={{ fontSize: 11, lineHeight: 1.4, marginBottom: 12 }}>
                  {selectedAgent.description}
                </div>
                <div style={{ fontSize: 10, letterSpacing: '0.15em', color: 'var(--text-dim)', marginBottom: 6, fontFamily: "'JetBrains Mono', monospace" }}>
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

          {agents.length === 0 && !agentPipeline && (
            <p className="panel-empty">No sub-agents registered. Click + Create Agent to build one.</p>
          )}
        </>
      )}
    </HoloPanel>
  )
}
