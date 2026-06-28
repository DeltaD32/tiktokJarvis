const STATE_LABELS = {
  idle:      'STANDBY',
  thinking:  'PROCESSING',
  listening: 'LISTENING',
  speaking:  'RESPONDING',
  alert:     'AWAITING INPUT',
}

export function TopBar({
  orbState,
  heartbeatActive,
  cost,
  noticeCount,
  connected,
  onKill,
  onResume,
  onOpenNotices,
  onOpenAudit,
  onOpenMemory,
}) {
  const dotClass = orbState === 'alert'
    ? 'status-dot alert'
    : orbState !== 'idle'
    ? 'status-dot active'
    : 'status-dot'

  return (
    <div className="top-bar">
      <span className="top-bar-logo">DELA</span>

      <div className="top-bar-status">
        <span className={dotClass} />
        <span>{STATE_LABELS[orbState] ?? 'STANDBY'}</span>
      </div>

      {!connected && (
        <span style={{ color: 'var(--amber)', fontSize: 10, letterSpacing: '0.1em' }}>
          ⚡ RECONNECTING
        </span>
      )}

      <span className="top-bar-spacer" />

      <div className="top-bar-meta">
        <span style={{ color: 'var(--text-dim)', fontSize: 11 }}>{cost}</span>

        {noticeCount > 0 && (
          <button
            className="icon-btn"
            onClick={onOpenNotices}
            style={{ border: '1px solid rgba(255,51,0,0.4)', color: 'var(--red)' }}
          >
            <span className="notice-badge">{noticeCount}</span>&nbsp;NOTICES
          </button>
        )}

        <button
          className="hb-btn"
          onClick={heartbeatActive ? onKill : onResume}
        >
          {heartbeatActive ? '♥ HB ON' : '○ HB OFF'}
        </button>

        <button className="hb-btn" onClick={onOpenAudit}>AUDIT</button>
        <button className="hb-btn" onClick={onOpenMemory}>MEMORY</button>
      </div>
    </div>
  )
}
