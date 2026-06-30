import { useState, useRef, useCallback, useEffect } from 'react'

/**
 * useVoiceRecorder — records audio from the microphone and sends it to /api/voice/stt.
 *
 * Uses MediaRecorder API to capture audio and POST the blob to the backend.
 * Opus/WebM preferred; Safari falls back to browser default container.
 *
 * Returns:
 *   - recording: bool — currently recording
 *   - transcript: string — last transcription result
 *   - error: string | null
 *   - start: () => void — start recording
 *   - stop: () => Promise<string> — stop and transcribe, returns text
 *   - toggle: () => void — start/stop toggle
 *   - clearError: () => void — reset error state
 */
export function useVoiceRecorder() {
  const [recording, setRecording] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState(null)
  const [transcribing, setTranscribing] = useState(false)

  const streamRef = useRef(null)
  const chunksRef = useRef([])
  const mediaRecorderRef = useRef(null)
  const abortRef = useRef(null)  // AbortController for in-flight STT fetch

  const start = useCallback(async () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') return // already recording
    setError(null)
    try {
      // Guard: browser must support getUserMedia and MediaRecorder
      if (typeof MediaRecorder === 'undefined') {
        throw new Error('MediaRecorder not supported in this browser')
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })

      // Pick MIME: prefer Opus, fallback to plain WebM, WAV for Safari
      let mimeType = ''
      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        mimeType = 'audio/webm;codecs=opus'
      } else if (MediaRecorder.isTypeSupported('audio/webm')) {
        mimeType = 'audio/webm'
      }
      // Safari: no WebM support; MediaRecorder will use default (mp4) — STT backend handles it

      const opts = mimeType ? { mimeType } : {}
      const recorder = new MediaRecorder(stream, opts)
      chunksRef.current = []

      // Only store refs after constructor succeeds — prevents stream leak on throw
      streamRef.current = stream
      mediaRecorderRef.current = recorder

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.start()
      setRecording(true)
    } catch (e) {
      // If stream was acquired but recorder failed, clean up
      if (streamRef.current && !mediaRecorderRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop())
        streamRef.current = null
      }
      setError(e.message || 'Could not access microphone')
    }
  }, [])

  const stop = useCallback(() => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current
      if (!recorder || recorder.state === 'inactive') {
        setRecording(false)
        resolve('')
        return
      }

      recorder.onstop = async () => {
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(t => t.stop())
          streamRef.current = null
        }
        setRecording(false)

        const blob = new Blob(chunksRef.current)
        if (blob.size === 0) {
          resolve('')
          return
        }

        // Abort any previous STT fetch still in flight (double-stop guard)
        if (abortRef.current) abortRef.current.abort()
        const controller = new AbortController()
        abortRef.current = controller

        setTranscribing(true)
        try {
          const res = await fetch('/api/voice/stt', {
            method: 'POST',
            body: blob,
            signal: controller.signal,
          })
          const data = await res.json()
          if (data.ok && data.text) {
            setTranscript(data.text)
            resolve(data.text)
          } else {
            setError(data.error || 'Transcription failed')
            resolve('')
          }
        } catch (e) {
          if (e.name !== 'AbortError') {
            setError(e.message || 'Network error during transcription')
          }
          resolve('')
        } finally {
          setTranscribing(false)
          abortRef.current = null
        }
      }

      recorder.stop()
    })
  }, [])

  const toggle = useCallback(() => {
    if (recording) {
      return stop()
    } else {
      return start()
    }
  }, [recording, start, stop])

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop())
      }
      if (abortRef.current) abortRef.current.abort()
    }
  }, [])

  return { recording, transcript, error, transcribing, start, stop, toggle, clearError: () => setError(null) }
}
