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
  const [fixingId, setFixingId] = useState(null)
  const [fixResult, setFixResult] = useState(null)

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

  const requestFix = (finding, autoApply = false) => {
    setFixingId(finding.title)
    setFixResult(null)
    fetch('/api/security/fix', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        finding_title: finding.title,
        finding_detail: finding.detail,
        finding_category: finding.category,
        finding_priority: finding.priority,
        auto_apply: autoApply,
      }),
    })
      .then(r => r.json())
      .then(data => { setFixingId(null); setFixResult(data) })
      .catch(() => setFixingId(null))
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

  const priorityColor = (p) => ({
    P0: 'var(--red)',
    P1: 'var(--red)',
    P2: 'var(--amber)',
    P3: 'var(--amber)',
    P4: 'var(--text-dim)',
  })[p] || 'var(--text-dim)'

  const priorityLabel = (p) => ({
    P0: 'CRITICAL',
    P1: 'HIGH',
    P2: 'MEDIUM',
    P3: 'LOW',
    P4: 'INFO',
  })[p] || 'INFO'

  const scoreColor = report?.score >= 90 ? 'var(--green)' : report?.score >= 70 ? 'var(--amber)' : 'var(--red)'

  // Sort findings by priority for display
  const sortedFindings = report?.findings ? [...report.findings].sort((a, b) => {
    const order = { P0: 0, P1: 1, P2: 2, P3: 3, P4: 4 }
    return (order[a.priority] || 5) - (order[b.priority] || 5)
  }) : []

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

              {/* Fix result modal */}
              {fixResult && (
                <div style={{ marginBottom: 12, padding: 14, borderRadius: 10, background: 'rgba(0,0,0,0.4)', border: '1px solid var(--accent)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--accent)', fontFamily: "'JetBrains Mono', monospace" }}>
                      AGENT FIX RECOMMENDATION
                    </span>
                    <button className="data-btn" onClick={() => setFixResult(null)}>CLOSE</button>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-2)', whiteSpace: 'pre-wrap', lineHeight: 1.5, maxHeight: 400, overflow: 'auto' }}>
                    {fixResult.result || fixResult.error || 'No result'}
                  </div>
                </div>
              )}

              {/* Findings — sorted by priority */}
              {sortedFindings.map((f, i) => {
                const isActionable = f.severity === 'critical' || f.severity === 'warning'
                const isFixing = fixingId === f.title
                return (
                  <div key={i} className="panel-item" style={{ borderLeft: `3px solid ${sevColor(f.severity)}` }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span className="panel-item-title" style={{ fontSize: 12 }}>{f.title}</span>
                        <span style={{
                          fontSize: 8,
                          fontWeight: 700,
                          color: priorityColor(f.priority),
                          border: `1px solid ${priorityColor(f.priority)}`,
                          borderRadius: 3,
                          padding: '1px 4px',
                          fontFamily: "'JetBrains Mono', monospace",
                        }}>
                          {f.priority}
                        </span>
                      </div>
                      <span className={`badge ${sevBadge(f.severity)}`}>{f.severity}</span>
                    </div>
                    <div className="panel-item-meta" style={{ fontSize: 10 }}>
                      <span style={{ color: 'var(--text-dim)' }}>[{f.category}]</span>
                      {f.detail && <span style={{ marginLeft: 6 }}>{f.detail}</span>}
                    </div>
                    {isActionable && (
                      <div style={{ marginTop: 6, display: 'flex', gap: 4 }}>
                        <button
                          className="data-btn"
                          onClick={() => requestFix(f, false)}
                          disabled={isFixing}
                          style={isFixing ? { opacity: 0.5 } : { borderColor: 'var(--accent)', color: 'var(--accent)' }}
                        >
                          {isFixing ? 'ANALYZING...' : 'RECOMMEND FIX'}
                        </button>
                        <button
                          className="data-btn"
                          onClick={() => requestFix(f, true)}
                          disabled={isFixing}
                          style={isFixing ? { opacity: 0.5 } : { borderColor: 'var(--amber)', color: 'var(--amber)' }}
                        >
                          AUTO-FIX
                        </button>
                      </div>
                    )}
                  </div>
                )
              })}

              {/* Auto-scan info */}
              <div style={{ marginTop: 16, padding: 12, borderRadius: 10, background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border)' }}>
                <div style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)', marginBottom: 6, fontFamily: "'JetBrains Mono', monospace" }}>
                  AUTO-SCAN + VULN KB REFRESH
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-3)', lineHeight: 1.5 }}>
                  The heartbeat runs a security scan hourly and refreshes the vuln KB checklist
                  from OWASP/CWE/CISA daily. Critical findings generate urgent notices.
                  Findings are prioritized P0-P4 by severity and impact.
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
                      Only these domains are contacted during KB refresh. Auto-refreshed daily by the heartbeat.
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
