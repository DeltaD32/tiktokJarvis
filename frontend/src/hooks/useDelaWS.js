import { useState, useEffect, useRef, useCallback } from 'react'

const WS_URL = `ws://${window.location.host}/ws`

export function useDelaWS() {
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)

  const [connected, setConnected]         = useState(false)
  const [orbState, setOrbState]           = useState('idle')
  const [conversation, setConversation]   = useState([])
  const [currentStream, setCurrentStream] = useState(null)   // null = no active stream
  const [toolStatus, setToolStatus]       = useState(null)
  const [activePanel, setActivePanel]     = useState(null)
  const [panelMessage, setPanelMessage]   = useState('')
  const [confirmRequest, setConfirmRequest] = useState(null)
  const [notices, setNotices]             = useState([])
  const [noticeCount, setNoticeCount]     = useState(0)
  const [heartbeatActive, setHeartbeatActive] = useState(true)
  const [cost, setCost]                   = useState('—')

  // Buffer to hold the full reply text while it animates
  const streamBuffer = useRef('')

  const connect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
      reconnectTimer.current = null
    }

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)

    ws.onmessage = (ev) => {
      let data
      try { data = JSON.parse(ev.data) } catch { return }

      switch (data.type) {
        case 'init':
          setNotices(data.notices ?? [])
          setNoticeCount((data.notices ?? []).length)
          setHeartbeatActive(data.heartbeat_active ?? true)
          if (data.cost) setCost(data.cost)
          break

        case 'state_change':
          setOrbState(data.state)
          break

        case 'token':
          if (data.tool_blip) {
            setToolStatus(data.content)
          } else {
            streamBuffer.current += data.content
            setCurrentStream(streamBuffer.current)
          }
          break

        case 'reply_done': {
          const reply = streamBuffer.current
          if (reply) {
            setConversation(prev => [
              ...prev,
              { role: 'assistant', content: reply, id: Date.now() },
            ])
            streamBuffer.current = ''
            setCurrentStream(null)
          }
          setToolStatus(null)
          setOrbState('idle')
          break
        }

        case 'confirmation_request':
          setConfirmRequest({ id: data.id, description: data.description })
          setOrbState('alert')
          break

        case 'open_panel':
          setActivePanel(data.panel)
          setPanelMessage(data.message ?? '')
          break

        case 'notice':
          setNotices(prev => [...prev, data.notice])
          setNoticeCount(prev => prev + 1)
          break

        case 'notices_refresh':
          setNotices(data.notices ?? [])
          setNoticeCount((data.notices ?? []).length)
          break

        case 'heartbeat_state':
          setHeartbeatActive(data.active)
          break

        case 'cost_update':
          setCost(data.cost ?? '—')
          break

        default:
          break
      }
    }

    ws.onclose = () => {
      setConnected(false)
      reconnectTimer.current = setTimeout(connect, 3500)
    }

    ws.onerror = () => ws.close()
  }, [])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
    }
  }, [connect])

  const send = useCallback((payload) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload))
    }
  }, [])

  const sendMessage = useCallback((content) => {
    setConversation(prev => [...prev, { role: 'user', content, id: Date.now() }])
    setOrbState('thinking')
    setCurrentStream(null)
    streamBuffer.current = ''
    send({ type: 'message', content })
  }, [send])

  const sendConfirm = useCallback((id, approved) => {
    send({ type: 'confirm', id, approved })
    setConfirmRequest(null)
    if (approved) setOrbState('thinking')
    else setOrbState('idle')
  }, [send])

  const closePanel = useCallback(() => {
    setActivePanel(null)
    setPanelMessage('')
  }, [])

  const dismissNotice = useCallback((id) => {
    fetch(`/api/notices/${id}`, { method: 'DELETE' }).catch(() => {})
    setNotices(prev => prev.filter(n => n.id !== id))
    setNoticeCount(prev => Math.max(0, prev - 1))
  }, [])

  const killHeartbeat = useCallback(() => {
    fetch('/api/heartbeat/kill', { method: 'POST' }).catch(() => {})
    setHeartbeatActive(false)
  }, [])

  const resumeHeartbeat = useCallback(() => {
    fetch('/api/heartbeat/resume', { method: 'POST' }).catch(() => {})
    setHeartbeatActive(true)
  }, [])

  return {
    connected,
    orbState,
    conversation,
    currentStream,
    toolStatus,
    activePanel,
    panelMessage,
    confirmRequest,
    notices,
    noticeCount,
    heartbeatActive,
    cost,
    sendMessage,
    sendConfirm,
    closePanel,
    dismissNotice,
    killHeartbeat,
    resumeHeartbeat,
  }
}
