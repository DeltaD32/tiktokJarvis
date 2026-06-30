import { useState, useEffect, useCallback } from 'react'
import { HoloPanel } from '../HoloPanel'

export function TasksPanel({ onClose, message }) {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [tab, setTab] = useState('all') // all | open | done

  const fetchTasks = useCallback(() => {
    setLoading(true)
    fetch('/api/tasks')
      .then(r => r.json())
      .then(data => { setTasks(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  useEffect(() => { fetchTasks() }, [fetchTasks])

  const filtered = tasks.filter(t => {
    if (tab === 'open' && t.status !== 'open') return false
    if (tab === 'done' && t.status !== 'done') return false
    if (filter && !t.title?.toLowerCase().includes(filter.toLowerCase())) return false
    return true
  })

  const openCount = tasks.filter(t => t.status === 'open').length
  const doneCount = tasks.filter(t => t.status === 'done').length

  return (
    <HoloPanel title={`Tasks (${tasks.length})`} message={message} onClose={onClose}>
      {/* Tab bar */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 10 }}>
        {[
          ['all', `All (${tasks.length})`],
          ['open', `Open (${openCount})`],
          ['done', `Done (${doneCount})`],
        ].map(([key, label]) => (
          <button key={key} className={`chip ${tab === key ? 'active' : ''}`} onClick={() => setTab(key)} style={{ fontSize: 10 }}>
            {label}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <button className="icon-btn" onClick={fetchTasks} style={{ fontSize: 9, opacity: 0.6 }}>refresh</button>
      </div>

      {/* Search */}
      <input
        className="chat-input"
        style={{ width: '100%', fontSize: 11, marginBottom: 10 }}
        placeholder="Filter tasks..."
        value={filter}
        onChange={e => setFilter(e.target.value)}
      />

      {loading ? (
        <p className="panel-empty">Loading...</p>
      ) : filtered.length === 0 ? (
        <p className="panel-empty">{filter ? 'No matching tasks.' : 'No tasks found.'}</p>
      ) : (
        filtered.map(t => (
          <div key={t.id} className="panel-item" style={t.status === 'done' ? { opacity: 0.5 } : undefined}>
            <div className="panel-item-title" style={t.status === 'done' ? { textDecoration: 'line-through' } : undefined}>
              {t.title}
            </div>
            <div className="panel-item-meta">
              <span className={`badge badge-${t.status === 'done' ? 'done' : 'open'}`}>
                {t.status}
              </span>
              {t.due && <span style={{ marginLeft: 8 }}>{t.status === 'done' ? 'was due' : 'due'} {t.due}</span>}
            </div>
          </div>
        ))
      )}
    </HoloPanel>
  )
}
