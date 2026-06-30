import { FloatWindow } from './FloatWindow'
import { RichMessage } from './RichMessage'

export function StreamWindow({ panel, onClose, onFocus, onDragMove, conversation, currentStream, toolStatus, systemState }) {
  const recent = conversation.slice(-20)

  const msgAlign = (role) => {
    if (role === 'user') return 'flex-end'
    if (role === 'assistant') return 'flex-start'
    return 'center'  // tool / unknown
  }

  const msgColor = (role) => {
    if (role === 'user') return { dot: 'var(--cyan)', bg: 'rgba(0,240,255,0.06)', tag: 'var(--cyan)', tagBg: 'rgba(0,240,255,0.12)' }
    if (role === 'assistant') return { dot: 'var(--green)', bg: 'rgba(70,242,176,0.06)', tag: 'var(--green)', tagBg: 'rgba(70,242,176,0.12)' }
    return { dot: 'var(--amber)', bg: 'rgba(255,179,0,0.06)', tag: 'var(--amber)', tagBg: 'rgba(255,179,0,0.12)' }
  }

  const renderNode = (role, label, tag, content, isStreaming, isTool) => {
    const colors = msgColor(role)
    const align = msgAlign(role)
    const isCenter = align === 'center'

    return (
      <div style={{
        display: 'flex',
        justifyContent: align,
        padding: '3px 0',
      }}>
        <div style={{
          maxWidth: isCenter ? '100%' : '85%',
          padding: '5px 8px',
          borderRadius: 8,
          background: colors.bg,
          border: `1px solid ${colors.dot}22`,
          fontSize: 11,
          lineHeight: 1.4,
          color: 'var(--text)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: content ? 3 : 0 }}>
            <span style={{
              fontSize: 9, fontWeight: 600, color: colors.tag,
              fontFamily: "'JetBrains Mono', monospace", letterSpacing: '0.05em'
            }}>
              {label}
            </span>
            <span style={{
              fontSize: 8, padding: '0 4px', borderRadius: 3,
              color: colors.tag, background: colors.tagBg,
              fontFamily: "'JetBrains Mono', monospace"
            }}>
              {tag}
            </span>
            {isStreaming && (
              <span style={{ animation: 'jblink 1s steps(1) infinite', color: 'var(--accent)', fontSize: 9 }}>▍</span>
            )}
          </div>
          {content && (
            <div style={{ maxHeight: 200, overflow: 'auto' }}>
              <RichMessage content={content} maxHeight={200} />
            </div>
          )}
          {isTool && (
            <div style={{ maxHeight: 120, overflow: 'auto', fontSize: 10, color: 'var(--amber)', opacity: 0.85 }}>
              <RichMessage content={content} maxHeight={120} />
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <FloatWindow
      title="THE STREAM"
      subtitle={systemState === 'idle' ? '— IDLE' : systemState.toUpperCase()}
      x={panel.x} y={panel.y} z={panel.z}
      onClose={onClose}
      onFocus={onFocus}
      onDragMove={onDragMove}
      width={600}
      maxHeight="62vh"
    >
      <div className="float-body" style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {recent.length === 0 && !currentStream && !toolStatus && (
          <p className="panel-empty">No activity yet. Send a message to begin.</p>
        )}

        {recent.map((msg, i) => {
          const isTool = msg.role === 'tool' || msg.content?.startsWith('[')
          const role = isTool ? 'tool' : msg.role
          const label = isTool ? 'TOOL' : role === 'user' ? 'YOU' : 'DELA'
          const tag = isTool ? 'EXEC' : role === 'user' ? 'DIRECTIVE' : 'RESPONSE'
          return (
            <div key={msg.id || i}>
              {renderNode(role, label, tag, msg.content, false, isTool)}
            </div>
          )
        })}

        {currentStream && renderNode('assistant', 'DELA', 'STREAMING', currentStream, true, false)}

        {toolStatus && renderNode('tool', 'TOOL', 'ACTIVE', toolStatus, false, true)}
      </div>
    </FloatWindow>
  )
}
