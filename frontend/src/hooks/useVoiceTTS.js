import { useState, useRef, useCallback } from 'react'

/**
 * useVoiceTTS — sends text to /api/voice/tts and plays the returned audio.
 *
 * Returns:
 *   - speaking: bool — audio is currently playing
 *   - speak: (text: string) => void — synthesize and play
 *   - stop: () => void — stop playback
 */
export function useVoiceTTS() {
  const [speaking, setSpeaking] = useState(false)
  const audioRef = useRef(null)
  const queueRef = useRef([])
  const playingRef = useRef(false)

  const playNext = useCallback(() => {
    if (queueRef.current.length === 0) {
      playingRef.current = false
      setSpeaking(false)
      return
    }

    const text = queueRef.current.shift()
    if (!text || !text.trim()) {
      playNext()
      return
    }

    playingRef.current = true
    setSpeaking(true)

    fetch('/api/voice/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })
      .then(r => {
        if (!r.ok) throw new Error('TTS failed')
        return r.blob()
      })
      .then(blob => {
        const url = URL.createObjectURL(blob)
        const audio = new Audio(url)
        audioRef.current = audio
        audio.onended = () => {
          URL.revokeObjectURL(url)
          playNext()
        }
        audio.onerror = () => {
          URL.revokeObjectURL(url)
          playNext()
        }
        audio.play()
      })
      .catch(() => {
        playNext()
      })
  }, [])

  const speak = useCallback((text) => {
    // Split into sentences for faster playback start
    const sentences = text.match(/[^.!?]+[.!?]*/g) || [text]
    queueRef.current.push(...sentences)
    if (!playingRef.current) {
      playNext()
    }
  }, [playNext])

  const stop = useCallback(() => {
    queueRef.current = []
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
    playingRef.current = false
    setSpeaking(false)
  }, [])

  return { speaking, speak, stop }
}
