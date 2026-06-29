import { useState, useEffect } from 'react'
import { HoloPanel } from '../HoloPanel'

export function SecurityPanel({ onClose, message }) {
  const [report, setReport]   = useState(null)
  const [scanning, setScanning] = useState(false)
  const [loading, setLoading]   = useState(true)
  const [tab, setTab]           = useState('findings')
  const [kb, setKb]             = useState(null)
  const [kbLoading, setKbLoading] = useState(false)
  const [kbRefreshing, setKbRefreshing] = useState(false)

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

  const fetchKb = () => {
    setKbLoading(true)
    fetch('/api/vuln-kb')
      .then(r => r.json())
      .then(data => { setKb(data); setKbLoading(false) })
      .catch(() => setKbLoading(false))
  }

  const refreshKb = () => {
    setKbRefreshing(true)
    fetch('/api/vuln-kb/refresh', { method: 'POST' })
      .then(r => r.json())
      .then(() => { fetchKb(); setKbRefreshing(false) })
      .catch(() => setKbRefreshing(false))
  }

  useEffect(() => { refresh() }, [])
  useEffect(() => { if (tab === 'checklist' && !kb) fetchKb() }, [tab, kb])

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

  // Map KB items to scan findings by check_id match
  const kbFindings = report?.findings?.filter(f => f.category === 'vuln_kb') || []
  const findingForKbItem = (item) => kbFindings.find(f => f.title?.includes(item.id) || f.title?.includes(item.title))

  const owaspItems = kb?.items?.filter(i => i.id.startsWith('LLM')) || []
  const cweItems   = kb?.items?.filter(i => i.id.startsWith('CWE')) || []

  return (
    <HoloPanel title="Security Audit" message={message} onClose={onClose}>
      {loading && <p className="panel-empty">Loading...</p>}

      {!loading && report && (
        <>
          {/* Tab switcher */}
          <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
            <button
              className="data-btn"
              onClick={() => setTab('findings')}
              style={tab === 'findings' ? { borderColor: 'var(--accent)', color: 'var(--accent)' } : {}}
            >
              FINDINGS ({report.summary.total})
            </button>
            <button
              className="data-btn"
              onClick={() => setTab('checklist')}
              style={tab === 'checklist' ? { borderColor: 'var(--accent)', color: 'var(--accent)' } : {}}
            >
              CHECKLIST ({kb?.item_count || '—'})
            </button>
          </div>

          {tab === 'findings' && (
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

          {tab === 'checklist' && (
            <>
              {/* KB header */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12, padding: 12, borderRadius: 10, background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)' }}>
                <div>
                  <div style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)', fontFamily: "'JetBrains Mono', monospace" }}>
                    VULNERABILITY KNOWLEDGE BASE
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 4 }}>
                    {kb?.item_count || 0} checks from OWASP LLM Top 10 2025 + CWE Top 25 2025
                  </div>
                  {kb?.cached && (
                    <div style={{ fontSize: 9, color: 'var(--text-dim)', marginTop: 2 }}>
                      Cached locally {kb.fetched_at ? new Date(kb.fetched_at * 1000).toLocaleString() : ''}
                    </div>
                  )}
                </div>
                <button
                  className="icon-btn"
                  onClick={refreshKb}
                  disabled={kbRefreshing}
                  style={{ borderColor: 'var(--accent)', color: 'var(--accent)', padding: '6px 12px', fontSize: 9 }}
                >
                  {kbRefreshing ? 'SYNCING...' : 'SYNC'}
                </button>
              </div>

              {kbLoading && <p className="panel-empty">Loading checklist...</p>}

              {!kbLoading && kb && (
                <>
                  {/* OWASP LLM Top 10 */}
                  {owaspItems.length > 0 && (
                    <>
                      <div style={{ fontSize: 9, letterSpacing: '0.15em', color: 'var(--accent)', marginBottom: 6, marginTop: 12, fontFamily: "'JetBrains Mono', monospace" }}>
                        OWASP TOP 10 FOR LLM APPLICATIONS 2025
                      </div>
                      {owaspItems.map(item => {
                        const finding = findingForKbItem(item)
                        const status = finding?.severity || 'pending'
                        return (
                          <div key={item.id} className="panel-item" style={{ borderLeft: `3px solid ${sevColor(status)}` }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                              <span className="panel-item-title" style={{ fontSize: 12 }}>
                                <span style={{ color: 'var(--accent)', marginRight: 6 }}>{item.id}</span>
                                {item.title}
                              </span>
                              <span className={`badge ${sevBadge(status)}`}>{status}</span>
                            </div>
                            <div style={{ fontSize: 10, color: 'var(--text-3)', lineHeight: 1.4, marginBottom: 4 }}>
                              {item.description}
                            </div>
                            <div style={{ fontSize: 9, color: 'var(--text-dim)' }}>
                              <span style={{ color: 'var(--green)' }}>Fix:</span> {item.remediation}
                            </div>
                          </div>
                        )
                      })}
                    </>
                  )}

                  {/* CWE Top 25 */}
                  {cweItems.length > 0 && (
                    <>
                      <div style={{ fontSize: 9, letterSpacing: '0.15em', color: 'var(--accent)', marginBottom: 6, marginTop: 16, fontFamily: "'JetBrains Mono', monospace" }}>
                        CWE TOP 25 MOST DANGEROUS WEAKNESSES 2025
                      </div>
                      {cweItems.map(item => {
                        const finding = findingForKbItem(item)
                        const status = finding?.severity || 'pending'
                        return (
                          <div key={item.id} className="panel-item" style={{ borderLeft: `3px solid ${sevColor(status)}` }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                              <span className="panel-item-title" style={{ fontSize: 12 }}>
                                <span style={{ color: 'var(--accent)', marginRight: 6 }}>{item.id}</span>
                                {item.title}
                              </span>
                              <span className={`badge ${sevBadge(status)}`}>{status}</span>
                            </div>
                            <div style={{ fontSize: 10, color: 'var(--text-3)', lineHeight: 1.4, marginBottom: 4 }}>
                              {item.description}
                            </div>
                            <div style={{ fontSize: 9, color: 'var(--text-dim)' }}>
                              <span style={{ color: 'var(--green)' }}>Fix:</span> {item.remediation}
                            </div>
                          </div>
                        )
                      })}
                    </>
                  )}

                  {/* Whitelisted domains info */}
                  <div style={{ marginTop: 16, padding: 12, borderRadius: 10, background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)', marginBottom: 6, fontFamily: "'JetBrains Mono', monospace" }}>
                      SECURE FETCH WHITELIST
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text-3)', lineHeight: 1.6 }}>
                      {(kb.whitelisted_domains || []).map(d => (
                        <div key={d} style={{ color: 'var(--green)' }}>https://{d}</div>
                      ))}
                    </div>
                    <div style={{ fontSize: 9, color: 'var(--text-dim)', marginTop: 8 }}>
                      Only these domains are contacted during KB refresh. All fetches use HTTPS.
                    </div>
                  </div>
                </>
              )}
            </>
          )}
        </>
      )}
    </HoloPanel>
  )
}
