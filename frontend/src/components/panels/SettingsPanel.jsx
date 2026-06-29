import { useState, useEffect } from 'react'
import { HoloPanel } from '../HoloPanel'
import { THEMES, applyTheme, getCurrentTheme } from '../../themes'

export function SettingsPanel({ onClose, message }) {
  const [settings, setSettings]   = useState(null)
  const [loading, setLoading]     = useState(true)
  const [section, setSection]     = useState('general')
  const [theme, setTheme]         = useState(getCurrentTheme())
  const [envKey, setEnvKey]       = useState('')
  const [envValue, setEnvValue]   = useState('')
  const [envMsg, setEnvMsg]       = useState('')

  const refresh = () => {
    fetch('/api/settings')
      .then(r => r.json())
      .then(data => { setSettings(data); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => { refresh() }, [])

  const selectTheme = (name) => {
    applyTheme(name)
    setTheme(name)
  }

  const updateHeartbeat = (key, value) => {
    fetch('/api/settings/heartbeat', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [key]: value }),
    }).then(() => refresh())
  }

  const updateEnv = () => {
    if (!envKey.trim() || !envKey.startsWith('DELA_')) {
      setEnvMsg('Key must start with DELA_')
      return
    }
    fetch('/api/settings/env', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: envKey, value: envValue }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.ok) {
          setEnvMsg('Saved. Restart required to take effect.')
          setEnvKey(''); setEnvValue('')
        } else {
          setEnvMsg(data.error || 'Failed to save.')
        }
      })
  }

  const sections = [
    { id: 'general',  label: 'GENERAL' },
    { id: 'voice',    label: 'VOICE' },
    { id: 'theme',    label: 'THEME' },
    { id: 'heartbeat', label: 'HEARTBEAT' },
    { id: 'env',      label: 'ENV VARS' },
  ]

  const Field = ({ label, value, hint }) => (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--text-dim)', marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-2)', fontFamily: "'JetBrains Mono', monospace" }}>
        {value}
      </div>
      {hint && <div style={{ fontSize: 10, color: 'var(--text-faint)', marginTop: 2 }}>{hint}</div>}
    </div>
  )

  return (
    <HoloPanel title="Settings" message={message} onClose={onClose}>
      {/* Section tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16, flexWrap: 'wrap' }}>
        {sections.map(s => (
          <button
            key={s.id}
            className={`sandbox-tab ${section === s.id ? 'active' : ''}`}
            onClick={() => setSection(s.id)}
            style={{ fontSize: 9 }}
          >
            {s.label}
          </button>
        ))}
      </div>

      {loading && <p className="panel-empty">Loading...</p>}

      {/* GENERAL */}
      {!loading && section === 'general' && settings && (
        <>
          <Field label="ASSISTANT NAME" value={settings.model.name} />
          <Field label="MODEL" value={settings.model.model} hint="Change via .env (DELA_MODEL) — requires restart" />
          <Field label="API ENDPOINT" value={settings.model.base_url} hint="Change via .env (DELA_BASE_URL) — requires restart" />
          <Field label="THINKING LEVEL" value={settings.model.thinking_level} hint="off/minimal/low/medium/high/xhigh" />
          <Field label="TRACING" value={settings.tracing.provider} />
          <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
            <Field label="TOOLS" value={`${settings.runtime.tools_count} registered`} />
            <Field label="AGENTS" value={`${settings.runtime.agents_count} registered`} />
            <Field label="PYTHON" value={settings.runtime.python_version} />
          </div>
        </>
      )}

      {/* VOICE */}
      {!loading && section === 'voice' && settings && (
        <>
          <Field label="WHISPER MODEL" value={settings.voice.whisper_model} hint="tiny.en / base.en / small.en / medium.en" />
          <Field label="WHISPER DEVICE" value={settings.voice.whisper_device} hint="cuda / cpu" />
          <Field label="WHISPER COMPUTE" value={settings.voice.whisper_compute} hint="float16 / int8 / float32" />
          <Field label="PIPER VOICE" value={settings.voice.piper_voice} />
          <Field label="VAD AGGRESSIVENESS" value={settings.voice.vad_aggressiveness} hint="0-3 (higher = more aggressive)" />
          <div style={{ marginTop: 16, padding: 12, borderRadius: 10, background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border)', fontSize: 11, color: 'var(--text-3)' }}>
            Voice settings are read from .env at startup. Use ENV VARS tab to change them (requires restart).
          </div>
        </>
      )}

      {/* THEME */}
      {section === 'theme' && (
        <>
          <div style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)', marginBottom: 12, fontFamily: "'JetBrains Mono', monospace" }}>
            COLOR THEME
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {Object.entries(THEMES).map(([key, t]) => (
              <div
                key={key}
                onClick={() => selectTheme(key)}
                style={{
                  cursor: 'pointer',
                  padding: 14,
                  borderRadius: 12,
                  border: theme === key ? '2px solid var(--accent)' : '1px solid var(--border)',
                  background: theme === key ? 'rgba(var(--accent-rgb), 0.05)' : 'rgba(0,0,0,0.2)',
                  transition: 'all 0.2s',
                }}
              >
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text)', marginBottom: 8, fontFamily: "'JetBrains Mono', monospace" }}>
                  {t.name}
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  {Object.entries(t.colors).map(([state, rgb]) => (
                    <div
                      key={state}
                      title={state}
                      style={{
                        width: 16, height: 16, borderRadius: '50%',
                        background: `rgb(${rgb})`,
                        boxShadow: `0 0 8px rgba(${rgb}, 0.5)`,
                      }}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 16, padding: 12, borderRadius: 10, background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border)', fontSize: 11, color: 'var(--text-3)' }}>
            Theme preference is saved to localStorage and persists across sessions. State colors: idle, thinking, busy, alert, complete.
          </div>
        </>
      )}

      {/* HEARTBEAT */}
      {!loading && section === 'heartbeat' && settings && settings.heartbeat && (
        <>
          <Field label="INTERVAL (seconds)" value={settings.heartbeat.interval || 3600} />
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--text-dim)', marginBottom: 4 }}>CHANGE INTERVAL</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                className="chat-input"
                type="number"
                style={{ width: 100 }}
                placeholder={settings.heartbeat.interval || 3600}
                id="hb-interval-input"
              />
              <button className="icon-btn" onClick={() => {
                const v = parseInt(document.getElementById('hb-interval-input').value)
                if (v > 0) updateHeartbeat('interval', v)
              }}>save</button>
            </div>
          </div>

          <div style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)', margin: '16px 0 8px', fontFamily: "'JetBrains Mono', monospace" }}>
            ENABLED CHECKS
          </div>
          {settings.heartbeat.checks && Object.entries(settings.heartbeat.checks).map(([name, cfg]) => (
            <div key={name} className="panel-item">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="panel-item-title" style={{ fontSize: 12 }}>{name}</span>
                <button
                  className={`badge ${cfg.enabled ? 'badge-done' : 'badge-open'}`}
                  onClick={() => updateHeartbeat('checks', { ...settings.heartbeat.checks, [name]: { ...cfg, enabled: !cfg.enabled } })}
                  style={{ cursor: 'pointer', border: 'none' }}
                >
                  {cfg.enabled ? 'ON' : 'OFF'}
                </button>
              </div>
            </div>
          ))}
        </>
      )}

      {/* ENV VARS */}
      {section === 'env' && (
        <>
          <div style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)', marginBottom: 12, fontFamily: "'JetBrains Mono', monospace" }}>
            UPDATE .ENV VARIABLE
          </div>
          <div style={{ marginBottom: 8 }}>
            <input
              className="chat-input"
              style={{ width: '100%', marginBottom: 8 }}
              value={envKey}
              onChange={e => setEnvKey(e.target.value)}
              placeholder="DELA_WHISPER_DEVICE"
            />
            <input
              className="chat-input"
              style={{ width: '100%', marginBottom: 8 }}
              value={envValue}
              onChange={e => setEnvValue(e.target.value)}
              placeholder="cpu"
            />
            <button className="icon-btn" onClick={updateEnv} style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }}>
              save (restart required)
            </button>
          </div>
          {envMsg && (
            <div style={{ marginTop: 8, fontSize: 11, color: envMsg.includes('Saved') ? 'var(--green)' : 'var(--red)' }}>
              {envMsg}
            </div>
          )}
          <div style={{ marginTop: 16, padding: 12, borderRadius: 10, background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border)', fontSize: 11, color: 'var(--text-3)' }}>
            Common variables: DELA_MODEL, DELA_WHISPER_DEVICE, DELA_WHISPER_MODEL, DELA_PIPER_VOICE, DELA_THINKING_LEVEL, DELA_COMPACTION_THRESHOLD_CHARS
          </div>
        </>
      )}
    </HoloPanel>
  )
}
