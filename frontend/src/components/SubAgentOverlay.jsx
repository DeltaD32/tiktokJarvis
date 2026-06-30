import { useState, useEffect } from 'react'
import { getVoiceAmplitude } from '../hooks/useVoiceTTS'

const AGENT_COLORS = {
  researcher: 'var(--cyan)',
  presenter: 'var(--green)',
  secretary: 'var(--amber)',
  workflow_designer: 'var(--accent)',
  system_expert: 'var(--red)',
}

export function SubAgentOverlay({ agentStatus, toolStatus, orbState }) {
  const [visible, setVisible] = useState(false)
  const [activeAgent, setActiveAgent] = useState(null)
  const [activityLog, setActivityLog] = useState([])
  const [fadeOut, setFadeOut] = useState(false)

  // Detect busy agents
  useEffect(() => {
    const busy = Object.entries(agentStatus || {}).find(([, s]) => s.state === 'busy')
    if (busy) {
      const [name, status] = busy
      setActiveAgent({ name, task: status.task || 'Working...' })
      setVisible(true)
      setFadeOut(false)
    } else if (activeAgent && !fadeOut) {
      // Agent finished — fade out after a moment
      setFadeOut(true)
      const timer = setTimeout(() => {
        setVisible(false)
        setActiveAgent(null)
        setActivityLog([])
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [agentStatus])

  // Track tool blips as activity
  useEffect(() => {
    if (toolStatus && visible) {
      setActivityLog(prev => {
        const entry = { text: toolStatus, time: Date.now() }
        const next = [...prev, entry]
        return next.slice(-8) // keep last 8 entries
      })
    }
  }, [toolStatus])

  if (!visible || !activeAgent) return null

  const color = AGENT_COLORS[activeAgent.name] || 'var(--accent)'

  return (
    <div style={{
      position: 'fixed',
      bottom: 120,
      left: '50%',
      transform: 'translateX(-50%)',
      zIndex: 20,
      opacity: fadeOut ? 0 : 1,
      transition: 'opacity 0.5s ease',
      pointerEvents: 'none',
    }}>
      <div style={{
        background: 'rgba(5,6,10,0.95)',
        border: `1px solid ${color}44`,
        borderRadius: 12,
        padding: '12px 16px',
        minWidth: 320,
        maxWidth: 500,
        backdropFilter: 'blur(12px)',
        boxShadow: `0 0 30px ${color}11`,
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: activityLog.length > 0 ? 8 : 0 }}>
          <span style={{
            width: 8, height: 8, borderRadius: '50%', background: color,
            boxShadow: `0 0 8px ${color}`, flexShrink: 0,
            animation: 'jpulse 1.5s ease-in-out infinite',
          }} />
          <span style={{
            fontSize: 10, fontFamily: "'JetBrains Mono', monospace", color,
            letterSpacing: '0.08em', fontWeight: 600,
          }}>
            {activeAgent.name.toUpperCase()}
          </span>
          <span style={{ fontSize: 9, color: 'var(--text-dim)', flex: 1, textAlign: 'right' }}>
            working...
          </span>
        </div>

        {/* Task */}
        <div style={{ fontSize: 11, color: 'var(--text)', lineHeight: 1.4, marginBottom: activityLog.length > 0 ? 6 : 0 }}>
          {activeAgent.task.length > 120 ? activeAgent.task.slice(0, 120) + '…' : activeAgent.task}
        </div>

        {/* Activity log */}
        {activityLog.length > 0 && (
          <div style={{
            maxHeight: 120,
            overflow: 'auto',
            borderTop: '1px solid var(--border)',
            paddingTop: 6,
          }}>
            {activityLog.map((entry, i) => (
              <div key={i} style={{
                fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
                color: i === activityLog.length - 1 ? 'var(--amber)' : 'var(--text-dim)',
                padding: '1px 0',
                opacity: i < activityLog.length - 3 ? 0.4 : 1,
              }}>
                {entry.text.length > 80 ? entry.text.slice(0, 80) + '…' : entry.text}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
