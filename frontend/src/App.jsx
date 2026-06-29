import { useState, useEffect, useCallback, useRef } from 'react'
import { AnimatePresence } from 'framer-motion'

import { ParticleCanvas }      from './components/ParticleCanvas'
import { TopStrip }            from './components/TopStrip'
import { Dock }                from './components/Dock'
import { VoiceHud }            from './components/VoiceHud'
import { HitlGate }            from './components/HitlGate'
import { HiveWindow }          from './components/HiveWindow'
import { StreamWindow }        from './components/StreamWindow'
import { SandboxWindow }       from './components/SandboxWindow'
import { MemoryPanel }         from './components/panels/MemoryPanel'
import { StateBrowserPanel }   from './components/panels/StateBrowserPanel'
import { ToolBrowserPanel }    from './components/panels/ToolBrowserPanel'
import { AuditPanel }          from './components/panels/AuditPanel'
import { NoticesPanel }         from './components/panels/NoticesPanel'
import { TasksPanel }           from './components/panels/TasksPanel'
import { SecurityPanel }        from './components/panels/SecurityPanel'
import { SettingsPanel }        from './components/panels/SettingsPanel'
import { AnalyticsPanel }       from './components/panels/AnalyticsPanel'
import { useDelaWS }            from './hooks/useDelaWS'
import { useVoiceRecorder }     from './hooks/useVoiceRecorder'
import { useVoiceTTS }          from './hooks/useVoiceTTS'
import { applyTheme, getCurrentTheme, THEMES } from './themes'

const ACCENT_RGB = {
  idle:     '0,240,255',
  thinking: '179,136,255',
  speaking: '0,240,255',
  busy:     '255,179,0',
  alert:    '255,90,69',
  complete: '70,242,176',
}

// Merge theme colors into ACCENT_RGB
const _themeName = getCurrentTheme()
const _theme = THEMES[_themeName] || THEMES.jarvis
Object.assign(ACCENT_RGB, {
  idle:     _theme.colors.idle,
  thinking: _theme.colors.thinking,
  busy:     _theme.colors.busy,
  alert:    _theme.colors.alert,
  complete: _theme.colors.complete,
})

const IDLE_STATS = [
  { label: 'HEARTBEAT', value: '—', pos: { left: '9%', top: '27%' }, key: 'heartbeat' },
  { label: 'TOOLS', value: '46', pos: { right: '9%', top: '27%' }, key: 'tools' },
  { label: 'UPLINK', value: '—', pos: { left: '11%', top: '60%' }, key: 'uplink' },
  { label: 'AGENTS', value: '5', sub: 'ready', pos: { right: '11%', top: '60%' }, key: 'agents' },
]

