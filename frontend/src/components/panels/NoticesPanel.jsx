import { useState } from 'react'
import { HoloPanel } from '../HoloPanel'

function formatTime(ts) {
  const d = new Date(ts * 1000)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export function NoticesPanel({ onClose, message, notices, onDismiss }) {
  const [severityFilter, setSeverityFilter] = useState('')

  const filtered = severityFilter
    ? notices.filter(n => n.severity === severityFilter)
    : notices

  const severities = [...new Set(notices.map(n => n.severity))].sort()

  const dismissAll = () => {
    if (!window.confirm(`Dismiss all ${notices.length} notices?`)) return
    notices.forEach(n => onDismiss(n.id))
  }

  return (
    <HoloPanel title={`Notices (${notices.length})`} message={message} onClose={onClose}>
      {/* Actions bar */}
      {notices.length > 0 && (
        <div style={{ display: 'flex', gap: 4, marginBottom: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <select
            className="chat-input"
            style={{ fontSize: 10, width: 100 }}
            value={severityFilter}
            onChange={e => setSeverityFilter(e.target.value)}
          >
            <option value="">All severities</option>
            {severities.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          {severityFilter && (
            <button className="icon-btn" onClick={() => setSeverityFilter('')} style={{ fontSize: 9 }}>clear</button>
          )}
          <div style={{ flex: 1 }} />
          <button className="icon-btn" onClick={dismissAll} style={{ fontSize: 9, color: 'var(--red)' }}>
            dismiss all
          </button>
        </div>
      )}

      {filtered.length === 0 ? (
        <p className="panel-empty">
          {notices.length === 0 ? 'No active notices.' : `No ${severityFilter} notices.`}
        </p>
      ) : (
        filtered.map(n => (
          <div key={n.id} className="panel-item">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
              <span className={`badge badge-${n.severity}`}>{n.severity}</span>
              <button className="icon-btn" onClick={() => onDismiss(n.id)} style={{ fontSize: 10 }}>
                dismiss
              </button>
            </div>
            <div className="panel-item-title" style={{ marginBottom: 4 }}>{n.message}</div>
            <div className="panel-item-meta">
              {n.source} · {formatTime(n.created_at)}
            </div>
          </div>
        ))
      )}
    </HoloPanel>
  )
}
