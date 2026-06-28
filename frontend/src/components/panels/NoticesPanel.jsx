import { HoloPanel } from '../HoloPanel'

function formatTime(ts) {
  const d = new Date(ts * 1000)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export function NoticesPanel({ onClose, message, notices, onDismiss }) {
  return (
    <HoloPanel title="Notices" message={message} onClose={onClose}>
      {notices.length === 0 && (
        <p className="panel-empty">No active notices.</p>
      )}

      {notices.map(n => (
        <div key={n.id} className="panel-item">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
            <span className={`badge badge-${n.severity}`}>{n.severity}</span>
            <button
              className="icon-btn"
              onClick={() => onDismiss(n.id)}
              style={{ fontSize: 10 }}
            >
              dismiss
            </button>
          </div>
          <div className="panel-item-title" style={{ marginBottom: 4 }}>{n.message}</div>
          <div className="panel-item-meta">
            {n.source} · {formatTime(n.created_at)}
          </div>
        </div>
      ))}
    </HoloPanel>
  )
}
