import { useState } from 'react'
import { HoloPanel } from '../HoloPanel'
import { useAuth } from '../../contexts/AuthContext'

const PANEL_STYLE = `
  .report-panel { padding: 16px 20px 24px; max-height: calc(100vh - 260px); overflow: auto; font-family: 'Inter', -apple-system, sans-serif; color: var(--text-2); font-size: 12px; line-height: 1.7; }
  .report-panel h1 { font-size: 15px; font-weight: 700; color: var(--accent); font-family: 'JetBrains Mono', monospace; letter-spacing: 0.03em; margin: 0 0 8px; }
  .report-panel h2 { font-size: 13px; font-weight: 700; color: var(--text); font-family: 'JetBrains Mono', monospace; letter-spacing: 0.02em; margin: 20px 0 8px; padding-bottom: 4px; border-bottom: 1px solid var(--border); }
  .report-panel h3 { font-size: 11px; font-weight: 600; color: var(--text); margin: 14px 0 6px; }
  .report-panel p { margin: 0 0 8px; }
  .report-panel ul, .report-panel ol { margin: 4px 0 10px; padding-left: 20px; }
  .report-panel li { margin-bottom: 3px; }
  .report-panel strong { color: var(--text); }
  .report-panel code { background: rgba(0,0,0,0.3); padding: 1px 5px; border-radius: 3px; font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--accent); }
  .report-panel hr { border: none; border-top: 1px solid var(--border); margin: 14px 0; }
  .report-panel .verdict { padding: 12px 16px; border-radius: 6px; margin: 12px 0; font-size: 13px; font-weight: 700; text-align: center; letter-spacing: 0.05em; font-family: 'JetBrains Mono', monospace; }
  .report-panel .verdict.recommended { background: rgba(70,242,176,0.1); border: 1px solid rgba(70,242,176,0.3); color: var(--green); }
  .report-panel .verdict.conditional { background: rgba(255,179,0,0.1); border: 1px solid rgba(255,179,0,0.3); color: var(--amber); }
  .report-panel .verdict.rejected { background: rgba(255,90,69,0.1); border: 1px solid rgba(255,90,69,0.3); color: var(--red); }
  .report-panel table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 11px; }
  .report-panel th { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); color: var(--text-dim); font-family: 'JetBrains Mono', monospace; font-size: 9px; letter-spacing: 0.1em; text-transform: uppercase; }
  .report-panel td { padding: 6px 8px; border-bottom: 1px solid var(--border); }
  .report-panel .score { display: inline-block; min-width: 24px; text-align: center; padding: 2px 6px; border-radius: 3px; font-family: 'JetBrains Mono', monospace; font-size: 11px; }
  .report-panel .score.high { background: rgba(70,242,176,0.15); color: var(--green); }
  .report-panel .score.medium { background: rgba(255,179,0,0.15); color: var(--amber); }
  .report-panel .score.low { background: rgba(255,90,69,0.15); color: var(--red); }
  .report-panel .meta-row { display: flex; gap: 16px; margin: 8px 0 16px; flex-wrap: wrap; }
  .report-panel .meta-item { flex: 1; min-width: 100px; }
  .report-panel .meta-label { font-size: 8px; color: var(--text-dim); letter-spacing: 0.12em; text-transform: uppercase; font-family: 'JetBrains Mono', monospace; margin-bottom: 2px; }
  .report-panel .meta-value { font-size: 12px; color: var(--text); font-weight: 600; }
  .report-panel .empty { color: var(--text-dim); font-size: 12px; font-style: italic; }
  .report-actions { display: flex; gap: 8px; padding: 12px 16px; border-top: 1px solid var(--border); background: rgba(5,6,10,0.9); position: sticky; bottom: 0; }
  .report-btn { flex: 1; padding: 10px; border-radius: 6px; border: 1px solid; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600; letter-spacing: 0.05em; cursor: pointer; transition: all 0.2s; background: transparent; }
  .report-btn:hover:not(:disabled) { transform: translateY(-1px); }
  .report-btn:disabled { opacity: 0.3; cursor: not-allowed; }
  .report-btn.shelve { color: var(--text-dim); border-color: var(--text-dim); }
  .report-btn.shelve:hover:not(:disabled) { background: rgba(255,255,255,0.06); color: var(--text); }
  .report-btn.reject { color: var(--red); border-color: rgba(255,90,69,0.4); }
  .report-btn.reject:hover:not(:disabled) { background: rgba(255,90,69,0.1); }
  .report-btn.accept { color: var(--green); border-color: rgba(70,242,176,0.4); }
  .report-btn.accept:hover:not(:disabled) { background: rgba(70,242,176,0.1); }
  .report-status { font-size: 10px; text-align: center; padding: 6px 16px; font-family: 'JetBrains Mono', monospace; letter-spacing: 0.03em; }
`

