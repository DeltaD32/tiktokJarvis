import { useState, useEffect, useRef, useCallback } from 'react'

const WS_URL = `ws://${window.location.host}/ws`

export function useDelaWS() {
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)
  const connIdRef = useRef(0)  // incremented on each connect; used to discard stale onclose

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
  const [agentStatus, setAgentStatus]     = useState({})  // { name: { state, task } }

  // Buffer to hold the full reply text while it animates
  const streamBuffer = useRef('')
  const idleTimer = useRef(null)
  const _processingTurn = useRef(false)
  const msgIdRef = useRef(0)

  const connect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
      reconnectTimer.current = null
    }

    connIdRef.current += 1
    const connId = connIdRef.current

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)

    ws.onmessage = (ev) => {
      if (connIdRef.current !== connId) return  // stale connection
      let data
      try { data = JSON.parse(ev.data) } catch { return }

      switch (data.type) {
        case 'init':
          setNotices(data.notices ?? [])
          setNoticeCount((data.notices ?? []).length)
          setHeartbeatActive(data.heartbeat_active ?? true)
          if (data.cost) setCost(data.cost)
          _processingTurn.current = false
          streamBuffer.current = ''
          break

        case 'state_change':
          if (idleTimer.current) {
            clearTimeout(idleTimer.current)
            idleTimer.current = null
          }
          if (data.state === 'idle') {
            _processingTurn.current = false
            // Delay idle transition so the conversation stays visible between turns
            idleTimer.current = setTimeout(() => {
              setOrbState('idle')
              idleTimer.current = null
            }, 60000)
          } else {
            setOrbState(data.state)
          }
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
          streamBuffer.current = ''
          setCurrentStream(null)
          if (reply) {
            msgIdRef.current += 1
            setConversation(prev => [
              ...prev,
              { role: 'assistant', content: reply, id: msgIdRef.current },
            ])
          }
          setToolStatus(null)
          _processingTurn.current = false
          // Delay idle so the conversation stays visible between turns
          if (idleTimer.current) clearTimeout(idleTimer.current)
          idleTimer.current = setTimeout(() => {
            setOrbState('idle')
            idleTimer.current = null
          }, 60000)
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

        case 'agent_status':
          setAgentStatus(prev => ({
            ...prev,
            [data.agent]: { state: data.state, task: data.task || '' },
          }))
          break

        default:
          break
      }
    }

    ws.onclose = () => {
      setConnected(false)
      _processingTurn.current = false
      setToolStatus(null)
      setCurrentStream(null)
      streamBuffer.current = ''
      if (idleTimer.current) {
        clearTimeout(idleTimer.current)
        idleTimer.current = null
      }
      if (connIdRef.current === connId) {
        reconnectTimer.current = setTimeout(connect, 3500)
      }
    }

    ws.onerror = () => { if (connIdRef.current === connId) ws.close() }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      connIdRef.current += 1  // invalidate any pending reconnect from this mount
      wsRef.current?.close()
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      if (idleTimer.current) clearTimeout(idleTimer.current)
    }
  }, [connect])

  const send = useCallback((payload) => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      // If CONNECTING, the message will be lost; reconnect will resync via init
      return
    }
    try { ws.send(JSON.stringify(payload)) } catch { /* malformed payload */ }
  }, [])

  const sendMessage = useCallback((content) => {
    console.log('[ws] sendMessage:', content.slice(0, 60))
    // Guard: if the brain is already processing, queue this for the next turn
    if (_processingTurn.current) {
      console.log('[ws] (ignored — already processing a turn)')
      return
    }
    if (idleTimer.current) {
      clearTimeout(idleTimer.current)
      idleTimer.current = null
    }
    _processingTurn.current = true
    msgIdRef.current += 1
    setConversation(prev => [...prev, { role: 'user', content, id: msgIdRef.current }])
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
    agentStatus,
    sendMessage,
    sendConfirm,
    closePanel,
    dismissNotice,
    killHeartbeat,
    resumeHeartbeat,
  }
}
