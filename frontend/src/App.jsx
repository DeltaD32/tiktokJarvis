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
import { RichMessage }         from './components/RichMessage'
import { SubAgentOverlay }     from './components/SubAgentOverlay'
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
  const [idleExpanded, setIdleExpanded] = useState(false)

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

    // Slash commands
    if (text.startsWith('/')) {
      const [cmd, ...args] = text.slice(1).split(/\s+/)
      const arg = args.join(' ')
      switch (cmd) {
        case 'help':
          sendMessage('List all available slash commands and briefly explain each.')
          break
        case 'clear':
          window.location.reload()
          return
        case 'voice':
          if (arg === 'on') { setVoiceEnabled(true); break }
          if (arg === 'off') { setVoiceEnabled(false); ttsStop(); break }
          setVoiceEnabled(!voiceEnabled)
          if (voiceEnabled) ttsStop()
          break
        case 'theme': {
          const themes = ['jarvis','ultraviolet','solar','forest','crimson']
          if (themes.includes(arg.toLowerCase())) { applyTheme(arg.toLowerCase()) }
          else sendMessage(`Switch to the ${arg || 'jarvis'} theme.`)
          break
        }
        case 'memory': openLocalPanel('memory'); break
        case 'agents': openLocalPanel('agents'); break
        case 'settings': openLocalPanel('settings'); break
        case 'scan': sendMessage('Run a security scan and report findings.'); break
        case 'tasks': openLocalPanel('projects'); break
        case 'cost': sendMessage('What is the current session cost?'); break
        default:
          sendMessage(text)
      }
      setInput('')
      return
    }

    sendMessage(text)
    setInput('')
  }, [input, sendMessage, voiceEnabled, ttsStop])

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

  // Don't transition to idle while TTS is still speaking
  const isIdle = orbState === 'idle' && !ttsSpeaking
  const isSpeaking = orbState === 'speaking' || (ttsSpeaking && orbState !== 'thinking')
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

      {/* Top strip — smooth transition between idle and conversation */}
      <div style={{ opacity: isIdle ? 0 : 1, transform: isIdle ? 'translateY(-8px)' : 'translateY(0)', transition: 'opacity 0.35s cubic-bezier(0.22, 1, 0.36, 1), transform 0.35s cubic-bezier(0.22, 1, 0.36, 1)', pointerEvents: isIdle ? 'none' : 'auto' }}>
        <TopStrip
          state={orbState}
          cost={cost}
          noticeCount={noticeCount}
          connected={connected}
          input={input}
          setInput={setInput}
          onSend={handleSend}
          voiceEnabled={voiceEnabled}
          onToggleVoice={() => {
            const next = !voiceEnabled
            setVoiceEnabled(next)
            if (!next) ttsStop()
          }}
        />
      </div>

      {/* Skip navigation link for keyboard users */}
      <a href="#idle-input" className="skip-link">Skip to input</a>

      {/* Data panel buttons — floating icons, no boxes */}
      <div style={{ position: 'absolute', top: isIdle ? 14 : 50, right: 24, zIndex: 7, display: 'flex', gap: 2, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
        <button className="float-btn" onClick={() => openLocalPanel('analytics')} title="Analytics">📊</button>
        <button className="float-btn" onClick={() => openLocalPanel('audit')} title="Audit">📋</button>
        <button className="float-btn" onClick={() => openLocalPanel('notices')} title={noticeCount > 0 ? `${noticeCount} notices` : 'Notices'}>{noticeCount > 0 ? '🔔' : '🔕'}</button>
        <button className="float-btn" onClick={() => openLocalPanel('security')} title="Security">🛡️</button>
        <span style={{ width: 8 }} />
        <button className="float-btn" onClick={() => openLocalPanel('memory')} title="Memory">🧠</button>
        <button className="float-btn" onClick={() => openLocalPanel('state')} title="State">🗂️</button>
        <button className="float-btn" onClick={() => openLocalPanel('projects')} title="Projects">📁</button>
        <button className="float-btn" onClick={() => openLocalPanel('workflows')} title="Workflows">⚙️</button>
        <span style={{ width: 8 }} />
        <button className="float-btn" onClick={() => openLocalPanel('agents')} title="Agents">🤖</button>
        <button className="float-btn" onClick={() => openLocalPanel('tools')} title="Tools">🔧</button>
        <button className="float-btn" onClick={() => openLocalPanel('settings')} title="Settings">⚡</button>
      </div>

      {/* Idle view */}
      {isIdle && (
        <div className="idle-view">
          <div className="idle-center">
            <div className={`idle-chat-panel${idleExpanded ? ' expanded' : ''}`}>
              <div className="idle-logo">DELA</div>
              <div className="idle-bar-collapsed">
                <button className="idle-icon-btn" onClick={() => setIdleExpanded(true)} title="Chat">
                  💬
                </button>
                <button
                  className={`idle-icon-btn ${recording ? 'recording' : ''} ${transcribing ? 'transcribing' : ''}`}
                  onClick={handleVoiceToggle}
                  title={recording ? 'Stop' : 'Voice'}
                >
                  {transcribing ? '···' : recording ? '⏹' : '🎤'}
                </button>
                <span
                  className={`idle-hb ${heartbeatActive ? 'active' : ''}`}
                  title={heartbeatActive ? 'Heartbeat active' : 'Heartbeat paused'}
                />
              </div>
              <div className="idle-bar-expanded">
                <div className="idle-subtitle">all systems nominal</div>
                <div className="idle-input-wrap" style={{ padding: '8px 12px' }}>
                  <span className="idle-input-prompt" style={{ fontSize: 14 }}>&gt;</span>
                  <input
                    id="idle-input"
                    className="idle-input"
                    style={{ fontSize: 13, padding: '4px 0' }}
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={handleKey}
                    placeholder="Message or /command..."
                    autoFocus
                  />
                  <button
                    className={`mic-btn ${recording ? 'recording' : ''} ${transcribing ? 'transcribing' : ''}`}
                    onClick={handleVoiceToggle}
                    aria-label={recording ? 'Stop recording' : transcribing ? 'Transcribing...' : 'Start voice input'}
                    style={{ fontSize: 14, padding: '4px 8px', minWidth: 28 }}
                  >
                    {transcribing ? '···' : recording ? '⏹' : '🎤'}
                  </button>
                  <button type="button" className="exec-btn-sm" onClick={handleSend}>↵</button>
                  <button className="idle-collapse-btn" onClick={() => setIdleExpanded(false)} title="Collapse">×</button>
                </div>
                {voiceError && (
                  <div style={{ font: "500 11px 'JetBrains Mono', monospace", color: 'var(--red)', marginTop: 4, textAlign: 'center' }}>
                    {voiceError}
                  </div>
                )}
                <div className="idle-extras">
                  <div className="chip-row">
                    <button className="chip" onClick={() => { sendMessage('What can you do?'); setInput('') }}>What can you do?</button>
                    <button className="chip" onClick={() => { sendMessage('Search memory'); setInput('') }}>Search memory</button>
                    <button className="chip" onClick={() => openLocalPanel('analytics')}>Analytics</button>
                    <button
                      className={`chip ${voiceEnabled ? 'active' : ''}`}
                      onClick={() => { const next = !voiceEnabled; setVoiceEnabled(next); if (!next) ttsStop() }}
                    >
                      {voiceEnabled ? '🔊 ON' : '🔇'}
                    </button>
                  </div>
                  <div style={{ fontSize: 8, color: 'var(--text-faint)', textAlign: 'center', marginTop: 4, fontFamily: "'JetBrains Mono', monospace", opacity: 0.4 }}>
                    /help /clear /voice /theme /memory /agents /scan
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sub-agent activity overlay */}
      <SubAgentOverlay agentStatus={agentStatus} toolStatus={toolStatus} orbState={orbState} />

      {/* Voice HUD */}
      <VoiceHud speaking={ttsSpeaking} caption={caption} recording={recording} transcribing={transcribing} />

      {/* Conversation overlay — smooth fade in/out */}
      <div className={`conv-overlay${!isIdle && (conversation.length > 0 || currentStream || toolStatus) ? ' visible' : ''}`}>
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

      {/* Dock — smooth transition */}
      <div style={{ opacity: isIdle ? 0 : 1, transform: isIdle ? 'translateY(12px)' : 'translateY(0)', transition: 'opacity 0.35s cubic-bezier(0.22, 1, 0.36, 1), transform 0.35s cubic-bezier(0.22, 1, 0.36, 1)', pointerEvents: isIdle ? 'none' : 'auto' }}>
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
      </div>

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
