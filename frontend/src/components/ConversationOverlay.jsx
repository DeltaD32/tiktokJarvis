import { useEffect, useState, useRef } from 'react'

// Typewriter effect — text arrives complete; this animates it character-by-character
function Typewriter({ text }) {
  const [chars, setChars] = useState(0)

  useEffect(() => {
    setChars(0)
    if (!text) return

    // Faster for longer text so it never feels sluggish
    const step = Math.max(2, Math.ceil(text.length / 160))
    const delay = 14

    const id = setInterval(() => {
      setChars(prev => {
        const next = prev + step
        if (next >= text.length) { clearInterval(id); return text.length }
        return next
      })
    }, delay)

    return () => clearInterval(id)
  }, [text])

  return (
    <>
      {text.slice(0, chars)}
      {chars < text.length && <span className="cursor-blink" />}
    </>
  )
}

// Show the last N messages from the conversation
const MAX_VISIBLE = 5

export function ConversationOverlay({ conversation, currentStream, toolStatus }) {
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation, currentStream, toolStatus])

  const visible = conversation.slice(-MAX_VISIBLE)

  return (
    <div className="conv-overlay">
      {visible.map(msg => (
        <div key={msg.id} className={`conv-msg ${msg.role}`}>
          <div className="msg-role">{msg.role === 'user' ? 'YOU' : 'DELA'}</div>
          {msg.content}
        </div>
      ))}

      {toolStatus && (
        <div className="conv-msg tool-blip">
          {toolStatus}
        </div>
      )}

      {currentStream && (
        <div className="conv-msg streaming">
          <div className="msg-role">DELA</div>
          <Typewriter text={currentStream} />
        </div>
      )}

      <div ref={endRef} />
    </div>
  )
}
