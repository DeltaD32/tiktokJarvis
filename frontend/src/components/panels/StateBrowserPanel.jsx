import { useState, useEffect } from 'react'
import { HoloPanel } from '../HoloPanel'

const TYPE_ICONS = {
  memory: '🧠', notices: '🔔', tasks: '📋', projects: '📁',
  blackboards: '⬛', workflows: '⚙️', sessions: '💬',
  routing: '🗺️', audit: '📊', events: '📌', cost: '💰', styles: '🎨',
}

export function StateBrowserPanel({ onClose, message }) {
  const [stateTypes, setStateTypes] = useState([])
  const [selectedType, setSelectedType] = useState(null)
  const [items, setItems] = useState(null)
  const [selectedItem, setSelectedItem] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetch('/api/state')
      .then(r => r.json())
      .then(data => setStateTypes(data || []))
      .catch(() => {})
  }, [])

  const loadType = (type) => {
    setSelectedType(type); setSelectedItem(null); setSearchResults(null); setLoading(true)
    fetch(`/api/state/${type}`)
      .then(r => r.json())
      .then(data => { setItems(data); setLoading(false) })
      .catch(() => setLoading(false))
  }

  const loadItem = (id) => {
    setLoading(true)
    fetch(`/api/state/${selectedType}/${id}`)
      .then(r => r.json())
      .then(data => { setSelectedItem(data); setLoading(false) })
      .catch(() => setLoading(false))
  }

  const doSearch = () => {
    if (!searchQuery.trim()) return
    setLoading(true); setSelectedItem(null)
    fetch(`/api/state/search?q=${encodeURIComponent(searchQuery)}`)
      .then(r => r.json())
      .then(data => { setSearchResults(data || []); setLoading(false) })
      .catch(() => setLoading(false))
  }

  const refreshTypes = () => {
    fetch('/api/state').then(r => r.json()).then(data => setStateTypes(data || [])).catch(() => {})
  }

  return (
    <HoloPanel title={`State Browser (${stateTypes.length} types)`} message={message} onClose={onClose}>
      {/* Search bar */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
        <input className="chat-input" style={{ flex: 1, fontSize: 11 }}
          value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && doSearch()} placeholder="Search all state..." />
        <button className="icon-btn" onClick={doSearch} style={{ borderColor: 'var(--cyan)', color: 'var(--cyan)', fontSize: 10 }}>search</button>
        <button className="icon-btn" onClick={refreshTypes} style={{ fontSize: 9, opacity: 0.5 }}>↻</button>
      </div>

      {/* Search results */}
      {searchResults && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--cyan)', fontFamily: "'JetBrains Mono', monospace" }}>
              RESULTS ({searchResults.length})
            </span>
            <button className="icon-btn" onClick={() => setSearchResults(null)} style={{ fontSize: 9 }}>clear</button>
          </div>
          {searchResults.length === 0 && <p className="panel-empty">No matches.</p>}
          {searchResults.map((r, i) => (
            <div key={i} className="panel-item" onClick={() => loadType(r.type)} style={{ cursor: 'pointer' }}>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 3 }}>
                <span className="badge badge-open" style={{ fontSize: 9 }}>{r.type}</span>
                <span style={{ fontSize: 10, fontFamily: "'JetBrains Mono', monospace", color: 'var(--text-dim)' }}>{r.id || r.line}</span>
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-dim)', lineHeight: 1.3 }}>{r.snippet?.slice(0, 120)}</div>
            </div>
          ))}
        </div>
      )}

      {/* Type grid */}
      {!selectedType && !searchResults && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
          {stateTypes.map(t => (
            <div key={t.type} className="panel-item" onClick={() => loadType(t.type)} style={{ cursor: 'pointer' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text)' }}>
                  {TYPE_ICONS[t.type] || '📄'} {t.type}
                </span>
                <span className="badge badge-open" style={{ fontSize: 9, fontFamily: "'JetBrains Mono', monospace" }}>{t.items}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Items in type */}
      {selectedType && !selectedItem && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--cyan)', fontFamily: "'JetBrains Mono', monospace" }}>
              {selectedType.toUpperCase()} {items?.items ? `(${items.items.length})` : ''}
            </span>
            <button className="icon-btn" onClick={() => { setSelectedType(null); setItems(null) }} style={{ fontSize: 9 }}>← back</button>
          </div>
          {loading && <p className="panel-empty">Loading...</p>}
          {!loading && items?.items?.map(item => (
            <div key={item.id || item.name} className="panel-item" onClick={() => loadItem(item.id || item.name)} style={{ cursor: 'pointer' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 11 }}>{item.name || item.id || '?'}</span>
                {item.status && <span className={`badge badge-${item.status === 'done' ? 'done' : 'open'}`} style={{ fontSize: 9 }}>{item.status}</span>}
              </div>
            </div>
          ))}
          {!loading && !items?.items && !items?.data && !items?.lines && <p className="panel-empty">Empty.</p>}
        </>
      )}

      {/* Item detail */}
      {selectedItem && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--cyan)', fontFamily: "'JetBrains Mono', monospace" }}>DETAIL</span>
            <button className="icon-btn" onClick={() => setSelectedItem(null)} style={{ fontSize: 9 }}>← back</button>
          </div>
          <pre className="audit-log" style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 10, maxHeight: 400, overflow: 'auto' }}>
            {JSON.stringify(selectedItem, null, 2).slice(0, 3000)}
          </pre>
        </>
      )}
    </HoloPanel>
  )
}
