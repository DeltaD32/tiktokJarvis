export function VoiceHud({ speaking, caption }) {
  if (!speaking) return null

  const bars = Array.from({ length: 20 }, (_, i) => ({
    dur: (0.5 + Math.random() * 0.55).toFixed(2) + 's',
    delay: (Math.random() * 0.4).toFixed(2) + 's',
  }))

  return (
    <div className="voice-hud">
      <div className="voice-bars">
        {bars.map((b, i) => (
          <div
            key={i}
            className="voice-bar"
            style={{ animation: `jeq ${b.dur} ease-in-out infinite`, animationDelay: b.delay }}
          />
        ))}
      </div>
      <div className="voice-caption">
        <span className="voice-caption-label">DELA</span>
        <span className="voice-caption-text">{caption}</span>
      </div>
    </div>
  )
}
