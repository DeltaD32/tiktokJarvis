import { useState, useEffect } from 'react'
import { HoloPanel } from '../HoloPanel'

export function TasksPanel({ onClose, message }) {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/tasks')
      .then(r => r.json())
      .then(data => { setTasks(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const open   = tasks.filter(t => t.status === 'open')
  const done   = tasks.filter(t => t.status === 'done')

  return (
    <HoloPanel title="Task List" message={message} onClose={onClose}>
      {loading && <p className="panel-empty">Loading…</p>}

      {!loading && tasks.length === 0 && (
        <p className="panel-empty">No tasks found.</p>
      )}

      {open.length > 0 && (
        <>
          <div style={{ fontSize: 10, letterSpacing: '0.15em', color: 'var(--text-dim)', marginBottom: 8, fontFamily: 'Orbitron, monospace' }}>
            OPEN — {open.length}
          </div>
          {open.map(t => (
            <div key={t.id} className="panel-item">
              <div className="panel-item-title">{t.title}</div>
              <div className="panel-item-meta">
                <span className="badge badge-open">open</span>
                {t.due && <span style={{ marginLeft: 8 }}>due {t.due}</span>}
              </div>
            </div>
          ))}
        </>
      )}

      {done.length > 0 && (
        <>
          <div style={{ fontSize: 10, letterSpacing: '0.15em', color: 'var(--text-dim)', margin: '16px 0 8px', fontFamily: 'Orbitron, monospace' }}>
            COMPLETED — {done.length}
          </div>
          {done.map(t => (
            <div key={t.id} className="panel-item" style={{ opacity: 0.5 }}>
              <div className="panel-item-title" style={{ textDecoration: 'line-through' }}>{t.title}</div>
              <div className="panel-item-meta">
                <span className="badge badge-done">done</span>
                {t.due && <span style={{ marginLeft: 8 }}>was due {t.due}</span>}
              </div>
            </div>
          ))}
        </>
      )}
    </HoloPanel>
  )
}
