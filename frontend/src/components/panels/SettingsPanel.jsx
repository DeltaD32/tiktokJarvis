import { useState, useEffect } from 'react'
import { HoloPanel } from '../HoloPanel'
import { THEMES, applyTheme, getCurrentTheme } from '../../themes'

const ConnInput = ({ label, value, onChange, placeholder, type = 'text', secret = false }) => (
  <div style={{ marginBottom: 8 }}>
    <div style={{ fontSize: 9, letterSpacing: '0.1em', color: 'var(--text-dim)', marginBottom: 3 }}>{label}</div>
    <input
      className="chat-input"
      type={type}
      style={{ width: '100%', fontSize: 11, padding: '5px 8px' }}
      value={value || ''}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
    />
  </div>
)

function ConnEditor({ form, setForm, onSave, onCancel }) {
  const set = (k, v) => setForm({ ...form, [k]: v })
  const isOauth = form.auth_type === 'oauth'
  return (
    <div style={{ marginTop: 10, padding: 12, borderRadius: 10, border: '1px solid var(--border)', background: 'rgba(0,0,0,0.3)' }}>
      <ConnInput label="NAME *" value={form.name} placeholder="my-openai" onChange={v => set('name', v)} />
      <ConnInput label="BASE URL *" value={form.base_url} placeholder="https://api.openai.com/v1" onChange={v => set('base_url', v)} />
      <ConnInput label="DEFAULT MODEL" value={form.model} placeholder="gpt-4o" onChange={v => set('model', v)} />

      <div style={{ marginBottom: 8 }}>
        <div style={{ fontSize: 9, letterSpacing: '0.1em', color: 'var(--text-dim)', marginBottom: 3 }}>AUTH TYPE</div>
        <select
          className="chat-input"
          style={{ width: '100%', padding: '5px 8px', fontSize: 11 }}
          value={form.auth_type || 'simple'}
          onChange={e => set('auth_type', e.target.value)}
        >
          <option value="simple">API Key (bearer)</option>
          <option value="oauth">OAuth (client_id + secret → token)</option>
        </select>
      </div>

      {!isOauth && (
        <ConnInput label="API KEY" value={form.api_key} placeholder="sk-... (leave blank to keep existing)" onChange={v => set('api_key', v)} />
      )}

      {isOauth && (
        <>
          <ConnInput label="OAUTH CLIENT ID" value={form.oauth_client_id} placeholder="client-xxx" onChange={v => set('oauth_client_id', v)} />
          <ConnInput label="OAUTH CLIENT SECRET" value={form.oauth_client_secret} placeholder="secret-xxx (leave blank to keep)" secret onChange={v => set('oauth_client_secret', v)} />
          <ConnInput label="TOKEN URL" value={form.oauth_token_url} placeholder="https://.../oauth/token" onChange={v => set('oauth_token_url', v)} />
          <ConnInput label="SCOPES (optional)" value={form.oauth_scopes} placeholder="" onChange={v => set('oauth_scopes', v)} />
          <ConnInput label="CLIENT-ID HEADER NAME" value={form.oauth_header_name} placeholder="x-client-id" onChange={v => set('oauth_header_name', v)} />
          <div style={{ fontSize: 10, color: 'var(--text-faint)', marginBottom: 10, lineHeight: 1.4 }}>
            The token is sent as <code>Authorization: Bearer &lt;token&gt;</code>. The OAuth client_id is also sent in the header named above to the OpenAI-compatible endpoint. Token lifetime is capped at 7199s and auto-refreshed within 600s of expiry.
          </div>
        </>
      )}

      <div style={{ display: 'flex', gap: 8 }}>
        <button
          className="icon-btn"
          style={{ borderColor: 'var(--green)', color: 'var(--green)' }}
          onClick={() => { if (form.name?.trim() && form.base_url?.trim()) onSave() }}
        >save</button>
        {onCancel && <button className="icon-btn" onClick={onCancel}>cancel</button>}
      </div>
    </div>
  )
}

