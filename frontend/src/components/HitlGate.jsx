import { useEffect } from 'react'

export function HitlGate({ request, onApprove, onDeny }) {
  useEffect(() => {
    const handler = (e) => {
      if (e.code === 'Space' && request) {
        e.preventDefault()
        onApprove()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [request, onApprove])

  if (!request) return null

  return (
    <div className="hitl-overlay">
      <div className="hitl-box">
        <div className="hitl-header">
          <div className="hitl-dot" />
          <div className="hitl-title">HUMAN-IN-THE-LOOP GATE</div>
        </div>
        <div className="hitl-body">Action requires approval</div>
        <div className="hitl-desc-box">
          <div className="hitl-desc">{request.description}</div>
        </div>
        <div className="hitl-actions">
          <button className="hitl-btn hitl-approve" onClick={onApprove}>APPROVE</button>
          <button className="hitl-btn hitl-deny" onClick={onDeny}>DENY</button>
        </div>
        <div className="hitl-hint">
          press <span className="hitl-key">SPACE</span> to confirm
        </div>
      </div>
    </div>
  )
}
