import { useState, useEffect, useRef } from 'react'
import { HoloPanel } from '../HoloPanel'
import { useAuth } from '../../contexts/AuthContext'

export function AuditPanel({ onClose, message }) {
  const { token } = useAuth()
  const [log, setLog]   = useState('')
  const [cost, setCost] = useState('')
  const endRef = useRef(null)

  const refresh = () => {
    fetch('/api/audit?n=80', { headers: token ? { 'Authorization': `Bearer ${token}` } : {} })
      .then(r => r.json())
      .then(d => { setLog(d.log ?? ''); setCost(d.cost ?? '') })
      .catch(() => {})
  }

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 5000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView()
  }, [log])

  return (
    <HoloPanel title="Audit Log" message={message} onClose={onClose}>
      {cost && (
        <div style={{ fontSize: 11, color: 'var(--cyan)', marginBottom: 12, letterSpacing: '0.05em' }}>
          {cost}
        </div>
      )}
      <pre className="audit-log">{log || 'No log entries yet.'}</pre>
      <div ref={endRef} />
    </HoloPanel>
  )
}
