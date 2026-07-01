import { useState, useEffect, useCallback } from 'react'
import { HoloPanel } from '../HoloPanel'
import { useAuth } from '../../contexts/AuthContext'

function KpiCard({ label, value, sub, color, icon }) {
  return (
    <div style={{
      padding: '8px 10px', borderRadius: 8,
      background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)',
      minWidth: 80, flex: 1,
    }}>
      <div style={{ fontSize: 8, letterSpacing: '0.1em', color: 'var(--text-dim)', marginBottom: 3, fontFamily: "'JetBrains Mono', monospace" }}>
        {icon} {label}
      </div>
      <div style={{ fontSize: 16, fontWeight: 700, color: color || 'var(--text)', fontFamily: "'JetBrains Mono', monospace" }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 8, color: 'var(--text-dim)', marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

function BarRow({ name, count, max, color }) {
  const pct = max > 0 ? (count / max) * 100 : 0
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
      <div style={{ width: 130, fontSize: 10, fontFamily: "'JetBrains Mono', monospace", color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {name}
      </div>
      <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.04)', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', borderRadius: 3, background: color || 'var(--amber)', transition: 'width 0.5s ease' }} />
      </div>
      <div style={{ width: 24, textAlign: 'right', fontSize: 10, fontFamily: "'JetBrains Mono', monospace", color: 'var(--text-dim)' }}>
        {count}
      </div>
    </div>
  )
}

