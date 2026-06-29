import { useState, useEffect } from 'react'
import { HoloPanel } from '../HoloPanel'

export function SecurityPanel({ onClose, message }) {
  const [report, setReport]   = useState(null)
  const [scanning, setScanning] = useState(false)
  const [loading, setLoading]   = useState(true)

  const refresh = () => {
    fetch('/api/security')
      .then(r => r.json())
      .then(data => { setReport(data); setLoading(false) })
      .catch(() => setLoading(false))
  }

  const runScan = () => {
    setScanning(true)
    fetch('/api/security/scan', { method: 'POST' })
      .then(r => r.json())
      .then(data => { setReport(data); setScanning(false) })
      .catch(() => setScanning(false))
  }

  useEffect(() => { refresh() }, [])

  const sevColor = (s) => ({
    critical: 'var(--red)',
    warning:  'var(--amber)',
    ok:       'var(--green)',
    info:     'var(--text-dim)',
  })[s] || 'var(--text-dim)'

  const sevBadge = (s) => ({
    critical: 'badge-alert',
    warning:  'badge-attention',
    ok:       'badge-done',
    info:     'badge-open',
  })[s] || 'badge-open'

  const scoreColor = report?.score >= 90 ? 'var(--green)' : report?.score >= 70 ? 'var(--amber)' : 'var(--red)'

  return (
    <HoloPanel title="Security Audit" message={message} onClose={onClose}>
      {loading && <p className="panel-empty">Loading...</p>}

      {!loading && report && (
        <>
          {/* Score + summary */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16, padding: 14, borderRadius: 12, background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 32, fontWeight: 700, color: scoreColor, fontFamily: "'JetBrains Mono', monospace" }}>
                {report.score}
              </div>
              <div style={{ fontSize: 9, letterSpacing: '0.14em', color: 'var(--text-dim)' }}>SCORE</div>
            </div>
            <div style={{ flex: 1, display: 'flex', gap: 12 }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 18, color: 'var(--red)' }}>{report.summary.critical}</div>
                <div style={{ fontSize: 8, color: 'var(--text-dim)' }}>CRITICAL</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 18, color: 'var(--amber)' }}>{report.summary.warning}</div>
                <div style={{ fontSize: 8, color: 'var(--text-dim)' }}>WARN</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 18, color: 'var(--green)' }}>{report.summary.ok}</div>
                <div style={{ fontSize: 8, color: 'var(--text-dim)' }}>OK</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 18, color: 'var(--text-3)' }}>{report.summary.info}</div>
                <div style={{ fontSize: 8, color: 'var(--text-dim)' }}>INFO</div>
              </div>
            </div>
            <button
              className="icon-btn"
              onClick={runScan}
              disabled={scanning}
              style={{ borderColor: 'var(--accent)', color: 'var(--accent)', padding: '8px 14px' }}
            >
              {scanning ? 'SCANNING...' : 'RESCAN'}
            </button>
          </div>

          {/* Findings */}
          {report.findings.map((f, i) => (
            <div key={i} className="panel-item" style={{ borderLeft: `3px solid ${sevColor(f.severity)}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span className="panel-item-title" style={{ fontSize: 12 }}>{f.title}</span>
                <span className={`badge ${sevBadge(f.severity)}`}>{f.severity}</span>
              </div>
              <div className="panel-item-meta" style={{ fontSize: 10 }}>
                <span style={{ color: 'var(--text-dim)' }}>[{f.category}]</span>
                {f.detail && <span style={{ marginLeft: 6 }}>{f.detail}</span>}
              </div>
            </div>
          ))}

          {/* Auto-scan info */}
          <div style={{ marginTop: 16, padding: 12, borderRadius: 10, background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)', marginBottom: 6, fontFamily: "'JetBrains Mono', monospace" }}>
              AUTO-SCAN
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-3)', lineHeight: 1.5 }}>
              The heartbeat runs a security scan periodically. Configure it in Settings &gt; Heartbeat.
              Critical findings generate urgent notices automatically.
            </div>
          </div>
        </>
      )}
    </HoloPanel>
  )
}