export function SettingsPanel({ onClose, message }) {
  const [settings, setSettings]   = useState(null)
  const [loading, setLoading]     = useState(true)
  const [section, setSection]     = useState('general')
  const [theme, setTheme]         = useState(getCurrentTheme())
  const [envKey, setEnvKey]       = useState('')
  const [envValue, setEnvValue]   = useState('')
  const [envMsg, setEnvMsg]       = useState('')
  const [profileMsg, setProfileMsg] = useState('')
  const [ollama, setOllama]       = useState(null)
  const [modelList, setModelList] = useState(null)
  const [saveMsg, setSaveMsg]     = useState('')

  // Connections state
  const [connections, setConnections] = useState(null)
  const [oauthStatus, setOauthStatus] = useState(null)
  const [editingConn, setEditingConn] = useState(null)
  const [connForm, setConnForm]       = useState({})
  const [connMsg, setConnMsg]         = useState('')
  const [connTest, setConnTest]       = useState(null)

  const refresh = () => {
    fetch('/api/settings')
      .then(r => r.json())
      .then(data => { setSettings(data); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => { refresh() }, [])
  useEffect(() => {
    if (section === 'profile') {
      fetch('/api/ollama/status').then(r => r.json()).then(d => setOllama(d)).catch(() => {})
    }
    if (section === 'general') {
      fetch('/api/models').then(r => r.json()).then(d => setModelList(d)).catch(() => {})
    }
    if (section === 'connections') {
      refreshConnections()
    }
  }, [section])

  const refreshConnections = () => {
    fetch('/api/connections').then(r => r.json()).then(d => setConnections(d)).catch(() => {})
    fetch('/api/oauth/status').then(r => r.json()).then(d => setOauthStatus(d)).catch(() => {})
  }

  const setLiveModel = (model) => {
    fetch('/api/settings/live', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: 'model', value: model }),
    }).then(() => {
      setSaveMsg(`Model set to ${model}. Takes effect on next call.`)
      setTimeout(() => setSaveMsg(''), 3000)
      refresh()
      fetch('/api/models').then(r => r.json()).then(d => setModelList(d)).catch(() => {})
    })
  }

  const resetLiveModel = () => {
    fetch('/api/settings/live/model', { method: 'DELETE' })
      .then(r => r.json())
      .then(() => {
        setSaveMsg('Model reset to connection default. Takes effect on next call.')
        setTimeout(() => setSaveMsg(''), 3000)
        refresh()
        fetch('/api/models').then(r => r.json()).then(d => setModelList(d)).catch(() => {})
      })
  }

  const selectTheme = (name) => {
    applyTheme(name)
    setTheme(name)
  }

  const switchProfile = (name) => {
    fetch('/api/settings/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile: name }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.ok) {
          setProfileMsg(`Profile set to ${name.toUpperCase()}. Restart Dela to apply.`)
          refresh()
        } else {
          setProfileMsg(data.error || 'Failed to switch profile.')
        }
      })
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
          setEnvMsg('Saved to .env. Restart required to take effect.')
          setEnvKey(''); setEnvValue('')
        } else {
          setEnvMsg(data.error || 'Failed to save.')
        }
      })
  }

  const updateLive = (key, value) => {
    fetch('/api/settings/live', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key, value }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.ok) { refresh() }
      })
  }

  const resetLive = (key) => {
    fetch(`/api/settings/live/${key}`, { method: 'DELETE' })
      .then(r => r.json())
      .then(data => { if (data.ok) refresh() })
  }

  const sections = [
    { id: 'profile',  label: 'PROFILE' },
    { id: 'general',  label: 'GENERAL' },
    { id: 'connections', label: 'CONNECTIONS' },
    { id: 'router',   label: 'ROUTER' },
    { id: 'voice',    label: 'VOICE' },
    { id: 'theme',    label: 'THEME' },
    { id: 'heartbeat', label: 'HEARTBEAT' },
    { id: 'env',      label: 'ENV VARS' },
  ]

  const LiveField = ({ label, settingKey, value, options, hint }) => (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--text-dim)' }}>{label}</span>
        <span style={{ fontSize: 8, color: 'var(--green)', padding: '1px 5px', border: '1px solid rgba(70,242,176,0.3)', borderRadius: 4 }}>LIVE</span>
      </div>
      {options ? (
        <select
          className="chat-input"
          style={{ width: '100%', padding: '6px 8px', fontSize: 12 }}
          value={value || ''}
          onChange={e => updateLive(settingKey, e.target.value)}
        >
          {options.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
        </select>
      ) : (
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            className="chat-input"
            style={{ flex: 1, fontSize: 12 }}
            value={value || ''}
            onChange={e => updateLive(settingKey, e.target.value)}
          />
          <button className="icon-btn" onClick={() => resetLive(settingKey)} style={{ fontSize: 9 }}>reset</button>
        </div>
      )}
      {hint && <div style={{ fontSize: 10, color: 'var(--text-faint)', marginTop: 2 }}>{hint}</div>}
    </div>
  )

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

      {/* PROFILE */}
      {!loading && section === 'profile' && settings && (
        <>
          <div style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)', marginBottom: 12, fontFamily: "'JetBrains Mono', monospace" }}>
            SECURITY PROFILE
          </div>
          {settings.profile?.available.map(p => {
            const isCurrent = p.name === settings.profile.current
            return (
              <div
                key={p.name}
                onClick={() => !isCurrent && switchProfile(p.name)}
                style={{
                  cursor: isCurrent ? 'default' : 'pointer',
                  padding: 14,
                  borderRadius: 12,
                  border: isCurrent ? '2px solid var(--accent)' : '1px solid var(--border)',
                  background: isCurrent ? 'rgba(var(--accent-rgb), 0.05)' : 'rgba(0,0,0,0.2)',
                  marginBottom: 10,
                  transition: 'all 0.2s',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', fontFamily: "'JetBrains Mono', monospace" }}>
                    {p.name.toUpperCase()}
                  </span>
                  {isCurrent && <span className="badge badge-done">ACTIVE</span>}
                  {!isCurrent && <span className="badge badge-open">CLICK TO SWITCH</span>}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-3)', lineHeight: 1.4 }}>
                  {p.description}
                </div>
                <div style={{ display: 'flex', gap: 12, marginTop: 10, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>
                    CORS: {p.cors_origins.length === 1 && p.cors_origins[0] === '*' ? 'wildcard' : `${p.cors_origins.length} origin(s)`}
                  </span>
                  <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>
                    Blocked tools: {p.tools_blocked.length}
                  </span>
                  <span style={{ fontSize: 10, color: p.injection_level === 'maximum' ? 'var(--green)' : 'var(--text-dim)' }}>
                    Injection: {p.injection_level}
                  </span>
                  {p.wiz_enabled && <span style={{ fontSize: 10, color: 'var(--green)' }}>WIZ: ON</span>}
                </div>
              </div>
            )
          })}
          {profileMsg && (
            <div style={{ marginTop: 8, padding: 10, borderRadius: 8, background: 'rgba(0,0,0,0.3)', border: '1px solid var(--accent)', fontSize: 11, color: 'var(--accent)' }}>
              {profileMsg}
            </div>
          )}
          {/* Profile-specific API connection */}
          <div style={{ marginTop: 16, fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)', marginBottom: 10, fontFamily: "'JetBrains Mono', monospace" }}>
            API CONNECTION — {settings.profile?.current?.toUpperCase()}
          </div>
          <div style={{ padding: 14, borderRadius: 12, border: '1px solid var(--border)', background: 'rgba(0,0,0,0.2)', marginBottom: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <span style={{ font: "600 11px 'JetBrains Mono', monospace", color: 'var(--text-2)' }}>
                {settings.model?.model || '—'}
              </span>
              <span style={{ font: "500 10px 'JetBrains Mono', monospace", color: 'var(--text-dim)' }}>
                {settings.model?.base_url || ''}
              </span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 8 }}>
              Set profile-specific API credentials in .env (requires restart):
            </div>
            <div style={{ font: "500 10px 'JetBrains Mono', monospace", color: 'var(--text-dim)', lineHeight: 1.8 }}>
              <div>DELA_{settings.profile?.current?.toUpperCase()}_BASE_URL</div>
              <div>DELA_{settings.profile?.current?.toUpperCase()}_API_KEY</div>
              <div>DELA_{settings.profile?.current?.toUpperCase()}_MODEL</div>
            </div>
          </div>
          <div style={{ padding: 12, borderRadius: 10, background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border)', fontSize: 11, color: 'var(--text-3)', lineHeight: 1.5 }}>
            <strong style={{ color: 'var(--text-2)' }}>Personal:</strong> Full tool access, standard security, localhost-only. Cloud or local API.<br/>
            <strong style={{ color: 'var(--text-2)' }}>Work:</strong> Restricted tools, maximum injection defense, WIZ integration, verbose audit.<br/>
            <strong style={{ color: 'var(--green)' }}>Offline:</strong> Fully local — Ollama LLM + local voice stack. No internet required. Blocks web-dependent tools.<br/>
            <span style={{ color: 'var(--amber)' }}>Switching profiles or API config requires a restart.</span>
          </div>

          {/* Ollama status */}
          {ollama && (
            <div style={{ marginTop: 12, padding: 14, borderRadius: 10, background: 'rgba(0,0,0,0.3)', border: `1px solid ${ollama.status === 'running' ? 'var(--green)' : 'var(--amber)'}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)', fontFamily: "'JetBrains Mono', monospace" }}>
                  OLLAMA STATUS
                </span>
                <span style={{
                  fontSize: 9, fontWeight: 700,
                  color: ollama.status === 'running' ? 'var(--green)' : 'var(--amber)',
                  fontFamily: "'JetBrains Mono', monospace",
                }}>
                  {ollama.status === 'running' ? '● RUNNING' : '○ NOT RUNNING'}
                </span>
              </div>
              {ollama.status === 'running' ? (
                <>
                  {ollama.models.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      {ollama.models.map(m => (
                        <div key={m.name} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-3)' }}>
                          <span style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--text-2)' }}>{m.name}</span>
                          <span style={{ color: 'var(--text-dim)' }}>{m.size_gb}GB</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ fontSize: 10, color: 'var(--amber)' }}>
                      No models pulled — run: <code style={{ color: 'var(--accent)' }}>ollama pull llama3.1</code>
                    </div>
                  )}
                  {ollama.model_count > 0 && settings.profile?.current !== 'offline' && (
                    <div style={{ marginTop: 8, fontSize: 10, color: 'var(--accent)' }}>
                      Switch to OFFLINE profile + set DELA_OFFLINE_MODEL to use Ollama
                    </div>
                  )}
                </>
              ) : (
                <div style={{ fontSize: 10, color: 'var(--text-dim)', lineHeight: 1.5 }}>
                  Install from <a href="https://ollama.com" target="_blank" style={{ color: 'var(--accent)' }}>ollama.com</a>, then:
                  <pre style={{ marginTop: 6, color: 'var(--text-2)', fontSize: 10 }}>ollama pull llama3.1{'\n'}ollama serve</pre>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* GENERAL */}
      {!loading && section === 'general' && settings && (
        <>
          <Field label="ASSISTANT NAME" value={settings.model.name} />

          {/* Live model selector — populated from the active connection */}
          {modelList && modelList.status === 'ok' ? (
            <div style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--text-dim)' }}>ACTIVE MODEL</span>
                <span style={{ fontSize: 8, color: 'var(--green)', padding: '1px 5px', border: '1px solid rgba(70,242,176,0.3)', borderRadius: 4 }}>LIVE</span>
              </div>
              <select
                className="chat-input"
                style={{ width: '100%', padding: '6px 8px', fontSize: 12 }}
                value={settings.live_overrides?.model && settings.live_overrides.model !== 'default'
                  ? settings.live_overrides.model : '__default__'}
                onChange={e => {
                  if (e.target.value === '__default__') resetLiveModel()
                  else setLiveModel(e.target.value)
                }}
              >
                {!settings.live_overrides?.model && <option value="__default__">— connection default ({modelList.current}) —</option>}
                {modelList.models.map(m => (
                  <option key={m} value={m}>{m}{m === modelList.current ? '  (default)' : ''}</option>
                ))}
              </select>
              <div style={{ fontSize: 10, color: 'var(--text-faint)', marginTop: 2 }}>
                {modelList.count} models on {modelList.connection || 'env'} · switch instantly, no restart
              </div>
              {saveMsg && (
                <div style={{ fontSize: 10, color: 'var(--green)', marginTop: 4 }}>{saveMsg}</div>
              )}
            </div>
          ) : (
            <Field
              label="MODEL"
              value={settings.model.model}
              hint={modelList?.status === 'error'
                ? `Could not list models: ${modelList?.error || ''} — set up a connection in the CONNECTIONS tab`
                : 'Listing models from active connection…'}
            />
          )}

          <Field label="API ENDPOINT" value={settings.model.base_url} hint="Manage via CONNECTIONS tab — assign a connection to this profile" />
          <LiveField
            label="THINKING LEVEL"
            settingKey="thinking_level"
            value={settings.live?.thinking_level || ''}
            options={[
              { value: '', label: '(off)' },
              { value: 'low', label: 'low' },
              { value: 'medium', label: 'medium' },
              { value: 'high', label: 'high' },
            ]}
            hint="Controls reasoning depth. Applied to next model call — no restart."
          />
          <Field label="TRACING" value={settings.tracing.provider} />
          <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
            <Field label="TOOLS" value={`${settings.runtime.tools_count} registered`} />
            <Field label="AGENTS" value={`${settings.runtime.agents_count} registered`} />
            <Field label="PYTHON" value={settings.runtime.python_version} />
          </div>
        </>
      )}

      {/* CONNECTIONS */}
      {!loading && section === 'connections' && (
        <>
          <div style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)', marginBottom: 8, fontFamily: "'JetBrains Mono', monospace" }}>
            API CONNECTIONS — assign one per profile (live, no restart)
          </div>

          {/* OAuth monitor status */}
          {oauthStatus && (
            <div style={{ marginBottom: 12, padding: 10, borderRadius: 10, background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border)', fontSize: 11 }}>
              <span style={{ color: oauthStatus.monitor_running ? 'var(--green)' : 'var(--amber)', fontFamily: "'JetBrains Mono', monospace", fontSize: 10 }}>
                {oauthStatus.monitor_running ? '● OAUTH MONITOR: RUNNING' : '○ OAUTH MONITOR: OFF'}
              </span>
              <span style={{ color: 'var(--text-dim)', marginLeft: 10, fontSize: 10 }}>
                auto-refresh margin: {oauthStatus.refresh_margin_s}s
                {Object.keys(oauthStatus.tokens || {}).length > 0 && ` · ${Object.keys(oauthStatus.tokens).length} oauth token(s)`}
              </span>
            </div>
          )}

          {/* Per-profile assignment matrix */}
          {settings?.profile?.available?.map(p => {
            const assigned = connections?.assignments?.[p.name]
            return (
              <div key={p.name} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8, padding: 10, borderRadius: 10, border: '1px solid var(--border)', background: 'rgba(0,0,0,0.2)' }}>
                <span style={{ font: "700 11px 'JetBrains Mono', monospace", color: p.name === settings.profile.current ? 'var(--accent)' : 'var(--text-2)', minWidth: 80 }}>
                  {p.name.toUpperCase()}
                </span>
                <select
                  className="chat-input"
                  style={{ flex: 1, padding: '5px 8px', fontSize: 11 }}
                  value={assigned || ''}
                  onChange={e => {
                    fetch('/api/connections/assign', {
                      method: 'PUT',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ profile: p.name, connection: e.target.value }),
                    }).then(() => {
                      refreshConnections(); refresh()
                      setConnMsg(`Assigned connection to ${p.name.toUpperCase()}. Next model call uses it — no restart.`)
                      setTimeout(() => setConnMsg(''), 3000)
                    })
                  }}
                >
                  <option value="">— env default —</option>
                  {(connections?.connections || []).map(c => (
                    <option key={c.name} value={c.name}>
                      {c.name} ({c.auth_type === 'oauth' ? 'OAuth' : 'api-key'})
                    </option>
                  ))}
                </select>
                {p.name === settings.profile.current && (
                  <span style={{ fontSize: 9, color: 'var(--accent)', fontFamily: "'JetBrains Mono', monospace" }}>ACTIVE PROFILE</span>
                )}
              </div>
            )
          })}

          {/* Connection list */}
          <div style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)', margin: '16px 0 8px', fontFamily: "'JetBrains Mono', monospace" }}>
            CONFIGURED CONNECTIONS
          </div>
          {(connections?.connections || []).length === 0 && !editingConn && (
            <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 10 }}>
              No connections configured. Using env defaults ({settings?.model?.base_url}). Click NEW CONNECTION to define one.
            </div>
          )}
          {(connections?.connections || []).map(c => {
            const isAssigned = connections?.assignments && Object.values(connections.assignments).includes(c.name)
            const tok = oauthStatus?.tokens?.[c.name]
            const isEditing = editingConn === c.name
            return (
              <div key={c.name} style={{ marginBottom: 8, padding: 12, borderRadius: 12, border: `1px solid ${isAssigned ? 'rgba(var(--accent-rgb),0.4)' : 'var(--border)'}`, background: isAssigned ? 'rgba(var(--accent-rgb),0.04)' : 'rgba(0,0,0,0.2)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 6 }}>
                  <span style={{ font: "600 12px 'JetBrains Mono', monospace", color: 'var(--text-2)' }}>
                    {c.name}
                    <span style={{ marginLeft: 8, fontSize: 9, color: c.auth_type === 'oauth' ? 'var(--amber)' : 'var(--text-dim)' }}>
                      {c.auth_type === 'oauth' ? 'OAUTH' : 'API-KEY'}
                    </span>
                  </span>
                  <div style={{ display: 'flex', gap: 4 }}>
                    {c.auth_type === 'oauth' && (
                      <button className="icon-btn" style={{ fontSize: 9 }} onClick={() => {
                        fetch('/api/oauth/refresh', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: c.name }) })
                          .then(r => r.json()).then(d => {
                            if (d.ok) setConnMsg(`Token refreshed — ${c.name}`)
                            else setConnMsg(`Refresh failed: ${d.error}`)
                            setTimeout(() => setConnMsg(''), 4000)
                            refreshConnections()
                          })
                      }}>refresh token</button>
                    )}
                    <button className="icon-btn" style={{ fontSize: 9 }} onClick={() => {
                      setConnTest(null)
                      fetch(`/api/connections/${encodeURIComponent(c.name)}/test`, { method: 'POST' })
                        .then(r => r.json()).then(d => setConnTest({ name: c.name, ...d }))
                    }}>test</button>
                    <button className="icon-btn" style={{ fontSize: 9 }} onClick={() => {
                      if (editingConn) { setEditingConn(null); setConnForm({}) }
                      else { setEditingConn(c.name); setConnForm({ ...c }) }
                    }}>{isEditing ? 'close' : 'edit'}</button>
                    <button className="icon-btn" style={{ fontSize: 9, color: 'var(--red)', borderColor: 'var(--red)' }} onClick={() => {
                      if (confirm(`Delete connection "${c.name}"?`)) {
                        fetch(`/api/connections/${encodeURIComponent(c.name)}`, { method: 'DELETE' })
                          .then(() => { refreshConnections(); refresh() })
                      }
                    }}>delete</button>
                  </div>
                </div>
                <div style={{ fontSize: 10, color: 'var(--text-dim)', fontFamily: "'JetBrains Mono', monospace", marginTop: 4 }}>
                  {c.base_url} · model: {c.model || '—'}
                </div>
                {c.auth_type === 'oauth' && tok && (
                  <div style={{ fontSize: 10, marginTop: 4, color: tok.status === 'valid' ? 'var(--green)' : tok.status === 'expiring' ? 'var(--amber)' : 'var(--red)' }}>
                    token: {tok.status}{tok.seconds_left > 0 ? ` · ${Math.floor(tok.seconds_left / 60)}m left` : ''}
                  </div>
                )}
                {connTest && connTest.name === c.name && (
                  <div style={{ marginTop: 6, fontSize: 10, color: connTest.ok ? 'var(--green)' : 'var(--red)', fontFamily: "'JetBrains Mono', monospace" }}>
                    {connTest.ok ? '✓ ' : '✗ '}{connTest.message}
                    {connTest.models && connTest.models.length > 0 && <div style={{ color: 'var(--text-dim)', marginTop: 2 }}>Models: {connTest.models.slice(0, 5).join(', ')}{connTest.models.length > 5 ? ` (+${connTest.models.length - 5})` : ''}</div>}
                    {connTest.token_status && <div style={{ color: 'var(--text-dim)' }}>Token: {connTest.token_status.status} · {connTest.token_status.seconds_left > 0 ? Math.floor(connTest.token_status.seconds_left / 60) + 'm left' : 'expired'}</div>}
                  </div>
                )}

                {/* Inline editor */}
                {isEditing && (
                  <ConnEditor
                    form={connForm} setForm={setConnForm}
                    onSave={() => {
                      fetch('/api/connections', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(connForm) })
                        .then(r => r.json()).then(d => {
                          if (d.ok) { setEditingConn(null); setConnForm({}); setConnMsg(`Saved connection: ${connForm.name}`); setTimeout(() => setConnMsg(''), 3000); refreshConnections(); refresh() }
                          else setConnMsg(d.error || 'Save failed')
                        })
                    }}
                  />
                )}
              </div>
            )
          })}

          {/* New connection button / editor */}
          {!editingConn && (
            <button className="icon-btn" style={{ marginTop: 8, borderColor: 'var(--accent)', color: 'var(--accent)' }} onClick={() => {
              setEditingConn('__new__')
              setConnForm({ name: '', base_url: '', api_key: '', model: '', auth_type: 'simple', extra_headers: {} })
              setConnTest(null)
            }}>+ new connection</button>
          )}
          {editingConn === '__new__' && (
            <>
              <ConnEditor
                form={connForm} setForm={setConnForm}
                onSave={() => {
                  fetch('/api/connections', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(connForm) })
                    .then(r => r.json()).then(d => {
                      if (d.ok) { setEditingConn(null); setConnForm({}); setConnMsg(`Created connection: ${connForm.name}`); setTimeout(() => setConnMsg(''), 3000); refreshConnections(); refresh() }
                      else setConnMsg(d.error || 'Create failed')
                    })
                }}
                onCancel={() => { setEditingConn(null); setConnForm({}) }}
              />
            </>
          )}

          {connMsg && (
            <div style={{ marginTop: 10, padding: 8, borderRadius: 8, background: 'rgba(0,0,0,0.3)', border: '1px solid var(--accent)', fontSize: 11, color: 'var(--accent)' }}>
              {connMsg}
            </div>
          )}

          <div style={{ marginTop: 16, padding: 12, borderRadius: 10, background: 'rgba(0,240,255,0.05)', border: '1px solid rgba(0,240,255,0.2)', fontSize: 11, color: 'var(--text-3)', lineHeight: 1.5 }}>
            <div style={{ color: 'var(--accent)', marginBottom: 6, fontFamily: "'JetBrains Mono', monospace", fontSize: 9, letterSpacing: '0.1em' }}>HOW IT WORKS</div>
            Each security profile can be assigned one connection. Assignments and model selection take effect on the next model call — no restart. OAuth connections auto-refresh their bearer token when it's within {oauthStatus?.refresh_margin_s || 600}s of expiry (background monitor + lazy refresh on every call). Leave a profile's assignment blank to use the env default (DELA_*_BASE_URL / API_KEY / MODEL).
          </div>
        </>
      )}

      {/* ROUTER */}
      {!loading && section === 'router' && settings && (
        <>
          <div style={{ fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)', marginBottom: 12, fontFamily: "'JetBrains Mono', monospace" }}>
            MODEL ROUTER
          </div>
          <div className="settings-grid">
            <LiveField
              label="ROUTER ENABLED"
              settingKey="model_router_enabled"
              value={settings.live?.model_router_enabled || 'false'}
              options={[
                { value: 'true', label: 'ON — auto-select model by complexity' },
                { value: 'false', label: 'OFF — use default model for all' },
              ]}
              hint="When ON, simple tasks use the fast model, complex tasks use premium."
            />
            <LiveField
              label="FAST MODEL"
              settingKey="model_fast"
              value={settings.live?.model_fast || settings.model}
              hint="Cheap model for trivial tasks (math, formatting, lookups)"
            />
            <LiveField
              label="PREMIUM MODEL"
              settingKey="model_premium"
              value={settings.live?.model_premium || settings.model}
              hint="Expensive model for complex tasks (coding, architecture, analysis)"
            />
          </div>
          <div style={{ marginTop: 16, padding: 12, borderRadius: 10, background: 'rgba(0,240,255,0.05)', border: '1px solid rgba(0,240,255,0.2)', fontSize: 11, color: 'var(--text-3)', lineHeight: 1.5 }}>
            <div style={{ color: 'var(--accent)', marginBottom: 6, fontFamily: "'JetBrains Mono', monospace", fontSize: 9, letterSpacing: '0.1em' }}>
              HOW IT WORKS
            </div>
            The router classifies each request by complexity using signals like input length,
            code blocks, keywords, and tool usage. Trivial tasks (e.g. "what is 2+2") route to
            the fast model. Complex tasks (e.g. "implement a security scanner") route to premium.
            Everything else uses the default model. This saves tokens and cost on simple operations.
          </div>
        </>
      )}

      {/* VOICE */}
      {!loading && section === 'voice' && settings && (
        <>
          <LiveField
            label="WHISPER MODEL"
            settingKey="whisper_model"
            value={settings.live?.whisper_model || settings.voice.whisper_model}
            options={[
              { value: 'tiny.en', label: 'tiny.en (fastest)' },
              { value: 'base.en', label: 'base.en' },
              { value: 'small.en', label: 'small.en (recommended)' },
              { value: 'medium.en', label: 'medium.en (slower)' },
            ]}
            hint="Reloaded on next STT call — no restart."
          />
          <LiveField
            label="WHISPER DEVICE"
            settingKey="whisper_device"
            value={settings.live?.whisper_device || settings.voice.whisper_device}
            options={[
              { value: 'cuda', label: 'cuda (GPU)' },
              { value: 'cpu', label: 'cpu' },
            ]}
            hint="Reloaded on next STT call — no restart."
          />
          <Field label="WHISPER COMPUTE" value={settings.voice.whisper_compute} hint="float16 / int8 / float32 — change via .env" />
          <LiveField
            label="PIPER VOICE"
            settingKey="piper_voice"
            value={settings.live?.piper_voice || settings.voice.piper_voice}
            options={[
              { value: 'en_US-amy-medium', label: 'en_US-amy-medium (female)' },
              { value: 'en_US-lessac-medium', label: 'en_US-lessac-medium (female)' },
              { value: 'en_US-libritts-high', label: 'en_US-libritts-high (high quality)' },
              { value: 'en_GB-alan-medium', label: 'en_GB-alan-medium (male, British)' },
            ]}
            hint="Reloaded on next TTS call — no restart."
          />
          <LiveField
            label="VAD AGGRESSIVENESS"
            settingKey="vad_aggressiveness"
            value={settings.live?.vad_aggressiveness ?? settings.voice.vad_aggressiveness}
            hint="0-3 (higher = more aggressive). Applied to next voice session."
          />
          <div style={{ marginTop: 16, padding: 12, borderRadius: 10, background: 'rgba(70,242,176,0.05)', border: '1px solid rgba(70,242,176,0.2)', fontSize: 11, color: 'var(--green)' }}>
            Voice settings marked LIVE apply immediately — no restart needed. They persist across restarts via dela_state/live_settings.json.
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
