import { useState, useRef, useCallback, useEffect } from 'react'

const MAX_QUEUE = 50

// Shared audio analyser for real-time voice amplitude
let _audioCtx = null
let _analyser = null
let _analyserData = null
let _ampRaf = null
let _currentAmp = 0
let _userInteracted = false

function _ensureAudio() {
  if (!_audioCtx) {
    _audioCtx = new (window.AudioContext || window.webkitAudioContext)()
    _analyser = _audioCtx.createAnalyser()
    _analyser.fftSize = 256
    _analyser.smoothingTimeConstant = 0.4
    _analyserData = new Uint8Array(_analyser.frequencyBinCount)
    _analyser.connect(_audioCtx.destination)
  }
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

// Cross-tab coordination: only one tab plays audio at a time
let _speakerChannel = null
let _isSpeaker = true  // first tab is the speaker by default

function _ensureChannel() {
  if (_speakerChannel) return
  try {
    _speakerChannel = new BroadcastChannel('dela-audio')
    _speakerChannel.onmessage = (ev) => {
      if (ev.data === 'speaking') _isSpeaker = false
      if (ev.data === 'stopped') _isSpeaker = true
    }
  } catch (_) {
    _speakerChannel = null
  }
}

function _claimSpeaker() {
  if (!_speakerChannel) return true
  _isSpeaker = true
  try { _speakerChannel.postMessage('speaking') } catch (_) {}
  return true
}

function _releaseSpeaker() {
  // Broadcast that speaker role is available — other tabs can take over
  // This tab remains the speaker until another tab claims it
  try { _speakerChannel?.postMessage('stopped') } catch (_) {}
}

export function useVoiceTTS(token) {
  const [speaking, setSpeaking] = useState(false)
  const queueRef = useRef([])
  const playingRef = useRef(false)
  const cancelledRef = useRef(false)
  const sourceNodeRef = useRef(null)
  const prefetchBufferRef = useRef(null)  // pre-fetched audio for next sentence
  const tokenRef = useRef(token)
  tokenRef.current = token

  // Fetch TTS audio and return decoded AudioBuffer (or null)
  const fetchAudio = useCallback(async (text) => {
    try {
      const headers = { 'Content-Type': 'application/json' }
      if (tokenRef.current) headers['Authorization'] = `Bearer ${tokenRef.current}`
      const resp = await fetch('/api/voice/tts', {
        method: 'POST',
        headers,
        body: JSON.stringify({ text }),
      })
      if (!resp.ok) return null
      const arrayBuffer = await resp.arrayBuffer()
      if (cancelledRef.current) return null
      _ensureAudio()
      if (_audioCtx.state === 'suspended') await _audioCtx.resume()
      return await _audioCtx.decodeAudioData(arrayBuffer)
    } catch {
      return null
    }
  }, [])

  // Prefetch the next sentence while current plays
  const prefetchNext = useCallback(() => {
    if (queueRef.current.length === 0 || cancelledRef.current) return
    const nextText = queueRef.current[0]
    if (!nextText || !nextText.trim()) return
    // Don't overwrite an existing prefetch
    if (prefetchBufferRef.current) return
    fetchAudio(nextText).then(buffer => {
      if (buffer && !cancelledRef.current) {
        prefetchBufferRef.current = { text: nextText, buffer }
      }
    })
  }, [fetchAudio])

  const playNext = useCallback(() => {
    if (queueRef.current.length === 0) {
      playingRef.current = false
      setSpeaking(false)
      _stopAmpLoop()
      _releaseSpeaker()
      return
    }

    const text = queueRef.current.shift()
    if (!text || !text.trim()) {
      playNext()
      return
    }

    playingRef.current = true
    setSpeaking(true)

    // Use prefetched buffer if available
    if (prefetchBufferRef.current && prefetchBufferRef.current.text === text) {
      const audioBuffer = prefetchBufferRef.current.buffer
      prefetchBufferRef.current = null
      if (cancelledRef.current) { playNext(); return }
      playBuffer(audioBuffer)
      // Prefetch next
      prefetchNext()
      return
    }

    // Fetch and play
    fetchAudio(text).then(audioBuffer => {
      prefetchBufferRef.current = null  // clear any stale prefetch
      if (!audioBuffer || cancelledRef.current) { playNext(); return }
      playBuffer(audioBuffer)
      // Prefetch next
      prefetchNext()
    })
  }, [fetchAudio, prefetchNext])

  const playBuffer = useCallback((audioBuffer) => {
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
  }, [playNext])

  const speak = useCallback((text) => {
    // Only play audio if this tab is the speaker (prevents duplicate audio from multiple tabs)
    if (_speakerChannel && !_isSpeaker) return

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
      _claimSpeaker()
      if (_audioCtx && _audioCtx.state === 'suspended') {
        _audioCtx.resume()
      }
      playNext()
    }
  }, [playNext])

  const stop = useCallback(() => {
    cancelledRef.current = true
    queueRef.current.length = 0
    prefetchBufferRef.current = null
    _stopAmpLoop()
    try {
      sourceNodeRef.current?.stop()
      sourceNodeRef.current?.disconnect()
    } catch (_) {}
    sourceNodeRef.current = null
    playingRef.current = false
    setSpeaking(false)
    _releaseSpeaker()
  }, [])

  useEffect(() => {
    return () => {
      cancelledRef.current = true
      queueRef.current.length = 0
      prefetchBufferRef.current = null
      _stopAmpLoop()
      try {
        sourceNodeRef.current?.stop()
        sourceNodeRef.current?.disconnect()
      } catch (_) {}
    }
  }, [])

  useEffect(() => {
    const onInteract = () => {
      _userInteracted = true
      _ensureAudio()
      _ensureChannel()
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
