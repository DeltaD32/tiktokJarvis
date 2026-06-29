import { useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import { AnimatePresence } from 'framer-motion'

import { JarvisOrb }            from './components/JarvisOrb'
import { TopBar }               from './components/TopBar'
import { ConversationOverlay }  from './components/ConversationOverlay'
import { ConfirmationDialog }   from './components/ConfirmationDialog'
import { TasksPanel }           from './components/panels/TasksPanel'
import { NoticesPanel }         from './components/panels/NoticesPanel'
import { AuditPanel }           from './components/panels/AuditPanel'
import { MemoryPanel }          from './components/panels/MemoryPanel'
import { StateBrowserPanel }    from './components/panels/StateBrowserPanel'
import { ToolBrowserPanel }     from './components/panels/ToolBrowserPanel'
import { useDelaWS }            from './hooks/useDelaWS'

export default function App() {
  const {
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
  } = useDelaWS()

  const [input, setInput] = useState('')
  const [localPanel, setLocalPanel] = useState(null)

  const openPanel = (p) => {
    setLocalPanel(p)
  }

  const handleClose = () => {
    closePanel()
    setLocalPanel(null)
  }

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

  return (
    <div className="app">
      {/* Three.js canvas fills the background */}
      <div className="canvas-wrap">
        <Canvas
          camera={{ position: [0, 0, 6], fov: 45 }}
          gl={{ alpha: true, antialias: true }}
          style={{ background: 'transparent' }}
          dpr={Math.min(window.devicePixelRatio, 2)}
        >
          <JarvisOrb state={orbState} />
          <EffectComposer>
            <Bloom
              intensity={1.8}
              luminanceThreshold={0.04}
              luminanceSmoothing={0.88}
              height={512}
            />
          </EffectComposer>
        </Canvas>
      </div>

      {/* HUD corner decorations */}
      <div className="hud-corners">
        <div className="hud-corner tl" />
        <div className="hud-corner tr" />
        <div className="hud-corner bl" />
        <div className="hud-corner br" />
      </div>

      {/* Top bar */}
      <TopBar
        orbState={orbState}
        heartbeatActive={heartbeatActive}
        cost={cost}
        noticeCount={noticeCount}
        connected={connected}
        onKill={killHeartbeat}
        onResume={resumeHeartbeat}
        onOpenNotices={() => openPanel('notices')}
        onOpenAudit={() => openPanel('audit')}
        onOpenMemory={() => openPanel('memory')}
        onOpenState={() => openPanel('state')}
        onOpenTools={() => openPanel('tools')}
      />

      {/* Conversation overlay */}
      <ConversationOverlay
        conversation={conversation}
        currentStream={currentStream}
        toolStatus={toolStatus}
      />

      {/* Input bar */}
      <div className="input-row">
        <input
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Speak to Dela…"
          autoFocus
        />
        <button
          className="send-btn"
          onClick={handleSend}
          disabled={!input.trim() || orbState === 'thinking'}
        >
          ▶
        </button>
      </div>

      {/* Slide-in panels */}
      <AnimatePresence>
        {panel === 'tasks' && (
          <TasksPanel key="tasks" onClose={handleClose} message={panelMessage} />
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
        {panel === 'audit' && (
          <AuditPanel key="audit" onClose={handleClose} message={panelMessage} />
        )}
        {panel === 'memory' && (
          <MemoryPanel key="memory" onClose={handleClose} message={panelMessage} />
        )}
        {panel === 'state' && (
          <StateBrowserPanel key="state" onClose={handleClose} message={panelMessage} />
        )}
        {panel === 'tools' && (
          <ToolBrowserPanel key="tools" onClose={handleClose} message={panelMessage} />
        )}
      </AnimatePresence>

      {/* Confirmation dialog */}
      <AnimatePresence>
        {confirmRequest && (
          <ConfirmationDialog
            key="confirm"
            request={confirmRequest}
            onConfirm={() => sendConfirm(confirmRequest.id, true)}
            onDeny={() => sendConfirm(confirmRequest.id, false)}
          />
        )}
      </AnimatePresence>

      {/* Disconnection banner */}
      {!connected && (
        <div className="conn-banner">⚡ Connecting to Dela…</div>
      )}
    </div>
  )
}
