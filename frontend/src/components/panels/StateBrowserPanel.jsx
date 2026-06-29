import { useState, useEffect } from 'react'
import { HoloPanel } from '../HoloPanel'

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
      .then(data => { setStateTypes(data || []) })
      .catch(() => {})
  }, [])

  const loadType = (type) => {
    setSelectedType(type)
    setSelectedItem(null)
    setSearchResults(null)
    setLoading(true)
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
    setLoading(true)
    setSelectedItem(null)
    fetch(`/api/state/search?q=${encodeURIComponent(searchQuery)}`)
      .then(r => r.json())
      .then(data => { setSearchResults(data || []); setLoading(false) })
      .catch(() => setLoading(false))
  }

  const dismissNotice = (id) => {
    fetch(`/api/state/notices/${id}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify({dismiss: true}) })
      .then(() => loadType('notices'))
  }

  const deleteFact = (id) => {
    fetch(`/api/state/memory/${id}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify({delete: true}) })
      .then(() => loadType('memory'))
  }

  return (
    <HoloPanel title="State Browser" message={message} onClose={onClose}>
      {/* Search bar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input
          className="chat-input"
          style={{ flex: 1, fontSize: 12 }}
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && doSearch()}
          placeholder="Search all state..."
        />
        <button className="icon-btn" onClick={doSearch} style={{ borderColor: 'var(--cyan)', color: 'var(--cyan)' }}>search</button>
      </div>

      {/* Search results */}
      {searchResults && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 10, letterSpacing: '0.15em', color: 'var(--text-dim)', marginBottom: 8, fontFamily: 'Orbitron, monospace' }}>
            SEARCH RESULTS ({searchResults.length})
          </div>
          {searchResults.length === 0 && <p className="panel-empty">No matches found.</p>}
          {searchResults.map((r, i) => (
            <div key={i} className="panel-item" onClick={() => loadType(r.type)}>
              <span className={`badge badge-${r.type === 'memory' ? 'info' : 'open'}`}>{r.type}</span>
              <span style={{ marginLeft: 8, fontSize: 11 }}>{r.id || r.line}</span>
              <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4 }}>{r.snippet}</div>
            </div>
          ))}
          <button className="icon-btn" onClick={() => setSearchResults(null)} style={{ marginTop: 8 }}>clear search</button>
        </div>
      )}

      {/* State type list */}
      {!selectedType && !searchResults && (
        <>
          <div style={{ fontSize: 10, letterSpacing: '0.15em', color: 'var(--text-dim)', marginBottom: 8, fontFamily: 'Orbitron, monospace' }}>
            STATE TYPES
          </div>
          {stateTypes.map(t => (
            <div key={t.type} className="panel-item" onClick={() => loadType(t.type)} style={{ cursor: 'pointer' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="panel-item-title">{t.type}</span>
                <span className="badge badge-open">{t.items}</span>
              </div>
              <div className="panel-item-meta">{t.description}</div>
            </div>
          ))}
        </>
      )}

      {/* Items in selected type */}
      {selectedType && !selectedItem && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 10, letterSpacing: '0.15em', color: 'var(--cyan)', fontFamily: 'Orbitron, monospace' }}>
              {selectedType.toUpperCase()}
            </span>
            <button className="icon-btn" onClick={() => { setSelectedType(null); setItems(null) }}>back</button>
          </div>

          {loading && <p className="panel-empty">Loading...</p>}

          {!loading && items?.items && items.items.map(item => (
            <div key={item.id || item.name} className="panel-item" onClick={() => loadItem(item.id || item.name)} style={{ cursor: 'pointer' }}>
              <div className="panel-item-title">{item.name || item.id || '?'}</div>
              <div className="panel-item-meta">
                {item.status && <span className={`badge badge-${item.status === 'done' ? 'done' : 'open'}`}>{item.status}</span>}
                {item.id && <span style={{ marginLeft: 8 }}>id: {item.id}</span>}
              </div>
            </div>
          ))}

          {!loading && items?.data && typeof items.data === 'object' && Object.entries(items.data).map(([key, val]) => (
            <div key={key} className="panel-item">
              <div className="panel-item-title">{key}</div>
              <div className="panel-item-meta" style={{ whiteSpace: 'pre-wrap', maxHeight: 100, overflow: 'hidden' }}>
                {typeof val === 'string' ? val : JSON.stringify(val, null, 2).slice(0, 200)}
              </div>
              {selectedType === 'memory' && (
                <button className="icon-btn" onClick={() => deleteFact(key)} style={{ marginTop: 4, fontSize: 10 }}>delete</button>
              )}
            </div>
          ))}

          {!loading && items?.lines && items.lines.map((line, i) => (
            <div key={i} className="panel-item" style={{ fontSize: 10, fontFamily: 'monospace' }}>
              {line.slice(0, 150)}
            </div>
          ))}

          {!loading && !items?.items && !items?.data && !items?.lines && (
            <p className="panel-empty">No items or empty state.</p>
          )}
        </>
      )}

      {/* Selected item detail */}
      {selectedItem && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 10, letterSpacing: '0.15em', color: 'var(--cyan)', fontFamily: 'Orbitron, monospace' }}>
              ITEM DETAIL
            </span>
            <button className="icon-btn" onClick={() => setSelectedItem(null)}>back</button>
          </div>
          <pre className="audit-log" style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {JSON.stringify(selectedItem, null, 2).slice(0, 2000)}
          </pre>
        </>
      )}
    </HoloPanel>
  )
}