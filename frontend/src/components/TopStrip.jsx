import { useState, useRef, useCallback } from 'react'

const STATE_LABELS = {
  idle:      ['STANDBY', 'all systems nominal'],
  thinking:  ['DECOMPOSING', 'planning sub-tasks'],
  speaking:  ['RESPONDING', 'speaking'],
  busy:      ['EXECUTING', 'agents active'],
  alert:     ['AWAITING AUTH', 'action required'],
  complete:  ['COMPLETE', 'objective met'],
}

export function TopStrip({ state, cost, noticeCount, connected, input, setInput, onSend }) {
  const [ringLabel, ringSub] = STATE_LABELS[state] || STATE_LABELS.idle

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  return (
    <div className="top-strip">
      <div className="top-strip-logo">
        <div className="top-strip-dot" />
        <div className="top-strip-name">DELA</div>
        <div className="top-strip-ring">// {ringLabel}</div>
      </div>

      {state !== 'idle' && (
        <div className="top-strip-center">
          <div className="top-strip-input-wrap">
            <span className="top-strip-prompt">&gt;</span>
            <input
              className="top-strip-input"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Issue a new directive..."
            />
            <button type="button" className="run-btn" onClick={onSend}>RUN</button>
          </div>
        </div>
      )}

      <div className="top-strip-stats">
        {!connected && (
          <span style={{ color: 'var(--amber)', fontSize: 10, letterSpacing: '0.1em' }}>
            RECONNECTING
          </span>
        )}
        {noticeCount > 0 && (
          <div className="stat-block">
            <div className="stat-value accent">{noticeCount}</div>
            <div className="stat-label">NOTICES</div>
          </div>
        )}
        <div className="stat-block">
          <div className="stat-value" style={{ fontSize: 13 }}>{cost}</div>
          <div className="stat-label">COST</div>
        </div>
      </div>
    </div>
  )
}
