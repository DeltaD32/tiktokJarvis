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
import { ProjectsPanel }        from './components/panels/ProjectsPanel'
import { SecurityPanel }        from './components/panels/SecurityPanel'
import { SettingsPanel }        from './components/panels/SettingsPanel'
import { AnalyticsPanel }       from './components/panels/AnalyticsPanel'
import { WorkflowDesignerPanel } from './components/panels/WorkflowDesignerPanel'
import { AgentRosterPanel }    from './components/panels/AgentRosterPanel'
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
    killHeartbeat, resumeHeartbeat, agentStatus,
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
  const [voiceEnabled, setVoiceEnabled] = useState(true)

  // Voice
  const { recording, transcribing, error: voiceError, toggle: toggleVoice, clearError: clearVoiceError } = useVoiceRecorder()
  const { speaking: ttsSpeaking, speak: ttsSpeak, stop: ttsStop } = useVoiceTTS()

  // Initialize theme on mount + clear stale voice error
  useEffect(() => {
    applyTheme(getCurrentTheme())
    clearVoiceError()
  }, [])

  // Re-focus idle input when transitioning back to idle
  useEffect(() => {
    if (orbState === 'idle') {
      document.getElementById('idle-input')?.focus()
    }
  }, [orbState])

  // Fetch uplink status + agent/tool counts on mount and periodically
  const fetchControllerRef = useRef(null)

  const fetchWithAbort = useCallback((url, onOk, onErr) => {
    const controller = new AbortController()
    // Abort any in-flight request before starting a new one
    if (fetchControllerRef.current) fetchControllerRef.current.abort()
    fetchControllerRef.current = controller
    fetch(url, { signal: controller.signal })
      .then(r => r.json())
      .then(onOk)
      .catch(err => {
        if (err.name !== 'AbortError') onErr?.()
      })
  }, [])

  const fetchUplink = useCallback(() => {
    fetchWithAbort('/api/uplink', setUplink, () => setUplink({ status: 'unreachable' }))
  }, [fetchWithAbort])

  const fetchAgentInfo = useCallback(() => {
    fetchWithAbort('/api/agents', (data) => {
      const agents = data || []
      const ready = agents.filter(a => a.status === 'ready').length
      setAgentInfo({ count: agents.length, ready, agents })
    })
  }, [fetchWithAbort])

  const fetchToolCount = useCallback(() => {
    fetchWithAbort('/api/tools', (data) => setToolCount(data?.length || 46))
  }, [fetchWithAbort])

  useEffect(() => {
    fetchUplink()
    fetchAgentInfo()
    fetchToolCount()
    const interval = setInterval(() => {
      fetchUplink()
      fetchAgentInfo()
    }, 15000)
    return () => {
      clearInterval(interval)
      if (fetchControllerRef.current) fetchControllerRef.current.abort()
    }
  }, [fetchUplink, fetchAgentInfo, fetchToolCount])

  // Update CSS accent variables when state or theme changes
  useEffect(() => {
    const varName = `--${orbState}-rgb`
    const rgb =
      getComputedStyle(document.documentElement).getPropertyValue(varName).trim() ||
      getComputedStyle(document.documentElement).getPropertyValue('--idle-rgb').trim()
    if (rgb) {
      document.documentElement.style.setProperty('--accent-rgb', rgb)
      document.documentElement.style.setProperty('--accent', `rgb(${rgb})`)
    }
  }, [orbState])

  // Re-apply accent when theme changes (from Settings panel)
  useEffect(() => {
    const syncAccent = () => {
      const style = getComputedStyle(document.documentElement)
      const rgb =
        style.getPropertyValue(`--${orbState}-rgb`).trim() ||
        style.getPropertyValue('--idle-rgb').trim()
      if (rgb) {
        document.documentElement.style.setProperty('--accent-rgb', rgb)
        document.documentElement.style.setProperty('--accent', `rgb(${rgb})`)
      }
    }
    window.addEventListener('dela-theme-changed', syncAccent)
    return () => window.removeEventListener('dela-theme-changed', syncAccent)
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

  const openLocalPanel = useCallback((p) => setLocalPanel(p), [])
  const handleClose = useCallback(() => { closePanel(); setLocalPanel(null) }, [closePanel])
  const panel = activePanel ?? localPanel

  const handleSend = useCallback(() => {
    const text = input.trim()
    if (!text) return
    sendMessage(text)
    setInput('')
  }, [input, sendMessage])

  const handleKey = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }, [handleSend])

  const handleVoiceToggle = useCallback(async () => {
    if (recording) {
      const text = await toggleVoice()
      console.log('[voice] STT result:', JSON.stringify(text))
      if (text && text.trim()) {
        setInput(text.trim())
        sendMessage(text.trim())
        setInput('')
      } else {
        console.log('[voice] empty/error — not sending')
      }
    } else {
      toggleVoice()
    }
  }, [recording, toggleVoice, sendMessage])

  // TTS: speak Dela's reply when a new assistant message arrives (only if voice enabled)
  const lastReplyRef = useRef('')
  useEffect(() => {
    if (!voiceEnabled || conversation.length === 0) return
    const lastMsg = conversation[conversation.length - 1]
    if (lastMsg.role === 'assistant' && lastMsg.content && lastMsg.content !== lastReplyRef.current) {
      lastReplyRef.current = lastMsg.content
      ttsSpeak(lastMsg.content)
    }
  }, [conversation, voiceEnabled, ttsSpeak])

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

      {/* Top strip — only when not idle (idle view has its own input + logo) */}
      {!isIdle && (
        <TopStrip
          state={orbState}
          cost={cost}
          noticeCount={noticeCount}
          connected={connected}
          input={input}
          setInput={setInput}
          onSend={handleSend}
        />
      )}

      {/* Skip navigation link for keyboard users */}
      <a href="#idle-input" className="skip-link">Skip to input</a>

      {/* Data panel buttons — right side, below top strip when active */}
      <div style={{ position: 'absolute', top: isIdle ? 14 : 50, right: 24, zIndex: 7, display: 'flex', gap: 3, flexWrap: 'wrap', justifyContent: 'flex-end', maxWidth: 320 }}>
        {[
          ['analytics', 'ANALYTICS'],
          ['tools', 'TOOLS'],
          ['workflows', 'WORKFLOWS'],
          ['notices', 'NOTICES' + (noticeCount > 0 ? ' (' + noticeCount + ')' : '')],
          ['agents', 'AGENTS'],
          ['settings', 'SETTINGS'],
          ['security', 'SECURITY'],
          ['memory', 'MEMORY'],
          ['state', 'STATE'],
          ['audit', 'AUDIT'],
          ['projects', 'PROJECTS'],
        ].map(([panel, label]) => (
          <button key={panel} className="data-btn" onClick={() => openLocalPanel(panel)} aria-label={`Open ${label} panel`}>
            {label}
          </button>
        ))}
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
                id="idle-input"
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
                aria-label={recording ? 'Stop recording' : transcribing ? 'Transcribing...' : 'Start voice input'}
              >
                {transcribing ? '...' : recording ? 'STOP' : 'MIC'}
              </button>
              <button type="button" className="execute-btn" onClick={handleSend}>EXECUTE</button>
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
            {/* Agent status summary — click AGENTS button for full roster */}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 4 }}>
              {agentInfo.agents && agentInfo.agents.slice(0, 5).map(a => {
                const live = agentStatus[a.name]
                const status = live?.state || a.status
                return (
                  <span key={a.name} style={{ fontSize: 9, color: status === 'busy' ? 'var(--amber)' : status === 'ready' ? 'var(--text-dim)' : 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: 3 }}>
                    <span style={{ width: 5, height: 5, borderRadius: '50%', display: 'inline-block', background: status === 'busy' ? 'var(--amber)' : status === 'ready' ? 'var(--green)' : 'var(--text-faint)' }} />
                    {a.name}
                  </span>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Voice HUD — only during actual audio (recording, transcribing, TTS playback), not during text streaming */}
      <VoiceHud speaking={ttsSpeaking} caption={caption} recording={recording} transcribing={transcribing} />

      {/* Conversation overlay — minimal, full details in Stream panel */}
      {!isIdle && (conversation.length > 0 || currentStream || toolStatus) && (
        <div className="conv-overlay">
          {conversation.slice(-8).map(msg => (
            <div
              key={msg.id}
              className={`conv-msg ${msg.role}`}
              title="Click or press Enter to copy"
              tabIndex={0}
              role="button"
              style={{ cursor: 'pointer', wordBreak: 'break-all', overflowWrap: 'break-word' }}
              onClick={() => {
                navigator.clipboard.writeText(msg.content).catch(() => {
                  const ta = document.createElement('textarea')
                  ta.value = msg.content
                  ta.style.position = 'fixed'; ta.style.opacity = '0'
                  document.body.appendChild(ta)
                  ta.select()
                  try { document.execCommand('copy') } catch (_) {}
                  document.body.removeChild(ta)
                })
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  navigator.clipboard.writeText(msg.content).catch(() => {
                    const ta = document.createElement('textarea')
                    ta.value = msg.content
                    ta.style.position = 'fixed'; ta.style.opacity = '0'
                    document.body.appendChild(ta)
                    ta.select()
                    try { document.execCommand('copy') } catch (_) {}
                    document.body.removeChild(ta)
                  })
                }
              }}
            >
              <span className="conv-role-tag">{msg.role === 'user' ? 'YOU' : 'DELA'}</span>
              {msg.content.slice(0, 60)}{msg.content.length > 60 ? '…' : ''}
            </div>
          ))}
          {currentStream && (
            <div className="conv-msg streaming" style={{ wordBreak: 'break-all', overflowWrap: 'break-word' }}>
              <span className="conv-role-tag" style={{ color: 'var(--accent)' }}>DELA</span>
              {currentStream.slice(0, 60)}{currentStream.length > 60 ? '…' : ''}
              <span style={{ animation: 'jblink 1s steps(1) infinite', color: 'var(--accent)' }}>▍</span>
            </div>
          )}
          {toolStatus && (
            <div className="conv-msg tool-blip" style={{ wordBreak: 'break-all' }}>
              <span className="conv-role-tag" style={{ color: 'var(--amber)' }}>TOOL</span>
              {toolStatus}
            </div>
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
        {panel === 'agents' && (
          <AgentRosterPanel key="agents" onClose={handleClose} message={panelMessage} />
        )}
        {panel === 'projects' && (
          <ProjectsPanel key="projects" onClose={handleClose} message={panelMessage} />
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
        {panel === 'workflows' && (
          <WorkflowDesignerPanel key="workflows" onClose={handleClose} message={panelMessage} />
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