export function ReportPanel({ onClose, message, content, title, onSendMessage }) {
  const { token } = useAuth()
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)

  const displayTitle = title || message || 'Report'

  const htmlContent = content || ''
  const hasHtml = htmlContent.includes('<')

  const extractFeatureName = () => {
    const match = displayTitle.match(/^(.+?)\s*[-–—]\s*Impact\s*Analysis/i)
    return match ? match[1].trim() : displayTitle.replace(' — Impact Analysis', '')
  }

  const reportAction = async (action) => {
    setLoading(true)
    setStatus(`${action}ing...`)
    try {
      const featureName = extractFeatureName()
      const res = await fetch('/api/report/action', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          action,
          feature: featureName,
          report: content,
          title: displayTitle,
        }),
      })
      const data = await res.json()
      if (data.ok) {
        const messages = {
          shelve: `📦 "${featureName}" shelved for later — research stored in memory`,
          reject: `❌ "${featureName}" rejected — analysis archived`,
          accept: `✅ "${featureName}" accepted — implementation will begin`,
        }
        setStatus(messages[action] || data.message)
        if (action === 'accept') {
          setTimeout(() => onClose?.(), 1500)
        }
      } else {
        setStatus(`Error: ${data.error || 'unknown'}`)
      }
    } catch {
      setStatus('Network error — try again')
    } finally {
      setLoading(false)
    }
  }

  return (
    <HoloPanel title={displayTitle} onClose={onClose}>
      <style>{PANEL_STYLE}</style>
      {hasHtml ? (
        <div className="report-panel" dangerouslySetInnerHTML={{ __html: htmlContent }} />
      ) : (
        <div className="report-panel">
          {content ? (
            content.split('\n').map((line, i) => <p key={i} style={{ margin: '0 0 4px' }}>{line}</p>)
          ) : (
            <div className="empty">No report content available.</div>
          )}
        </div>
      )}
      {status && <div className="report-status" style={{ color: status.includes('✅') || status.includes('📦') ? 'var(--green)' : status.includes('Error') ? 'var(--red)' : 'var(--amber)' }}>{status}</div>}
      <div className="report-actions">
        <button
          className="report-btn shelve"
          disabled={loading || !!status}
          onClick={() => reportAction('shelve')}
          title="Save research so agents don't re-investigate later"
        >
          📦 SHELVE
        </button>
        <button
          className="report-btn reject"
          disabled={loading || !!status}
          onClick={() => reportAction('reject')}
          title="Reject this feature — store as not viable"
        >
          ❌ REJECT
        </button>
        <button
          className="report-btn accept"
          disabled={loading || !!status}
          onClick={() => reportAction('accept')}
          title="Accept and begin implementation"
        >
          ✅ ACCEPT
        </button>
      </div>
      <div className="report-actions" style={{ borderTop: 'none', paddingTop: 0 }}>
        <button
          className="report-btn reimagine"
          disabled={loading}
            onClick={() => {
              const featureName = extractFeatureName()
              const prompt = `Re-imagine ${featureName} — design a native Python version that fits Dela's architecture. Use evaluate_feature to analyze the feasibility of this native redesign.`
              onSendMessage?.(prompt)
              onClose?.()
            }}
          title="Ask Dela to redesign this feature natively for Dela's architecture"
          style={{
            flex: 1, padding: 10, borderRadius: 6, border: '1px solid var(--purple)',
            fontFamily: "'JetBrains Mono', monospace", fontSize: 10, fontWeight: 600,
            letterSpacing: '0.05em', cursor: 'pointer', background: 'transparent',
            color: 'var(--purple)', transition: 'all 0.2s',
          }}
          onMouseEnter={e => { e.target.style.background = 'rgba(179,136,255,0.1)' }}
          onMouseLeave={e => { e.target.style.background = 'transparent' }}
        >
          💡 RE-IMAGINE
        </button>
      </div>
    </HoloPanel>
  )
}
