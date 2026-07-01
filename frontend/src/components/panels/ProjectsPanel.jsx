import { useState, useEffect, useCallback } from 'react'
import { HoloPanel } from '../HoloPanel'
import { useAuth } from '../../contexts/AuthContext'

const STATUS_COLORS = {
  open: 'var(--amber)', 'in_progress': 'var(--accent)', closed: 'var(--green)',
}

function ProjectDetail({ project, onBack }) {
  const { token } = useAuth()
  const [auditResult, setAuditResult] = useState(null)
  const [auditing, setAuditing] = useState(false)

  const runAudit = () => {
    setAuditing(true)
    fetch('/api/audit/workflow', {
      method: 'POST',
      headers: { ...(token ? { 'Authorization': `Bearer ${token}` } : {}), 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: project.name || 'Untitled', description: project.description || '', steps: project.steps || [] }),
    })
      .then(r => r.json())
      .then(data => { if (data.ok) setAuditResult(data); setAuditing(false) })
      .catch(() => setAuditing(false))
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--cyan)', fontFamily: "'JetBrains Mono', monospace" }}>
          {project.name?.toUpperCase?.() || 'PROJECT'}
        </span>
        <button className="icon-btn" onClick={onBack} style={{ fontSize: 9 }}>← back</button>
      </div>

      {/* Status */}
      <div style={{ marginBottom: 10 }}>
        <span style={{
          display: 'inline-block', padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 600,
          color: STATUS_COLORS[project.status] || 'var(--text-dim)',
          background: (STATUS_COLORS[project.status] || 'var(--text-dim)') + '18',
          border: `1px solid ${(STATUS_COLORS[project.status] || 'var(--text-dim)') + '33'}`,
        }}>
          {project.status || 'open'}
        </span>
      </div>

      {/* Tasks */}
      <div style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--text-dim)', marginBottom: 6, fontFamily: "'JetBrains Mono', monospace" }}>
        TASKS
      </div>
      {(project.tasks || []).map((t, i) => (
        <div key={i} className="panel-item" style={t.status === 'done' ? { opacity: 0.5 } : {}}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 11, textDecoration: t.status === 'done' ? 'line-through' : 'none' }}>
              {t.title || t.name || 'Untitled'}
            </span>
            <span className={`badge badge-${t.status === 'done' ? 'done' : 'open'}`} style={{ fontSize: 8 }}>
              {t.status || 'open'}
            </span>
          </div>
          {t.agent && <div style={{ fontSize: 9, color: 'var(--text-dim)', marginTop: 2 }}>Agent: {t.agent}</div>}
        </div>
      ))}

      {/* Agent steps */}
      {project.steps && project.steps.length > 0 && (
        <>
          <div style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--text-dim)', marginTop: 14, marginBottom: 6, fontFamily: "'JetBrains Mono', monospace" }}>
            AGENT STEPS
          </div>
          {project.steps.map((s, i) => (
            <div key={i} style={{
              padding: '6px 8px', marginBottom: 4, borderRadius: 6,
              background: 'rgba(0,240,255,0.03)', border: '1px solid var(--border)',
              fontSize: 10,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                <span style={{ color: 'var(--accent)', fontFamily: "'JetBrains Mono', monospace" }}>Step {i + 1}</span>
                <span style={{ color: 'var(--text-dim)', fontSize: 9 }}>{s.agent}</span>
              </div>
              <div style={{ color: 'var(--text)' }}>{s.task}</div>
              {s.notes && <div style={{ color: 'var(--text-dim)', fontSize: 9, marginTop: 2, fontStyle: 'italic' }}>📝 {s.notes}</div>}
            </div>
          ))}
        </>
      )}

      {/* Usefulness audit */}
      <div style={{ marginTop: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <span style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--text-dim)', fontFamily: "'JetBrains Mono', monospace" }}>
            USEFULNESS AUDIT
          </span>
          <button className="chip" onClick={runAudit} disabled={auditing} style={{ fontSize: 8 }}>
            {auditing ? 'Running...' : 'Run Audit'}
          </button>
        </div>
        {auditResult && (
          <div style={{ padding: '8px 10px', borderRadius: 6, background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', gap: 10, marginBottom: 6 }}>
              <span style={{ fontSize: 14, fontWeight: 700, color: auditResult.overall >= 7 ? 'var(--green)' : 'var(--amber)', fontFamily: "'JetBrains Mono', monospace" }}>
                {auditResult.grade}
              </span>
              <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>Overall: {auditResult.overall}/10</span>
            </div>
            {auditResult.findings.map((f, i) => (
              <div key={i} style={{ fontSize: 9, color: 'var(--text)', marginBottom: 2, paddingLeft: 6, borderLeft: `2px solid ${f.severity === 'high' ? 'var(--red)' : f.severity === 'medium' ? 'var(--amber)' : 'var(--text-dim)'}` }}>
                {f.message}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function ProjectsPanel({ onClose, message }) {
  const { token } = useAuth()
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [tab, setTab] = useState('all')
  const [selected, setSelected] = useState(null)
  const [expanded, setExpanded] = useState({})

  const fetchProjects = useCallback(() => {
    setLoading(true)
    // Try projects endpoint, fall back to tasks
    fetch('/api/state/projects', { headers: token ? { 'Authorization': `Bearer ${token}` } : {} })
      .then(r => r.json())
      .then(data => {
        const items = data?.items || data || []
        setProjects(Array.isArray(items) ? items : [])
        setLoading(false)
      })
      .catch(() => {
        // Fallback: fetch tasks and group
        fetch('/api/tasks', { headers: token ? { 'Authorization': `Bearer ${token}` } : {} })
          .then(r => r.json())
          .then(tasks => {
            // Mock projects from tasks for now
            const mock = [{
              name: 'Current Tasks', status: 'open',
              tasks: (tasks || []).map(t => ({ ...t, title: t.title || t.name })),
            }]
            setProjects(mock)
            setLoading(false)
          })
          .catch(() => setLoading(false))
      })
  }, [])

  useEffect(() => { fetchProjects() }, [fetchProjects])

  const toggleExpand = (name) => {
    setExpanded(prev => ({ ...prev, [name]: !prev[name] }))
  }

  const filtered = projects.filter(p => {
    if (tab !== 'all' && p.status !== tab) return false
    if (filter && !p.name?.toLowerCase().includes(filter.toLowerCase())) return false
    return true
  })

  const counts = { all: projects.length, open: 0, in_progress: 0, closed: 0 }
  projects.forEach(p => { if (counts[p.status] !== undefined) counts[p.status]++ })

  return (
    <HoloPanel title={`Projects (${projects.length})`} message={message} onClose={onClose}>
      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
        {Object.entries(counts).map(([key, count]) => (
          <button key={key} className={`chip ${tab === key ? 'active' : ''}`}
            onClick={() => setTab(key)} style={{ fontSize: 9 }}>
            {key.replace('_', ' ')} ({count})
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <button className="icon-btn" onClick={fetchProjects} style={{ fontSize: 9, opacity: 0.5 }}>↻</button>
      </div>

      <input className="chat-input" style={{ width: '100%', fontSize: 10, marginBottom: 8 }}
        value={filter} onChange={e => setFilter(e.target.value)} placeholder="Filter projects..." />

      {loading ? <p className="panel-empty">Loading...</p>
        : filtered.length === 0 ? <p className="panel-empty">{filter ? 'No matches.' : 'No projects yet.'}</p>
        : selected ? (
          <ProjectDetail project={selected} onBack={() => setSelected(null)} />
        ) : (
          filtered.map(p => (
            <div key={p.name} className="panel-item">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                onClick={() => toggleExpand(p.name)}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 9, color: 'var(--text-dim)' }}>{expanded[p.name] ? '▼' : '▶'}</span>
                  <span style={{ fontSize: 11, fontWeight: 600 }}>{p.name}</span>
                </div>
                <span style={{
                  fontSize: 8, padding: '1px 5px', borderRadius: 3,
                  color: STATUS_COLORS[p.status] || 'var(--text-dim)',
                  border: `1px solid ${(STATUS_COLORS[p.status] || 'var(--text-dim)') + '44'}`,
                }}>
                  {p.status || 'open'}
                </span>
              </div>

              {/* Collapsed summary */}
              <div style={{ fontSize: 9, color: 'var(--text-dim)', marginTop: 2 }}>
                {p.tasks?.length || 0} task{(p.tasks?.length || 0) !== 1 ? 's' : ''}
                {p.steps?.length ? ` · ${p.steps.length} agent steps` : ''}
              </div>

              {/* Expanded detail */}
              {expanded[p.name] && (
                <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--border)' }}>
                  {(p.tasks || []).slice(0, 5).map((t, i) => (
                    <div key={i} style={{ fontSize: 10, padding: '2px 0', display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ textDecoration: t.status === 'done' ? 'line-through' : 'none', opacity: t.status === 'done' ? 0.5 : 1 }}>
                        {t.title || t.name}
                      </span>
                      <span style={{ fontSize: 8, color: 'var(--text-dim)' }}>{t.status}</span>
                    </div>
                  ))}
                  {(p.tasks || []).length > 5 && (
                    <div style={{ fontSize: 9, color: 'var(--text-dim)', marginTop: 2 }}>
                      +{(p.tasks || []).length - 5} more tasks
                    </div>
                  )}
                  <button className="chip" onClick={(e) => { e.stopPropagation(); setSelected(p) }}
                    style={{ fontSize: 8, marginTop: 6 }}>
                    View Details
                  </button>
                </div>
              )}
            </div>
          ))
        )}
    </HoloPanel>
  )
}
