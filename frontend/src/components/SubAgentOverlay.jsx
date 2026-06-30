import { useState, useEffect, useRef } from 'react'

const AGENT_COLORS = {
  researcher: 'var(--cyan)',
  presenter: 'var(--green)',
  secretary: 'var(--amber)',
  workflow_designer: 'var(--accent)',
  system_expert: 'var(--red)',
}

const ANIM_STYLE = `
@keyframes subagent-in {
  from { opacity: 0; transform: translateY(16px) scale(0.96); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes subagent-out {
  from { opacity: 1; transform: translateY(0) scale(1); }
  to   { opacity: 0; transform: translateY(8px) scale(0.97); }
}
`

function AgentPanel({ agent, color, activityLog, expanded, onToggleExpand, onDismiss, defaultPos }) {
  const panelRef = useRef(null)
  const dragRef = useRef({ dragging: false, startX: 0, startY: 0, posX: 0, posY: 0 })
  const [pos, setPos] = useState(defaultPos || { x: 50, y: 50 })
  const [closing, setClosing] = useState(false)

  const handleDismiss = () => {
    setClosing(true)
    setTimeout(() => onDismiss(agent.name), 300)
  }

  const onMouseDown = (e) => {
    if (e.target.tagName === 'BUTTON') return // don't drag on buttons
    dragRef.current = {
      dragging: true,
      startX: e.clientX - pos.x,
      startY: e.clientY - pos.y,
      posX: pos.x,
      posY: pos.y,
    }
    e.preventDefault()
  }

  useEffect(() => {
    const onMove = (e) => {
      if (!dragRef.current.dragging) return
      setPos({
        x: Math.max(0, Math.min(window.innerWidth - 340, e.clientX - dragRef.current.startX)),
        y: Math.max(0, Math.min(window.innerHeight - 300, e.clientY - dragRef.current.startY)),
      })
    }
    const onUp = () => { dragRef.current.dragging = false }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [])

  return (
    <div style={{
      position: 'fixed',
      left: pos.x,
      top: pos.y,
      zIndex: 25,
      animation: closing ? 'subagent-out 0.3s ease forwards' : 'subagent-in 0.35s ease',
      pointerEvents: 'auto',
    }}>
      <style>{ANIM_STYLE}</style>
      <div style={{
        background: 'rgba(5,6,10,0.97)',
        border: `1px solid ${color}33`,
        borderRadius: 12,
        width: 320,
        backdropFilter: 'blur(16px)',
        boxShadow: `0 4px 24px ${color}11, 0 0 1px ${color}22`,
        overflow: 'hidden',
      }}>
        {/* Header — draggable */}
        <div
          onMouseDown={onMouseDown}
          style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
            cursor: 'grab', borderBottom: '1px solid var(--border)',
            background: `${color}08`,
          }}>
          <span style={{
            width: 7, height: 7, borderRadius: '50%', background: color,
            boxShadow: `0 0 8px ${color}`, flexShrink: 0,
            animation: 'jpulse 1.5s ease-in-out infinite',
          }} />
          <span style={{
            fontSize: 9, fontFamily: "'JetBrains Mono', monospace", color,
            letterSpacing: '0.08em', fontWeight: 600, flex: 1,
          }}>
            {agent.name.toUpperCase()}
          </span>
          <button
            onClick={onToggleExpand}
            style={{
              background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer',
              fontSize: 10, padding: '2px 4px', fontFamily: "'JetBrains Mono', monospace",
            }}
            title={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? '−' : '+'}
          </button>
          <button
            onClick={handleDismiss}
            style={{
              background: 'none', border: 'none', color: 'var(--text-faint)', cursor: 'pointer',
              fontSize: 12, padding: '0 2px',
            }}
            title="Dismiss"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: '8px 12px' }}>
          {/* Task */}
          <div style={{ fontSize: 10, color: 'var(--text)', lineHeight: 1.4, marginBottom: 6 }}>
            {agent.task.length > 100 && !expanded
              ? agent.task.slice(0, 100) + '…'
              : agent.task}
          </div>

          {/* Activity log */}
          <div style={{
            maxHeight: expanded ? 250 : 80,
            overflow: 'auto',
            transition: 'max-height 0.3s ease',
            borderTop: activityLog.length > 0 ? `1px solid ${color}18` : 'none',
            paddingTop: activityLog.length > 0 ? 6 : 0,
          }}>
            {activityLog.map((entry, i) => {
              const isRecent = i >= activityLog.length - 3
              return (
                <div key={i} style={{
                  fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
                  color: isRecent ? 'var(--amber)' : 'var(--text-dim)',
                  padding: '1px 0',
                  opacity: isRecent ? 1 : 0.5,
                  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                }}>
                  {entry.text.length > (expanded ? 100 : 60)
                    ? entry.text.slice(0, expanded ? 100 : 60) + '…'
                    : entry.text}
                </div>
              )
            })}
            {activityLog.length === 0 && (
              <div style={{ fontSize: 9, color: 'var(--text-faint)', fontStyle: 'italic' }}>
                waiting for activity...
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export function SubAgentOverlay({ agentStatus, toolStatus, orbState }) {
  const [panels, setPanels] = useState({})
  const [expanded, setExpanded] = useState({})
  const [activityLogs, setActivityLogs] = useState({})
  const prevBusyRef = useRef({})

  // Track busy agents — create panel when agent becomes busy, remove when ready
  useEffect(() => {
    const current = agentStatus || {}
    const prev = prevBusyRef.current

    // Check for newly busy agents
    for (const [name, status] of Object.entries(current)) {
      if (status.state === 'busy' && prev[name]?.state !== 'busy') {
        // Agent just became busy — create panel
        setPanels(p => ({
          ...p,
          [name]: { name, task: status.task || 'Working...' },
        }))
        setActivityLogs(l => ({ ...l, [name]: [] }))
        // Position panels in a cascade
        const count = Object.keys({ ...panels, [name]: true }).length
        setExpanded(e => ({ ...e, [name]: count === 1 })) // auto-expand if only one
      }
      if (status.state !== 'busy' && prev[name]?.state === 'busy') {
        // Agent finished — schedule removal
        const timer = setTimeout(() => {
          setPanels(p => { const n = { ...p }; delete n[name]; return n })
          setActivityLogs(l => { const n = { ...l }; delete n[name]; return n })
          setExpanded(e => { const n = { ...e }; delete n[name]; return n })
        }, 2500)
        return () => clearTimeout(timer)
      }
    }
    prevBusyRef.current = current
  }, [agentStatus])

  // Route tool blips to the active busy agent
  useEffect(() => {
    if (!toolStatus) return
    const busyNames = Object.entries(agentStatus || {})
      .filter(([, s]) => s.state === 'busy')
      .map(([n]) => n)
    if (busyNames.length === 0) return

    // Add to all busy agents
    setActivityLogs(prev => {
      const next = { ...prev }
      busyNames.forEach(name => {
        const entries = [...(next[name] || []), { text: toolStatus, time: Date.now() }]
        next[name] = entries.slice(-20)
      })
      return next
    })
  }, [toolStatus])

  const toggleExpand = (name) => {
    setExpanded(e => ({ ...e, [name]: !e[name] }))
  }

  const dismissPanel = (name) => {
    setPanels(p => { const n = { ...p }; delete n[name]; return n })
    setActivityLogs(l => { const n = { ...l }; delete n[name]; return n })
    setExpanded(e => { const n = { ...e }; delete n[name]; return n })
  }

  const panelEntries = Object.entries(panels)
  if (panelEntries.length === 0) return null

  return (
    <>
      {panelEntries.map(([name, agent], i) => {
        const color = AGENT_COLORS[name] || 'var(--accent)'
        const log = activityLogs[name] || []
        return (
          <AgentPanel
            key={name}
            agent={agent}
            color={color}
            activityLog={log}
            expanded={!!expanded[name]}
            onToggleExpand={() => toggleExpand(name)}
            onDismiss={dismissPanel}
            defaultPos={{ x: 20 + i * 30, y: window.innerHeight - 380 - i * 40 }}
          />
        )
      })}
    </>
  )
}
