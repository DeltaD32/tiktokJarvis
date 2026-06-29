import { useState, useRef, useCallback, useEffect } from 'react'

/**
 * useVoiceRecorder — records audio from the microphone and sends it to /api/voice/stt.
 *
 * Uses the Web Audio API to capture at 16kHz mono, package as WAV, and POST
 * to the backend. No external dependencies — pure browser API.
 *
 * Returns:
 *   - recording: bool — currently recording
 *   - transcript: string — last transcription result
 *   - error: string | null
 *   - start: () => void — start recording
 *   - stop: () => Promise<string> — stop and transcribe, returns text
 *   - toggle: () => void — start/stop toggle
 */
export function useVoiceRecorder() {
  const [recording, setRecording] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState(null)
  const [transcribing, setTranscribing] = useState(false)

  const audioCtxRef = useRef(null)
  const streamRef = useRef(null)
  const chunksRef = useRef([])
  const mediaRecorderRef = useRef(null)

  const start = useCallback(async () => {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })
      streamRef.current = stream

      // Use MediaRecorder — most reliable cross-browser
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm'

      const recorder = new MediaRecorder(stream, { mimeType })
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.start()
      mediaRecorderRef.current = recorder
      setRecording(true)
    } catch (e) {
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
        // Stop all tracks
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(t => t.stop())
          streamRef.current = null
        }
        setRecording(false)

        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        if (blob.size === 0) {
          resolve('')
          return
        }

        setTranscribing(true)
        try {
          const formData = new FormData()
          formData.append('audio', blob, 'recording.webm')

          const res = await fetch('/api/voice/stt', {
            method: 'POST',
            body: blob,
            headers: { 'Content-Type': 'audio/webm' },
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
          setError(e.message || 'Network error during transcription')
          resolve('')
        } finally {
          setTranscribing(false)
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
    }
  }, [])

  return { recording, transcript, error, transcribing, start, stop, toggle }
}
