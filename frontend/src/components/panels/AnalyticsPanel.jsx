import { useState, useEffect } from 'react'
import { HoloPanel } from '../HoloPanel'

export function AnalyticsPanel({ onClose, message }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const refresh = () => {
    fetch('/api/analytics')
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 5000)
    return () => clearInterval(interval)
  }, [])

  const fmtNum = (n) => n?.toLocaleString() ?? '0'

  return (
    <HoloPanel title="ANALYTICS" subtitle="USAGE DASHBOARD" onClose={onClose} message={message} width={520}>
      {loading && <p className="panel-empty">Loading...</p>}
      {!loading && data && (
        <>
          {/* Top metrics */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
            <div className="analytics-card">
              <div className="analytics-label">MODEL CALLS</div>
              <div className="analytics-value" style={{ color: 'var(--accent)' }}>{fmtNum(data.model_calls)}</div>
            </div>
            <div className="analytics-card">
              <div className="analytics-label">EST. COST</div>
              <div className="analytics-value" style={{ color: 'var(--green)' }}>
                ${data.estimated_cost_usd?.toFixed(4)}
              </div>
            </div>
            <div className="analytics-card">
              <div className="analytics-label">TOOL CALLS</div>
              <div className="analytics-value" style={{ color: 'var(--amber)' }}>{fmtNum(data.tool_calls)}</div>
            </div>
            <div className="analytics-card">
              <div className="analytics-label">GATE DECISIONS</div>
              <div className="analytics-value" style={{ fontSize: 18 }}>
                <span style={{ color: 'var(--green)' }}>{data.gate_granted}</span>
                <span style={{ color: 'var(--text-dim)', fontSize: 12 }}> granted · </span>
                <span style={{ color: 'var(--red)' }}>{data.gate_denied}</span>
                <span style={{ color: 'var(--text-dim)', fontSize: 12 }}> denied</span>
              </div>
            </div>
          </div>

          {/* Tool usage breakdown */}
          {Object.keys(data.tool_breakdown || {}).length > 0 && (
            <>
              <div style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)', marginBottom: 10, fontFamily: "'JetBrains Mono', monospace" }}>
                TOOL USAGE BREAKDOWN
              </div>
              <div style={{ marginBottom: 16 }}>
                {Object.entries(data.tool_breakdown).map(([name, count]) => {
                  const max = Math.max(...Object.values(data.tool_breakdown))
                  const pct = max > 0 ? (count / max) * 100 : 0
                  return (
                    <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <div style={{ width: 140, font: "500 11px 'JetBrains Mono', monospace", color: 'var(--text-2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {name}
                      </div>
                      <div style={{ flex: 1, height: 8, borderRadius: 4, background: 'rgba(255,255,255,0.04)', overflow: 'hidden' }}>
                        <div style={{ width: `${pct}%`, height: '100%', borderRadius: 4, background: 'var(--amber)', transition: 'width 0.5s ease' }} />
                      </div>
                      <div style={{ width: 28, textAlign: 'right', font: "600 11px 'JetBrains Mono', monospace", color: 'var(--text-3)' }}>
                        {count}
                      </div>
                    </div>
                  )
                })}
              </div>
            </>
          )}

          {/* Other stats */}
          <div style={{ display: 'flex', gap: 16, marginBottom: 16, flexWrap: 'wrap' }}>
            <div className="analytics-mini">
              <span style={{ color: 'var(--text-dim)' }}>Heartbeat notices:</span>{' '}
              <span style={{ color: 'var(--text-2)' }}>{data.heartbeat_notices}</span>
            </div>
            <div className="analytics-mini">
              <span style={{ color: 'var(--text-dim)' }}>Kill switch events:</span>{' '}
              <span style={{ color: 'var(--text-2)' }}>{data.kill_switch_events}</span>
            </div>
          </div>

          {/* Recent activity */}
          {data.recent_events && data.recent_events.length > 0 && (
            <>
              <div style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)', marginBottom: 8, fontFamily: "'JetBrains Mono', monospace" }}>
                RECENT ACTIVITY
              </div>
              <div style={{ maxHeight: 200, overflowY: 'auto', borderRadius: 8, border: '1px solid var(--border)', background: 'rgba(0,0,0,0.2)' }}>
                {data.recent_events.slice(-15).reverse().map((ev, i) => {
                  const colors = {
                    tool: 'var(--amber)',
                    model: 'var(--accent)',
                    gate: ev.verdict === 'granted' ? 'var(--green)' : 'var(--red)',
                    heartbeat: 'var(--text-3)',
                    kill_switch: 'var(--red)',
                  }
                  const labels = {
                    tool: `TOOL: ${ev.name || '?'}`,
                    model: 'MODEL call',
                    gate: `GATE ${ev.verdict}`,
                    heartbeat: 'HEARTBEAT',
                    kill_switch: 'KILL_SWITCH',
                  }
                  return (
                    <div key={i} style={{ display: 'flex', gap: 8, padding: '4px 10px', borderBottom: i < 14 ? '1px solid rgba(255,255,255,0.03)' : 'none' }}>
                      <span style={{ font: "500 9px 'JetBrains Mono', monospace", color: 'var(--text-dim)', flexShrink: 0 }}>
                        {ev.ts?.split(' ')[1] || ''}
                      </span>
                      <span style={{ font: "500 11px 'JetBrains Mono', monospace", color: colors[ev.type] || 'var(--text-3)' }}>
                        {labels[ev.type] || ev.type}
                      </span>
                    </div>
                  )
                })}
              </div>
            </>
          )}

          {data.tool_calls === 0 && data.model_calls === 0 && (
            <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-dim)', fontSize: 12 }}>
              No activity yet. Send a message to Dela to start generating analytics.
            </div>
          )}
        </>
      )}
    </HoloPanel>
  )
}
