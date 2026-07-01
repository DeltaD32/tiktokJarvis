import { useRef, useEffect, useState } from 'react'

const MSG_STYLE = `
.conv-panel { position: fixed; bottom: 72px; right: 24px; z-index: 10; width: 380px; max-height: calc(100vh - 200px); pointer-events: auto; }
.conv-panel.minimized { max-height: 0; overflow: hidden; }
.conv-scroll { max-height: calc(100vh - 260px); overflow-y: auto; padding: 12px 0; scroll-behavior: smooth; }
.conv-scroll::-webkit-scrollbar { width: 3px; }
.conv-scroll::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

.card {
  margin: 4px 12px; padding: 8px 12px; border-radius: 8px; position: relative;
  animation: card-in 0.3s ease; font-size: 11px; line-height: 1.6;
  cursor: pointer; transition: background 0.15s;
}
@keyframes card-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

.card.user { background: rgba(var(--accent-rgb), 0.06); border: 1px solid rgba(var(--accent-rgb), 0.12); margin-left: 48px; text-align: right; }
.card.user:hover { background: rgba(var(--accent-rgb), 0.1); }

.card.assistant { background: rgba(255,255,255,0.03); border: 1px solid var(--border); margin-right: 48px; }
.card.assistant:hover { background: rgba(255,255,255,0.05); }

.card.tool { background: rgba(255,179,0,0.04); border: 1px solid rgba(255,179,0,0.15); margin-right: 48px; }
.card.tool .card-badge { background: rgba(255,179,0,0.15); color: var(--amber); }

.card.report { background: rgba(70,242,176,0.03); border: 1px solid rgba(70,242,176,0.12); margin-right: 48px; }
.card.report .card-badge { background: rgba(70,242,176,0.15); color: var(--green); }

.card-badge {
  display: inline-block; font-size: 8px; font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.08em; padding: 1px 6px; border-radius: 3px; margin-bottom: 4px;
}
.card.user .card-badge { background: rgba(var(--accent-rgb), 0.12); color: var(--accent); }

.card-body { color: var(--text-2); word-break: break-word; }
.card-body.collapsed { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-body.expanded { white-space: pre-wrap; }

.status-chip {
  display: inline-block; font-size: 9px; font-family: 'JetBrains Mono', monospace;
  color: var(--accent); margin-left: 6px; animation: jblink 1s steps(1) infinite;
  vertical-align: middle;
}
.speaking-chip {
  display: inline-block; font-size: 9px; font-family: 'JetBrains Mono', monospace;
  color: var(--green); margin-left: 6px; vertical-align: middle;
  animation: fadeInOut 0.6s ease;
}
@keyframes fadeInOut { from { opacity: 0; } to { opacity: 1; } }

.empty-state { padding: 20px; text-align: center; color: var(--text-faint); font-size: 11px; font-family: 'JetBrains Mono', monospace; }
`

function classifyMessage(msg) {
  if (msg.role === 'user') return 'user'
  const text = msg.content || ''
  if (text.includes('<h1>') || text.includes('Impact Analysis') || text.startsWith('```html'))
    return 'report'
  if (text.trim().startsWith('TOOL[') || text.trim().startsWith('[ran ') || text.trim().startsWith('[error'))
    return 'tool'
  return 'assistant'
}

function badgeLabel(type) {
  return { user: 'YOU', assistant: 'DELA', tool: 'TOOL', report: 'REPORT' }[type] || 'DELA'
}

function MessageCard({ msg, type, defaultExpanded }) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const maxLen = 120
  const text = msg.content || ''
  const collapsed = !expanded && text.length > maxLen
  const short = text.length <= maxLen

  return (
    <div
      className={`card ${type}`}
      onClick={() => setExpanded(e => !e)}
      title={short ? '' : 'Click to expand'}
    >
      <div className="card-badge">{badgeLabel(type)}</div>
      <div className={`card-body ${!expanded && !short ? 'collapsed' : 'expanded'}`}>
        {text}
      </div>
      {collapsed && (
        <div style={{ fontSize: 9, color: 'var(--text-dim)', marginTop: 2 }}>
          ({text.length - maxLen} more chars — click to expand)
        </div>
      )}
    </div>
  )
}

export function ConversationPanel({
  conversation, currentStream, toolStatus, orbState, ttsSpeaking,
  onVoiceToggle, voiceEnabled,
}) {
  const scrollRef = useRef(null)
  const streamingType = classifyMessage({ role: 'assistant', content: currentStream || '' })
  const [lastSpeakTime, setLastSpeakTime] = useState(0)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [conversation, currentStream, toolStatus])

  if (conversation.length === 0 && !currentStream && !toolStatus) {
    return null
  }

  return (
    <div className="conv-panel">
      <style>{MSG_STYLE}</style>
      <div className="conv-scroll" ref={scrollRef}>
        {conversation.map(msg => (
          <MessageCard
            key={msg.id}
            msg={msg}
            type={classifyMessage(msg)}
            defaultExpanded={false}
          />
        ))}
        {currentStream && (
          <div style={{ margin: '4px 12px', padding: '8px 12px' }}>
            <span className="card-badge" style={{
              background: 'rgba(var(--accent-rgb),0.1)', color: 'var(--accent)',
              fontSize: 8, fontFamily: "'JetBrains Mono', monospace",
              letterSpacing: '0.08em', padding: '1px 6px', borderRadius: 3,
            }}>
              {badgeLabel(streamingType)}
            </span>
            <span className="status-chip">
              {orbState === 'thinking' || orbState === 'decomposing' ? 'processing...' : 'speaking...'}
            </span>
            <div style={{
              fontSize: 11, color: 'var(--text-2)', lineHeight: 1.6,
              wordBreak: 'break-word', marginTop: 4,
            }}>
              {currentStream.slice(-200)}
              <span style={{ animation: 'jblink 1s steps(1) infinite', color: 'var(--accent)' }}>▍</span>
            </div>
          </div>
        )}
        {toolStatus && !currentStream && (
          <div
            className="card tool"
            style={{ margin: '4px 12px', padding: '8px 12px' }}
          >
            <div className="card-badge">TOOL</div>
            <div style={{ fontSize: 11, color: 'var(--amber)' }}>{toolStatus}</div>
          </div>
        )}
      </div>
    </div>
  )
}
