import { useMemo } from 'react'

export function VoiceHud({ speaking, caption, recording, transcribing }) {
  if (!speaking && !recording && !transcribing) return null

  // Memoize bar configs so animation durations don't jitter on re-render
  const bars = useMemo(() =>
    Array.from({ length: 20 }, () => ({
      dur: (0.5 + Math.random() * 0.55).toFixed(2) + 's',
      delay: (Math.random() * 0.4).toFixed(2) + 's',
    }))
  , [])

  const label = recording ? 'LISTENING' : transcribing ? 'TRANSCRIBING' : 'SPEAKING'
  const text = recording ? 'recording your voice...' : transcribing ? 'converting speech to text...' : caption

  return (
    <div className="voice-hud" style={recording || transcribing ? { top: '52%' } : undefined}>
      <div className="voice-bars" style={recording ? { ['--bar-color']: 'var(--red)' } : undefined}>
        {bars.map((b, i) => (
          <div
            key={i}
            className="voice-bar"
            style={{
              animation: `jeq ${b.dur} ease-in-out infinite`,
              animationDelay: b.delay,
              background: recording ? 'var(--red)' : transcribing ? 'var(--amber)' : 'var(--accent)',
            }}
          />
        ))}
      </div>
      <div className="voice-caption">
        <span className="voice-caption-label">{label}</span>
        <span className="voice-caption-text">{text}</span>
      </div>
    </div>
  )
}
