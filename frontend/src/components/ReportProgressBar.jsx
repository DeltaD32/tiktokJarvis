import { useState, useEffect } from 'react'

const STAGE_LABELS = {
  acknowledging: 'Starting evaluation...',
  dispatching: 'Dispatching sub-agents...',
  researching: 'Agents researching...',
  synthesizing: 'Synthesizing report...',
  complete: 'Report complete — opening panel...',
}

export function ReportProgressBar({ featureProgress }) {
  const [visible, setVisible] = useState(false)
  const [progress, setProgress] = useState(0)
  const [stage, setStage] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!featureProgress) return
    setVisible(true)
    setProgress(featureProgress.progress || 0)
    setStage(featureProgress.stage || '')
    setMessage(featureProgress.message || '')

    if (featureProgress.stage === 'complete') {
      setTimeout(() => setVisible(false), 2500)
    }
  }, [featureProgress])

  if (!visible) return null

  const label = message || STAGE_LABELS[stage] || stage
  const isComplete = stage === 'complete'

  return (
    <div style={{
      position: 'fixed',
      bottom: 120,
      left: '50%',
      transform: 'translateX(-50%)',
      zIndex: 30,
      background: 'rgba(5,6,10,0.95)',
      border: `1px solid ${isComplete ? 'rgba(70,242,176,0.4)' : 'var(--accent)'}`,
      borderRadius: 12,
      padding: '16px 24px',
      minWidth: 360,
      backdropFilter: 'blur(12px)',
      animation: 'subagent-in 0.35s ease',
      boxShadow: isComplete
        ? '0 0 20px rgba(70,242,176,0.1)'
        : `0 0 12px rgba(var(--accent-rgb), 0.08)`,
    }}>
      <div style={{
        fontSize: 11,
        fontFamily: "'JetBrains Mono', monospace",
        color: isComplete ? 'var(--green)' : 'var(--text-2)',
        marginBottom: 10,
        letterSpacing: '0.03em',
        textAlign: 'center',
      }}>
        {label}
      </div>
      <div style={{
        height: 4,
        background: 'rgba(255,255,255,0.08)',
        borderRadius: 2,
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${Math.round(progress)}%`,
          background: isComplete ? 'var(--green)' : 'var(--accent)',
          borderRadius: 2,
          transition: 'width 0.6s cubic-bezier(0.22, 1, 0.36, 1)',
          boxShadow: isComplete ? '0 0 12px var(--green)' : '0 0 8px var(--accent)',
        }} />
      </div>
      <div style={{
        fontSize: 9,
        fontFamily: "'JetBrains Mono', monospace",
        color: isComplete ? 'var(--green)' : 'var(--text-dim)',
        textAlign: 'right',
        marginTop: 4,
      }}>
        {Math.round(progress)}%
      </div>
    </div>
  )
}
