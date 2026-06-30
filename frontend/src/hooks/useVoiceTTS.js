import { useState, useRef, useCallback, useEffect } from 'react'

const MAX_QUEUE = 50

// Shared audio analyser for real-time voice amplitude
let _audioCtx = null
let _analyser = null
let _analyserData = null
let _ampRaf = null
let _currentAmp = 0
let _userInteracted = false  // true after first click/key — unlocks autoplay

function _ensureAudio() {
  if (!_audioCtx) {
    _audioCtx = new (window.AudioContext || window.webkitAudioContext)()
    _analyser = _audioCtx.createAnalyser()
    _analyser.fftSize = 256
    _analyser.smoothingTimeConstant = 0.4
    _analyserData = new Uint8Array(_analyser.frequencyBinCount)
    _analyser.connect(_audioCtx.destination)
  }
  // Always ensure context is running
  if (_audioCtx.state === 'suspended') {
    _audioCtx.resume()
  }
}

function _startAmpLoop() {
  if (_ampRaf) return
  const tick = () => {
    if (!_analyser) { _ampRaf = null; return }
    _analyser.getByteTimeDomainData(_analyserData)
    let sum = 0
    for (let i = 0; i < _analyserData.length; i++) {
      const v = (_analyserData[i] - 128) / 128
      sum += v * v
    }
    const rms = Math.sqrt(sum / _analyserData.length)
    _currentAmp += (rms - _currentAmp) * 0.3
    _ampRaf = requestAnimationFrame(tick)
  }
  _ampRaf = requestAnimationFrame(tick)
}

function _stopAmpLoop() {
  if (_ampRaf) { cancelAnimationFrame(_ampRaf); _ampRaf = null }
  _currentAmp = 0
}

export function getVoiceAmplitude() {
  return _currentAmp
}

/**
 * useVoiceTTS — sends text to /api/voice/tts and plays the returned audio.
 * Exposes real-time voice amplitude for visual pulse sync.
 */
export function useVoiceTTS() {
  const [speaking, setSpeaking] = useState(false)
  const audioRef = useRef(null)
  const queueRef = useRef([])
  const playingRef = useRef(false)
  const cancelledRef = useRef(false)
  const sourceNodeRef = useRef(null)  // current AudioBufferSourceNode

  const playNext = useCallback(() => {
    if (queueRef.current.length === 0) {
      playingRef.current = false
      setSpeaking(false)
      _stopAmpLoop()
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
        return r.arrayBuffer()
      })
      .then(arrayBuffer => {
        if (cancelledRef.current) { playNext(); return }
        _ensureAudio()
        if (_audioCtx.state === 'suspended') {
          _audioCtx.resume()
        }
        // Decode WAV into AudioBuffer for proper Web Audio playback
        return _audioCtx.decodeAudioData(arrayBuffer).then(audioBuffer => {
          if (cancelledRef.current) { playNext(); return }
          const source = _audioCtx.createBufferSource()
          source.buffer = audioBuffer
          source.connect(_analyser)
          sourceNodeRef.current = source
          _startAmpLoop()
          source.onended = () => {
            try { sourceNodeRef.current?.disconnect() } catch (_) {}
            sourceNodeRef.current = null
            _stopAmpLoop()
            playNext()
          }
          source.start()
        })
      })
      .catch(() => {
        playNext()
      })
  }, [])

  const speak = useCallback((text) => {
    // Strip emojis and other symbols that TTS can't pronounce
    const clean = text.replace(/[\p{Emoji_Presentation}\p{Emoji}\u200D\uFE0F]/gu, '').replace(/\s{2,}/g, ' ')
    const sentences = clean.match(/[^.!?]+(?:[.!?](?!\s+[A-Z]))*[.!?]?/g) || [clean]
    const filtered = sentences.filter(s => s.trim())
    if (filtered.length === 0) filtered.push(clean)
    if (queueRef.current.length + filtered.length > MAX_QUEUE) {
      queueRef.current.splice(0, queueRef.current.length + filtered.length - MAX_QUEUE)
    }
    queueRef.current.push(...filtered)
    if (!playingRef.current) {
      cancelledRef.current = false
      // Resume AudioContext now — user interaction (send message) has occurred
      if (_audioCtx && _audioCtx.state === 'suspended') {
        _audioCtx.resume()
      }
      playNext()
    }
  }, [playNext])

  const stop = useCallback(() => {
    cancelledRef.current = true
    queueRef.current.length = 0
    _stopAmpLoop()
    try {
      sourceNodeRef.current?.stop()
      sourceNodeRef.current?.disconnect()
    } catch (_) {}
    sourceNodeRef.current = null
    playingRef.current = false
    setSpeaking(false)
  }, [])

  useEffect(() => {
    return () => {
      cancelledRef.current = true
      queueRef.current.length = 0
      _stopAmpLoop()
      try {
        sourceNodeRef.current?.stop()
        sourceNodeRef.current?.disconnect()
      } catch (_) {}
    }
  }, [])

  // Create AudioContext on first user interaction (required by browser autoplay policy)
  useEffect(() => {
    const onInteract = () => {
      _userInteracted = true
      _ensureAudio()
      document.removeEventListener('click', onInteract)
      document.removeEventListener('keydown', onInteract)
    }
    document.addEventListener('click', onInteract)
    document.addEventListener('keydown', onInteract)
    return () => {
      document.removeEventListener('click', onInteract)
      document.removeEventListener('keydown', onInteract)
    }
  }, [])

  return { speaking, speak, stop }
}