export function AnalyticsPanel({ onClose, message }) {
  const { token } = useAuth()
  const [data, setData] = useState(null)
  const [extras, setExtras] = useState({})
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(false)
  const [elapsed, setElapsed] = useState(0)

  const refresh = useCallback(() => {
    Promise.all([
      fetch('/api/analytics', { headers: token ? { 'Authorization': `Bearer ${token}` } : {} }).then(r => r.json()),
      fetch('/api/agents', { headers: token ? { 'Authorization': `Bearer ${token}` } : {} }).then(r => r.json()).catch(() => []),
      fetch('/api/memory', { headers: token ? { 'Authorization': `Bearer ${token}` } : {} }).then(r => r.json()).catch(() => []),
      fetch('/api/state', { headers: token ? { 'Authorization': `Bearer ${token}` } : {} }).then(r => r.json()).catch(() => []),
      fetch('/api/workflows', { headers: token ? { 'Authorization': `Bearer ${token}` } : {} }).then(r => r.json()).catch(() => []),
    ])
      .then(([analytics, agents, memory, state, workflows]) => {
        setData(analytics)
        setExtras({
          agents: Array.isArray(agents) ? agents : [],
          memoryFacts: Array.isArray(memory) ? memory : [],
          stateTypes: Array.isArray(state) ? state : [],
          workflows: Array.isArray(workflows) ? workflows : [],
        })
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 5000)
    const tick = setInterval(() => setElapsed(prev => prev + 1), 1000)
    return () => { clearInterval(interval); clearInterval(tick) }
  }, [refresh])

  const fmtNum = (n) => n?.toLocaleString() ?? '0'
  const elapsedStr = `${Math.floor(elapsed / 3600)}h ${Math.floor((elapsed % 3600) / 60)}m ${elapsed % 60}s`

  const agentReady = extras.agents?.filter(a => a.status === 'ready').length || 0
  const agentTotal = extras.agents?.length || 0
  const noticeTypes = extras.stateTypes?.filter(t => t.type === 'notices')?.[0]?.items || 0

  return (
    <HoloPanel title={expanded ? 'Full Dashboard' : 'Analytics'} subtitle={!expanded ? 'COMPACT VIEW' : undefined} onClose={onClose} message={message} width={expanded ? 680 : 520}>
      {loading && <p className="panel-empty">Loading...</p>}

      {!loading && data && (
        <>
          {/* ── COMPACT KPI ROW ── */}
          <div style={{ display: 'flex', gap: 6, marginBottom: expanded ? 12 : 6, flexWrap: 'wrap' }}>
            <KpiCard label="MODEL CALLS" value={fmtNum(data.model_calls)} color="var(--accent)" icon="▶" />
            <KpiCard label="COST" value={`$${data.estimated_cost_usd?.toFixed(4)}`} color="var(--green)" icon="$" />
            <KpiCard label="TOOLS" value={fmtNum(data.tool_calls)} color="var(--amber)" icon="⚡" />
            <KpiCard label="AGENTS" value={`${agentReady}/${agentTotal}`} color="var(--cyan)" icon="🤖"
              sub={agentReady === agentTotal ? 'all ready' : `${agentTotal - agentReady} busy`} />
            <KpiCard label="MEMORY" value={fmtNum(extras.memoryFacts?.length || 0)} color="var(--text)" icon="🧠" sub="facts stored" />
            <KpiCard label="UPTIME" value={elapsedStr} color="var(--text-dim)" icon="⏱" />
          </div>

          {/* Gate decisions — inline */}
          <div style={{ display: 'flex', gap: 10, marginBottom: 8, fontSize: 10, color: 'var(--text-dim)' }}>
            <span>🔒 Gates: <span style={{ color: 'var(--green)' }}>{data.gate_granted} granted</span> · <span style={{ color: 'var(--red)' }}>{data.gate_denied} denied</span></span>
            <span>💓 HB: {data.heartbeat_notices}</span>
            <span>⚠️ Kill: {data.kill_switch_events}</span>
            <span>🔔 Notices: {noticeTypes}</span>
          </div>

          {/* Expand toggle */}
          <button className="chip" onClick={() => setExpanded(!expanded)}
            style={{ fontSize: 9, marginBottom: 8, borderColor: 'var(--accent)', color: 'var(--accent)' }}>
            {expanded ? '▲ Compact View' : '▼ View Full Dashboard'}
          </button>

          {/* ── FULL DASHBOARD ── */}
          {expanded && (
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12 }}>
              {/* Tool breakdown */}
              {Object.keys(data.tool_breakdown || {}).length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 9, letterSpacing: '0.12em', color: 'var(--amber)', marginBottom: 8, fontFamily: "'JetBrains Mono', monospace" }}>
                    TOOL USAGE BREAKDOWN
                  </div>
                  {Object.entries(data.tool_breakdown).sort((a, b) => b[1] - a[1]).map(([name, count]) => (
                    <BarRow key={name} name={name} count={count}
                      max={Math.max(...Object.values(data.tool_breakdown))} color="var(--amber)" />
                  ))}
                </div>
              )}

              {/* Agent status grid */}
              {extras.agents?.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 9, letterSpacing: '0.12em', color: 'var(--cyan)', marginBottom: 8, fontFamily: "'JetBrains Mono', monospace" }}>
                    AGENT STATUS
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                    {extras.agents.map(a => (
                      <div key={a.name} style={{
                        padding: '4px 8px', borderRadius: 4, fontSize: 9,
                        background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)',
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      }}>
                        <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>{a.name}</span>
                        <span style={{
                          width: 6, height: 6, borderRadius: '50%', display: 'inline-block',
                          background: a.status === 'ready' ? 'var(--green)' : a.status === 'busy' ? 'var(--amber)' : 'var(--red)',
                        }} />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Memory summary */}
              {extras.memoryFacts?.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 9, letterSpacing: '0.12em', color: 'var(--text-dim)', marginBottom: 6, fontFamily: "'JetBrains Mono', monospace" }}>
                    MEMORY BY CATEGORY
                  </div>
                  {(() => {
                    const cats = {}
                    extras.memoryFacts.forEach(f => { cats[f.category] = (cats[f.category] || 0) + 1 })
                    const maxCat = Math.max(...Object.values(cats), 1)
                    return Object.entries(cats).map(([cat, count]) => (
                      <BarRow key={cat} name={cat} count={count} max={maxCat} color="var(--green)" />
                    ))
                  })()}
                </div>
              )}

              {/* Workflows */}
              {extras.workflows?.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 9, letterSpacing: '0.12em', color: 'var(--accent)', marginBottom: 6, fontFamily: "'JetBrains Mono', monospace" }}>
                    WORKFLOWS ({extras.workflows.length})
                  </div>
                  {extras.workflows.map(wf => (
                    <div key={wf.name} style={{ fontSize: 10, padding: '2px 0', display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>{wf.name}</span>
                      <span style={{ color: 'var(--text-dim)', fontSize: 9 }}>{wf.steps} steps</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Recent activity log */}
              {data.recent_events?.length > 0 && (
                <div>
                  <div style={{ fontSize: 9, letterSpacing: '0.12em', color: 'var(--text-dim)', marginBottom: 6, fontFamily: "'JetBrains Mono', monospace" }}>
                    RECENT ACTIVITY ({Math.min(data.recent_events.length, 30)})
                  </div>
                  <div style={{ maxHeight: 250, overflow: 'auto', borderRadius: 6, border: '1px solid var(--border)', background: 'rgba(0,0,0,0.2)' }}>
                    {data.recent_events.slice(-30).reverse().map((ev, i) => {
                      const colors = { tool: 'var(--amber)', model: 'var(--accent)', gate: ev.verdict === 'granted' ? 'var(--green)' : 'var(--red)', heartbeat: 'var(--text-dim)', kill_switch: 'var(--red)' }
                      const labels = { tool: `TOOL: ${ev.name || '?'}`, model: 'MODEL call', gate: `GATE ${ev.verdict}`, heartbeat: 'HEARTBEAT', kill_switch: 'KILL SWITCH' }
                      return (
                        <div key={i} style={{ display: 'flex', gap: 8, padding: '2px 8px', borderBottom: i < 29 ? '1px solid rgba(255,255,255,0.02)' : 'none' }}>
                          <span style={{ fontSize: 8, fontFamily: "'JetBrains Mono', monospace", color: 'var(--text-dim)', flexShrink: 0 }}>{ev.ts?.split(' ')[1] || ''}</span>
                          <span style={{ fontSize: 9, fontFamily: "'JetBrains Mono', monospace", color: colors[ev.type] || 'var(--text-dim)' }}>{labels[ev.type] || ev.type}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Empty state */}
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