export default function App() {
  const {
    connected, orbState, conversation, currentStream, toolStatus,
    activePanel, panelMessage, confirmRequest,
    notices, noticeCount, heartbeatActive, cost,
    sendMessage, sendConfirm, closePanel, dismissNotice,
    killHeartbeat, resumeHeartbeat,
  } = useDelaWS()

  const [input, setInput] = useState('')
  const [panels, setPanels] = useState({
    hive:    { open: false, x: 28, y: 96, z: 1 },
    stream:  { open: false, x: 360, y: 460, z: 1 },
    sandbox: { open: false, x: 880, y: 96, z: 1 },
  })
  const [localPanel, setLocalPanel] = useState(null)
  const zRef = useRef(1)

  // Live idle stats
  const [uplink, setUplink] = useState(null)
  const [agentInfo, setAgentInfo] = useState({ count: 5, ready: 5 })
  const [toolCount, setToolCount] = useState(46)
  const [voiceEnabled, setVoiceEnabled] = useState(false)

  // Voice
  const { recording, transcribing, error: voiceError, toggle: toggleVoice } = useVoiceRecorder()
  const { speaking: ttsSpeaking, speak: ttsSpeak, stop: ttsStop } = useVoiceTTS()

  // Initialize theme on mount
  useEffect(() => {
    applyTheme(getCurrentTheme())
  }, [])

  // Fetch uplink status + agent/tool counts on mount and periodically
  const fetchUplink = useCallback(() => {
    fetch('/api/uplink')
      .then(r => r.json())
      .then(data => setUplink(data))
      .catch(() => setUplink({ status: 'unreachable' }))
  }, [])

  const fetchAgentInfo = useCallback(() => {
    fetch('/api/agents')
      .then(r => r.json())
      .then(data => {
        const agents = data || []
        const ready = agents.filter(a => a.status === 'ready').length
        setAgentInfo({ count: agents.length, ready, agents })
      })
      .catch(() => {})
  }, [])

  const fetchToolCount = useCallback(() => {
    fetch('/api/tools')
      .then(r => r.json())
      .then(data => setToolCount(data?.length || 46))
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetchUplink()
    fetchAgentInfo()
    fetchToolCount()
    const interval = setInterval(() => {
      fetchUplink()
      fetchAgentInfo()
    }, 15000)
    return () => clearInterval(interval)
  }, [fetchUplink, fetchAgentInfo, fetchToolCount])

  // Update CSS accent variables when state changes
  useEffect(() => {
    const rgb = ACCENT_RGB[orbState] || ACCENT_RGB.idle
    document.documentElement.style.setProperty('--accent-rgb', rgb)
    document.documentElement.style.setProperty('--accent', `rgb(${rgb})`)
  }, [orbState])

  // Initialize panel positions based on viewport
  useEffect(() => {
    const W = window.innerWidth, H = window.innerHeight
    setPanels({
      hive:    { open: false, x: 28, y: 96, z: 1 },
      sandbox: { open: false, x: Math.max(28, W - 458), y: 96, z: 1 },
      stream:  { open: false, x: Math.max(28, Math.round((W - 560) / 2)), y: Math.max(120, H - 430), z: 1 },
    })
  }, [])

  const togglePanel = useCallback((id) => {
    setPanels(prev => ({
      ...prev,
      [id]: { ...prev[id], open: !prev[id].open, z: ++zRef.current },
    }))
  }, [])

  const closeFloatPanel = useCallback((id) => {
    setPanels(prev => ({ ...prev, [id]: { ...prev[id], open: false } }))
  }, [])

  const focusPanel = useCallback((id) => {
    setPanels(prev => ({ ...prev, [id]: { ...prev[id], z: ++zRef.current } }))
  }, [])

  const dragPanel = useCallback((id, x, y) => {
    setPanels(prev => ({ ...prev, [id]: { ...prev[id], x, y } }))
  }, [])

  const minimizeAll = useCallback(() => {
    setPanels(prev => {
      const n = {}
      for (const k in prev) n[k] = { ...prev[k], open: false }
      return n
    })
  }, [])

  const openLocalPanel = (p) => setLocalPanel(p)
  const handleClose = () => { closePanel(); setLocalPanel(null) }
  const panel = activePanel ?? localPanel

  const handleSend = () => {
    const text = input.trim()
    if (!text) return
    sendMessage(text)
    setInput('')
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleVoiceToggle = async () => {
    const text = await toggleVoice()
    if (text && text.trim()) {
      setInput(text.trim())
      // Auto-send after voice transcription
      sendMessage(text.trim())
      setInput('')
    }
  }

  // TTS: speak Dela's reply when it completes (only if voice enabled)
  const lastReplyRef = useRef('')
  useEffect(() => {
    if (voiceEnabled && orbState === 'idle' && conversation.length > 0) {
      const lastMsg = conversation[conversation.length - 1]
      if (lastMsg.role === 'assistant' && lastMsg.content && lastMsg.content !== lastReplyRef.current) {
        lastReplyRef.current = lastMsg.content
        ttsSpeak(lastMsg.content)
      }
    }
  }, [orbState, conversation, voiceEnabled, ttsSpeak])

  // Stop TTS when state changes to thinking (barge-in)
  useEffect(() => {
    if (orbState === 'thinking' && ttsSpeaking) {
      ttsStop()
    }
  }, [orbState, ttsSpeaking, ttsStop])

  const isIdle = orbState === 'idle'
  const isSpeaking = orbState === 'speaking'
  const caption = currentStream || (toolStatus || '')

  return (
    <div className="app">
      {/* Grid overlay */}
      <div className="grid-overlay" />

      {/* Particle canvas (galaxy engine) */}
      <ParticleCanvas state={orbState} speaking={isSpeaking} />

      {/* Corner brackets */}
      <div className="corner-bracket tl" />
      <div className="corner-bracket tr" />
      <div className="corner-bracket bl" />
      <div className="corner-bracket br" />

      {/* Top strip */}
      <TopStrip
        state={orbState}
        cost={cost}
        noticeCount={noticeCount}
        connected={connected}
        input={input}
        setInput={setInput}
        onSend={handleSend}
      />

      {/* Data panel buttons (right side of top strip area — small buttons) */}
      <div style={{ position: 'absolute', top: 14, right: 24, zIndex: 7, display: 'flex', gap: 3, flexWrap: 'wrap', justifyContent: 'flex-end', maxWidth: 320 }}>
        <button className="data-btn" onClick={() => openLocalPanel('analytics')}>ANALYTICS</button>
        <button className="data-btn" onClick={() => openLocalPanel('tools')}>TOOLS</button>
        <button className="data-btn" onClick={() => openLocalPanel('notices')}>NOTICES{noticeCount > 0 ? ` (${noticeCount})` : ''}</button>
        <button className="data-btn" onClick={() => openLocalPanel('settings')}>SETTINGS</button>
        <button className="data-btn" onClick={() => openLocalPanel('security')}>SECURITY</button>
        <button className="data-btn" onClick={() => openLocalPanel('memory')}>MEMORY</button>
        <button className="data-btn" onClick={() => openLocalPanel('state')}>STATE</button>
        <button className="data-btn" onClick={() => openLocalPanel('audit')}>AUDIT</button>
        <button className="data-btn" onClick={() => openLocalPanel('tasks')}>TASKS</button>
      </div>

      {/* Idle view */}
      {isIdle && (
        <div className="idle-view">
          {IDLE_STATS.map((s, i) => {
            let value = s.value, sub = s.sub, statColor = null
            if (s.key === 'heartbeat') {
              value = heartbeatActive ? 'ACTIVE' : 'PAUSED'
              statColor = heartbeatActive ? 'var(--green)' : 'var(--text-dim)'
            } else if (s.key === 'uplink' && uplink) {
              if (uplink.status === 'connected') {
                value = 'LINKED'
                sub = uplink.model || ''
                statColor = 'var(--green)'
              } else if (uplink.status === 'auth_error') {
                value = 'AUTH FAIL'
                sub = uplink.error?.slice(0, 20) || 'check API key'
                statColor = 'var(--red)'
              } else if (uplink.status === 'unreachable') {
                value = 'OFFLINE'
                sub = 'no connection'
                statColor = 'var(--amber)'
              } else {
                value = 'ERROR'
                sub = uplink.error?.slice(0, 20) || 'unknown'
                statColor = 'var(--amber)'
              }
            } else if (s.key === 'agents') {
              value = String(agentInfo.count)
              sub = agentInfo.ready === agentInfo.count ? 'ready' : `${agentInfo.ready} ready`
              statColor = agentInfo.ready === agentInfo.count ? 'var(--green)' : 'var(--amber)'
            } else if (s.key === 'tools') {
              value = String(toolCount)
            }
            return (
              <div key={i} className="idle-corner-stat" style={s.pos}>
                <div className="label">{s.label}</div>
                <div className="value" style={statColor ? { color: statColor } : undefined}>
                  {value}
                  {sub && <span style={{ color: 'var(--text-dim)', fontSize: 11 }}> {sub}</span>}
                </div>
                {s.key === 'uplink' && uplink && uplink.latency_ms != null && (
                  <div style={{ font: "500 9px 'JetBrains Mono', monospace", color: 'var(--text-dim)', marginTop: 2 }}>
                    {uplink.latency_ms}ms · {uplink.profile}
                  </div>
                )}
              </div>
            )
          })}
          <div className="idle-center">
            <div>
              <div className="idle-logo">DELA</div>
              <div className="idle-subtitle">all systems nominal — awaiting your directive</div>
            </div>
            <div className="idle-input-wrap">
              <span className="idle-input-prompt">&gt;</span>
              <input
                className="idle-input"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Issue a directive — natural language or /command..."
                autoFocus
              />
              <button
                className={`mic-btn ${recording ? 'recording' : ''} ${transcribing ? 'transcribing' : ''}`}
                onClick={handleVoiceToggle}
                title={recording ? 'Stop and transcribe' : 'Start voice input'}
              >
                {transcribing ? '...' : recording ? 'STOP' : 'MIC'}
              </button>
              <button className="execute-btn" onClick={handleSend}>EXECUTE</button>
            </div>
            {voiceError && (
              <div style={{ font: "500 11px 'JetBrains Mono', monospace", color: 'var(--red)' }}>
                Voice error: {voiceError}
              </div>
            )}
            <div className="chip-row">
              <button className="chip" onClick={() => { sendMessage('What can you do?'); setInput('') }}>What can you do?</button>
              <button className="chip" onClick={() => { sendMessage('Search your memory for facts about me'); setInput('') }}>Search memory</button>
              <button className="chip" onClick={() => openLocalPanel('analytics')}>Analytics</button>
              <button
                className={`chip ${voiceEnabled ? 'active' : ''}`}
                onClick={() => {
                  const next = !voiceEnabled
                  setVoiceEnabled(next)
                  if (!next) ttsStop()
                }}
              >
                {voiceEnabled ? 'VOICE ON' : 'VOICE OFF'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Voice HUD */}
      <VoiceHud speaking={isSpeaking || ttsSpeaking} caption={caption} recording={recording} transcribing={transcribing} />

      {/* Conversation overlay (when not idle) */}
      {!isIdle && (conversation.length > 0 || currentStream || toolStatus) && (
        <div className="conv-overlay">
          {conversation.slice(-6).map(msg => (
            <div key={msg.id} className={`conv-msg ${msg.role}`}>
              {msg.content.slice(0, 200)}{msg.content.length > 200 ? '...' : ''}
            </div>
          ))}
          {currentStream && (
            <div className="conv-msg streaming">
              {currentStream.slice(0, 200)}{currentStream.length > 200 ? '...' : ''}
              <span style={{ animation: 'jblink 1s steps(1) infinite', color: 'var(--accent)' }}>▍</span>
            </div>
          )}
          {toolStatus && (
            <div className="conv-msg tool-blip">{toolStatus}</div>
          )}
        </div>
      )}

      {/* Dock */}
      {!isIdle && (
        <Dock
          state={orbState}
          panels={panels}
          onToggle={togglePanel}
          onMinimize={minimizeAll}
          heartbeatActive={heartbeatActive}
          onToggleHeartbeat={heartbeatActive ? killHeartbeat : resumeHeartbeat}
          noticeCount={noticeCount}
          onOpenNotices={() => openLocalPanel('notices')}
        />
      )}

      {/* Floating windows */}
      {panels.hive.open && (
        <HiveWindow
          panel={panels.hive}
          onClose={() => closeFloatPanel('hive')}
          onFocus={() => focusPanel('hive')}
          onDragMove={(x, y) => dragPanel('hive', x, y)}
          systemState={orbState}
        />
      )}
      {panels.stream.open && (
        <StreamWindow
          panel={panels.stream}
          onClose={() => closeFloatPanel('stream')}
          onFocus={() => focusPanel('stream')}
          onDragMove={(x, y) => dragPanel('stream', x, y)}
          conversation={conversation}
          currentStream={currentStream}
          toolStatus={toolStatus}
          systemState={orbState}
        />
      )}
      {panels.sandbox.open && (
        <SandboxWindow
          panel={panels.sandbox}
          onClose={() => closeFloatPanel('sandbox')}
          onFocus={() => focusPanel('sandbox')}
          onDragMove={(x, y) => dragPanel('sandbox', x, y)}
          toolStatus={toolStatus}
          conversation={conversation}
        />
      )}

      {/* Slide-in data panels (each panel wraps itself in HoloPanel) */}
      <AnimatePresence>
        {panel === 'memory' && (
          <MemoryPanel key="memory" onClose={handleClose} message={panelMessage} />
        )}
        {panel === 'state' && (
          <StateBrowserPanel key="state" onClose={handleClose} message={panelMessage} />
        )}
        {panel === 'tools' && (
          <ToolBrowserPanel key="tools" onClose={handleClose} message={panelMessage} />
        )}
        {panel === 'audit' && (
          <AuditPanel key="audit" onClose={handleClose} message={panelMessage} />
        )}
        {panel === 'notices' && (
          <NoticesPanel
            key="notices"
            onClose={handleClose}
            message={panelMessage}
            notices={notices}
            onDismiss={dismissNotice}
          />
        )}
        {panel === 'tasks' && (
          <TasksPanel key="tasks" onClose={handleClose} message={panelMessage} />
        )}
        {panel === 'security' && (
          <SecurityPanel key="security" onClose={handleClose} message={panelMessage} />
        )}
        {panel === 'settings' && (
          <SettingsPanel key="settings" onClose={handleClose} message={panelMessage} />
        )}
        {panel === 'analytics' && (
          <AnalyticsPanel key="analytics" onClose={handleClose} message={panelMessage} />
        )}
      </AnimatePresence>

      {/* HITL gate */}
      <HitlGate
        request={confirmRequest}
        onApprove={() => sendConfirm(confirmRequest.id, true)}
        onDeny={() => sendConfirm(confirmRequest.id, false)}
      />

      {/* Connection banner */}
      {!connected && (
        <div className="conn-banner">Connecting to Dela...</div>
      )}
    </div>
  )
}
