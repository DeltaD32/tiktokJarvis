import { useState, useEffect, useCallback } from 'react'
import { HoloPanel } from '../HoloPanel'
import { useAuth } from '../../contexts/AuthContext'

const AGENTS = [
  { name: 'researcher',      label: 'Researcher',      desc: 'Web research, URL fetching, host checking' },
  { name: 'presenter',       label: 'Presenter',       desc: 'Presentation design, PPT generation' },
  { name: 'secretary',       label: 'Secretary',       desc: 'Coordination, blackboard, conflict resolution' },
  { name: 'workflow_designer', label: 'Workflow Designer', desc: 'Workflow brainstorm, design, refinement' },
  { name: 'system_expert',   label: 'System Expert',   desc: 'Codebase inspection, code implementation' },
]

export function WorkflowDesignerPanel({ onClose, message }) {
  const { token } = useAuth()
  const [workflows, setWorkflows] = useState([])
  const [selected, setSelected]   = useState(null)
  const [loading, setLoading]     = useState(true)
  const [view, setView]           = useState('list')  // list | detail | editor
  const [editing, setEditing]     = useState(null)    // workflow being edited
  const [saving, setSaving]       = useState(false)
  const [running, setRunning]     = useState(false)
  const [runResult, setRunResult] = useState(null)
  const [error, setError]         = useState(null)
  const [wfFilter, setWfFilter]   = useState('')

  const fetchWorkflows = useCallback(() => {
    fetch('/api/workflows', { headers: token ? { 'Authorization': `Bearer ${token}` } : {} })
      .then(r => r.json())
      .then(data => { setWorkflows(data || []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  useEffect(() => { fetchWorkflows() }, [])

  const openWorkflow = (name) => {
    fetch(`/api/workflows/${encodeURIComponent(name)}`, { headers: token ? { 'Authorization': `Bearer ${token}` } : {} })
      .then(r => r.json())
      .then(data => { setSelected(data); setView('detail'); setError(null) })
      .catch(() => setError(`Failed to load workflow '${name}'`))
  }

  const deleteWorkflow = (name) => {
    if (!confirm(`Delete workflow '${name}'?`)) return
    fetch(`/api/workflows/${encodeURIComponent(name)}`, { method: 'DELETE', headers: token ? { 'Authorization': `Bearer ${token}` } : {} })
      .then(() => { fetchWorkflows(); setSelected(null); setView('list') })
      .catch(() => setError('Failed to delete'))
  }

  const runWorkflow = (name) => {
    setRunning(true)
    setRunResult(null)
    fetch(`/api/workflows/${encodeURIComponent(name)}/run`, { method: 'POST', headers: { ...(token ? { 'Authorization': `Bearer ${token}` } : {}), 'Content-Type': 'application/json' }, body: '{}' })
      .then(r => r.json())
      .then(data => { setRunResult(data); setRunning(false) })
      .catch(() => { setRunning(false); setError('Failed to run workflow') })
  }

  const startNewWorkflow = () => {
    setEditing({
      name: '',
      description: '',
      steps: [{ id: 's1', name: '', agent: 'researcher', task: '', depends_on: [] }],
      schedule: '',
    })
    setView('editor')
    setError(null)
  }

  const startEditWorkflow = (wf) => {
    setEditing({
      name: wf.name || '',
      description: wf.description || '',
      steps: wf.steps || [],
      schedule: wf.schedule || '',
    })
    setView('editor')
    setError(null)
  }

  const addStep = () => {
    const steps = [...editing.steps, {
      id: `s${editing.steps.length + 1}`,
      name: '',
      agent: 'researcher',
      task: '',
      depends_on: [],
    }]
    setEditing({ ...editing, steps })
  }

  const removeStep = (idx) => {
    const steps = editing.steps.filter((_, i) => i !== idx)
    setEditing({ ...editing, steps })
  }

  const updateStep = (idx, field, value) => {
    const steps = editing.steps.map((s, i) => i === idx ? { ...s, [field]: value } : s)
    setEditing({ ...editing, steps })
  }

  const saveWorkflow = () => {
    if (!editing.name.trim()) { setError('Workflow name is required'); return }
    if (!editing.steps.length) { setError('At least one step is required'); return }
    setSaving(true)
    setError(null)
    fetch('/api/workflows', {
      method: 'POST',
      headers: { ...(token ? { 'Authorization': `Bearer ${token}` } : {}), 'Content-Type': 'application/json' },
      body: JSON.stringify(editing),
    })
      .then(r => r.json())
      .then(() => {
        setSaving(false)
        setView('list')
        setEditing(null)
        fetchWorkflows()
      })
      .catch(() => { setSaving(false); setError('Failed to save') })
  }

  const agentColor = (name) => ({
    researcher: 'var(--cyan)',
    presenter: 'var(--green)',
    secretary: 'var(--amber)',
    workflow_designer: 'var(--accent)',
    system_expert: 'var(--red)',
  })[name] || 'var(--text-dim)'

  return (
    <HoloPanel title="Workflow Designer" message={message} onClose={onClose}>
      {loading && <p className="panel-empty">Loading...</p>}

      {!loading && view === 'list' && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)', fontFamily: "'JetBrains Mono', monospace" }}>
              {workflows.length} WORKFLOW{workflows.length !== 1 ? 'S' : ''}
            </div>
            <button
              className="icon-btn"
              onClick={startNewWorkflow}
              style={{ borderColor: 'var(--accent)', color: 'var(--accent)', padding: '6px 12px', fontSize: 9 }}
            >
              + NEW
            </button>
          </div>

          <input
            className="chat-input"
            style={{ width: '100%', fontSize: 11, marginBottom: 8 }}
            placeholder="Filter workflows..."
            value={wfFilter}
            onChange={e => setWfFilter(e.target.value)}
          />

          {workflows.length === 0 && (
            <div className="panel-empty" style={{ padding: 20 }}>
              No workflows yet. Click + NEW to design one, or ask Dela to "design a workflow" in chat.
            </div>
          )}

          {workflows.filter(w => !wfFilter || w.name.toLowerCase().includes(wfFilter.toLowerCase())).map(wf => (
            <div key={wf.name} className="panel-item" style={{ cursor: 'pointer' }} onClick={() => openWorkflow(wf.name)}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span className="panel-item-title" style={{ fontSize: 13 }}>{wf.name}</span>
                <span style={{ fontSize: 9, color: 'var(--text-dim)' }}>{wf.steps} step{wf.steps !== 1 ? 's' : ''}</span>
              </div>
              <div className="panel-item-meta" style={{ fontSize: 10 }}>
                {wf.description.slice(0, 80)}{wf.description.length > 80 ? '...' : ''}
              </div>
              {wf.schedule && (
                <div style={{ fontSize: 9, color: 'var(--accent)', marginTop: 4, fontFamily: "'JetBrains Mono', monospace" }}>
                  SCHEDULE: {wf.schedule}
                </div>
              )}
            </div>
          ))}
        </>
      )}

      {!loading && view === 'detail' && selected && (
        <>
          <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
            <button className="data-btn" onClick={() => { setView('list'); setSelected(null) }}>&lt; BACK</button>
            <button className="data-btn" onClick={() => startEditWorkflow(selected)} style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }}>EDIT</button>
            <button className="data-btn" onClick={() => runWorkflow(selected.name)} disabled={running} style={{ borderColor: 'var(--green)', color: 'var(--green)' }}>
              {running ? 'RUNNING...' : 'RUN'}
            </button>
            <button className="data-btn" onClick={() => deleteWorkflow(selected.name)} style={{ borderColor: 'var(--red)', color: 'var(--red)' }}>DELETE</button>
          </div>

          {error && <div style={{ color: 'var(--red)', fontSize: 11, marginBottom: 8 }}>{error}</div>}

          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)', fontFamily: "'JetBrains Mono', monospace" }}>
              {selected.name}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 4 }}>
              {selected.description}
            </div>
            {selected.schedule && (
              <div style={{ fontSize: 9, color: 'var(--accent)', marginTop: 6, fontFamily: "'JetBrains Mono', monospace" }}>
                SCHEDULE: {selected.schedule}
              </div>
            )}
          </div>

          {/* Workflow steps visualization */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {(selected.steps || []).map((step, i) => (
              <div key={step.id || i} style={{ position: 'relative', paddingLeft: 20 }}>
                {/* Vertical connector line */}
                {i < (selected.steps || []).length - 1 && (
                  <div style={{
                    position: 'absolute', left: 6, top: 16, bottom: -8,
                    width: 1, background: 'var(--border)',
                  }} />
                )}
                {/* Step dot */}
                <div style={{
                  position: 'absolute', left: 2, top: 8,
                  width: 9, height: 9, borderRadius: '50%',
                  background: agentColor(step.agent),
                  boxShadow: `0 0 4px ${agentColor(step.agent)}`,
                }} />
                {/* Step content */}
                <div className="panel-item" style={{ marginBottom: 8, borderLeft: `3px solid ${agentColor(step.agent)}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <span className="panel-item-title" style={{ fontSize: 12 }}>
                      {step.id}. {step.name || step.id}
                    </span>
                    <span style={{
                      fontSize: 9, fontWeight: 600,
                      color: agentColor(step.agent),
                      border: `1px solid ${agentColor(step.agent)}`,
                      borderRadius: 3, padding: '1px 5px',
                      fontFamily: "'JetBrains Mono', monospace",
                    }}>
                      {step.agent}
                    </span>
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-3)', lineHeight: 1.4 }}>
                    {step.task}
                  </div>
                  {step.depends_on && step.depends_on.length > 0 && (
                    <div style={{ fontSize: 9, color: 'var(--text-dim)', marginTop: 4 }}>
                      depends on: {step.depends_on.join(', ')}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Run result */}
          {runResult && (
            <div style={{ marginTop: 12, padding: 14, borderRadius: 10, background: 'rgba(0,0,0,0.4)', border: '1px solid var(--accent)' }}>
              <div style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--accent)', marginBottom: 8, fontFamily: "'JetBrains Mono', monospace" }}>
                EXECUTION RESULT
              </div>
              {runResult.error ? (
                <div style={{ fontSize: 11, color: 'var(--red)' }}>{runResult.error}</div>
              ) : (
                <>
                  <div style={{ fontSize: 11, color: 'var(--text-2)', marginBottom: 8 }}>
                    {runResult.completed}/{runResult.total} completed, {runResult.failed} failed
                  </div>
                  {Object.entries(runResult.results || {}).map(([stepId, result]) => (
                    <div key={stepId} style={{ fontSize: 10, color: 'var(--text-3)', marginBottom: 4, whiteSpace: 'pre-wrap' }}>
                      <span style={{ color: 'var(--accent)' }}>{stepId}:</span> {String(result).slice(0, 200)}
                    </div>
                  ))}
                </>
              )}
            </div>
          )}
        </>
      )}

      {!loading && view === 'editor' && editing && (
        <>
          <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
            <button className="data-btn" onClick={() => { setView('list'); setEditing(null) }}>&lt; CANCEL</button>
            <button className="data-btn" onClick={saveWorkflow} disabled={saving} style={{ borderColor: 'var(--green)', color: 'var(--green)' }}>
              {saving ? 'SAVING...' : 'SAVE'}
            </button>
          </div>

          {error && <div style={{ color: 'var(--red)', fontSize: 11, marginBottom: 8 }}>{error}</div>}

          {/* Workflow metadata */}
          <div style={{ marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div>
              <label style={{ fontSize: 9, color: 'var(--text-dim)', letterSpacing: '0.1em', fontFamily: "'JetBrains Mono', monospace" }}>NAME</label>
              <input
                style={{
                  width: '100%', padding: '8px 10px', marginTop: 4,
                  background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)',
                  borderRadius: 6, color: 'var(--text)', fontSize: 12,
                  fontFamily: "'JetBrains Mono', monospace",
                }}
                value={editing.name}
                onChange={e => setEditing({ ...editing, name: e.target.value })}
                placeholder="my-workflow"
              />
            </div>
            <div>
              <label style={{ fontSize: 9, color: 'var(--text-dim)', letterSpacing: '0.1em', fontFamily: "'JetBrains Mono', monospace" }}>DESCRIPTION</label>
              <input
                style={{
                  width: '100%', padding: '8px 10px', marginTop: 4,
                  background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)',
                  borderRadius: 6, color: 'var(--text)', fontSize: 12,
                }}
                value={editing.description}
                onChange={e => setEditing({ ...editing, description: e.target.value })}
                placeholder="What this workflow does"
              />
            </div>
            <div>
              <label style={{ fontSize: 9, color: 'var(--text-dim)', letterSpacing: '0.1em', fontFamily: "'JetBrains Mono', monospace" }}>SCHEDULE (optional cron)</label>
              <input
                style={{
                  width: '100%', padding: '8px 10px', marginTop: 4,
                  background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)',
                  borderRadius: 6, color: 'var(--text)', fontSize: 12,
                  fontFamily: "'JetBrains Mono', monospace",
                }}
                value={editing.schedule}
                onChange={e => setEditing({ ...editing, schedule: e.target.value })}
                placeholder="0 9 * * *  (daily at 9am)"
              />
            </div>
          </div>

          {/* Steps editor */}
          <div style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)', marginBottom: 8, fontFamily: "'JetBrains Mono', monospace" }}>
            STEPS ({editing.steps.length})
          </div>

          {editing.steps.map((step, idx) => (
            <div key={idx} style={{
              marginBottom: 12, padding: 12, borderRadius: 10,
              background: 'rgba(0,0,0,0.3)', border: `1px solid ${agentColor(step.agent)}40`,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: agentColor(step.agent), fontFamily: "'JetBrains Mono', monospace" }}>
                  STEP {step.id}
                </span>
                {editing.steps.length > 1 && (
                  <button className="data-btn" onClick={() => removeStep(idx)} style={{ borderColor: 'var(--red)', color: 'var(--red)' }}>REMOVE</button>
                )}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
                <div>
                  <label style={{ fontSize: 8, color: 'var(--text-dim)' }}>ID</label>
                  <input
                    style={{ width: '100%', padding: '5px 8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text)', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
                    value={step.id}
                    onChange={e => updateStep(idx, 'id', e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 8, color: 'var(--text-dim)' }}>NAME</label>
                  <input
                    style={{ width: '100%', padding: '5px 8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text)', fontSize: 11 }}
                    value={step.name}
                    onChange={e => updateStep(idx, 'name', e.target.value)}
                    placeholder="Step name"
                  />
                </div>
              </div>

              <div style={{ marginBottom: 8 }}>
                <label style={{ fontSize: 8, color: 'var(--text-dim)' }}>AGENT</label>
                <select
                  style={{ width: '100%', padding: '5px 8px', background: 'rgba(0,0,0,0.3)', border: `1px solid ${agentColor(step.agent)}`, borderRadius: 4, color: agentColor(step.agent), fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
                  value={step.agent}
                  onChange={e => updateStep(idx, 'agent', e.target.value)}
                >
                  {AGENTS.map(a => (
                    <option key={a.name} value={a.name} style={{ color: 'var(--text)' }}>
                      {a.label} — {a.desc}
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ marginBottom: 8 }}>
                <label style={{ fontSize: 8, color: 'var(--text-dim)' }}>TASK</label>
                <textarea
                  style={{ width: '100%', padding: '5px 8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text)', fontSize: 11, minHeight: 50, resize: 'vertical' }}
                  value={step.task}
                  onChange={e => updateStep(idx, 'task', e.target.value)}
                  placeholder="What the agent should do..."
                />
              </div>

              <div>
                <label style={{ fontSize: 8, color: 'var(--text-dim)' }}>DEPENDS ON (comma-separated step IDs)</label>
                <input
                  style={{ width: '100%', padding: '5px 8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text)', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
                  value={(step.depends_on || []).join(', ')}
                  onChange={e => updateStep(idx, 'depends_on', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                  placeholder="s1, s2  (empty = runs immediately)"
                />
              </div>
            </div>
          ))}

          <button
            className="icon-btn"
            onClick={addStep}
            style={{ borderColor: 'var(--accent)', color: 'var(--accent)', width: '100%', padding: '8px' }}
          >
            + ADD STEP
          </button>
        </>
      )}
    </HoloPanel>
  )
}
