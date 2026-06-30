import { useState, useEffect, useCallback } from 'react'

const CATS = ['general', 'preference', 'identity', 'decision', 'project']

const CAT_COLORS = {
  preference: 'var(--amber)',
  identity:   'var(--accent)',
  decision:   'var(--red)',
  project:    'var(--green)',
  general:    'var(--text-dim)',
}

export function MemoryPanel() {
  const [facts, setFacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [editId, setEditId] = useState(null)
  const [editText, setEditText] = useState('')
  const [newText, setNewText] = useState('')
  const [newCat, setNewCat] = useState('general')
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('')
  const [catFilter, setCatFilter] = useState('')

  const fetchFacts = useCallback(() => {
    const url = filter
      ? `/api/memory/search?q=${encodeURIComponent(filter)}${catFilter ? '&category=' + catFilter : ''}`
      : '/api/memory'
    fetch(url)
      .then(r => r.json())
      .then(data => {
        setFacts(filter ? (data.facts || []) : (data || []))
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [filter, catFilter])

  useEffect(() => { fetchFacts() }, [fetchFacts])

  const saveEdit = (id) => {
    const text = editText.trim()
    if (!text) return
    fetch(`/api/memory/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.ok) { setEditId(null); fetchFacts() }
        else setError(data.error || 'Failed to save')
      })
      .catch(() => setError('Network error'))
  }

  const deleteFact = (id) => {
    if (!window.confirm('Delete this fact?')) return
    fetch(`/api/memory/${id}`, { method: 'DELETE' })
      .then(r => r.json())
      .then(data => {
        if (data.ok) fetchFacts()
        else setError('Failed to delete')
      })
      .catch(() => setError('Network error'))
  }

  const addFact = () => {
    const text = newText.trim()
    if (!text) return
    fetch('/api/memory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, category: newCat }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.id && data.id > 0) {
          setNewText('')
          setNewCat('general')
          fetchFacts()
        } else if (data.duplicate) {
          setError('Duplicate fact — already stored.')
        } else {
          setError(data.error || 'Failed to add')
        }
      })
      .catch(() => setError('Network error'))
  }

  const handleEditKey = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      saveEdit(editId)
    } else if (e.key === 'Escape') {
      setEditId(null)
    }
  }

  return (
    <div className="panel-body">
      {error && (
        <div style={{ padding: '6px 10px', marginBottom: 10, background: 'rgba(255,90,69,0.1)', border: '1px solid rgba(255,90,69,0.3)', borderRadius: 6, fontSize: 11, color: 'var(--red)' }}>
          {error}
          <button onClick={() => setError('')} style={{ float: 'right', background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', fontSize: 14 }}>✕</button>
        </div>
      )}

      {/* Search + filter bar */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
        <input
          className="chat-input"
          style={{ flex: 1, fontSize: 12 }}
          placeholder="Search facts..."
          value={filter}
          onChange={e => setFilter(e.target.value)}
        />
        <select
          className="chat-input"
          style={{ width: 120, fontSize: 12 }}
          value={catFilter}
          onChange={e => setCatFilter(e.target.value)}
        >
          <option value="">All categories</option>
          {CATS.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        {filter && <button className="icon-btn" onClick={() => { setFilter(''); setCatFilter('') }} style={{ fontSize: 9 }}>clear</button>}
      </div>

      {loading ? (
        <div style={{ color: 'var(--text-dim)', fontSize: 12 }}>Loading...</div>
      ) : facts.length === 0 ? (
        <div style={{ color: 'var(--text-dim)', fontSize: 12 }}>
          {filter ? `No facts matching "${filter}".` : 'No stored facts yet.'}
        </div>
      ) : (
        facts.map(f => (
          <div key={f.id} style={{ marginBottom: 10, padding: '8px 10px', borderRadius: 8, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <span style={{
                fontSize: 8, padding: '1px 5px', borderRadius: 3, fontWeight: 600, letterSpacing: '0.08em',
                color: CAT_COLORS[f.category] || 'var(--text-dim)',
                border: `1px solid ${CAT_COLORS[f.category] || 'var(--border)'}`,
              }}>
                {f.category}
              </span>
              <span style={{ fontSize: 9, color: 'var(--text-dim)', fontFamily: "'JetBrains Mono', monospace" }}>#{f.id}</span>
              <div style={{ flex: 1 }} />
              <button className="icon-btn" onClick={() => { setEditId(f.id); setEditText(f.text) }} style={{ fontSize: 9 }}>edit</button>
              <button className="icon-btn" onClick={() => deleteFact(f.id)} style={{ fontSize: 9, color: 'var(--red)' }}>delete</button>
            </div>
            {editId === f.id ? (
              <div>
                <textarea
                  className="chat-input"
                  style={{ width: '100%', minHeight: 40, fontSize: 11, resize: 'vertical', marginBottom: 4 }}
                  value={editText}
                  onChange={e => setEditText(e.target.value)}
                  onKeyDown={handleEditKey}
                  autoFocus
                />
                <div style={{ display: 'flex', gap: 6, fontSize: 9 }}>
                  <button className="chip active" onClick={() => saveEdit(f.id)}>save</button>
                  <button className="chip" onClick={() => setEditId(null)}>cancel</button>
                  <span style={{ color: 'var(--text-faint)', alignSelf: 'center' }}>Ctrl+Enter to save</span>
                </div>
              </div>
            ) : (
              <div style={{ fontSize: 12, color: 'var(--text)', lineHeight: 1.4 }}>{f.text}</div>
            )}
          </div>
        ))
      )}

      {/* Add new fact */}
      <div style={{ marginTop: 16, padding: '10px 12px', borderRadius: 10, background: 'rgba(0,240,255,0.03)', border: '1px solid rgba(0,240,255,0.15)' }}>
        <div style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--text-dim)', marginBottom: 6 }}>ADD FACT</div>
        <textarea
          className="chat-input"
          style={{ width: '100%', minHeight: 36, fontSize: 11, resize: 'vertical', marginBottom: 6 }}
          value={newText}
          onChange={e => setNewText(e.target.value)}
          placeholder="Enter a new fact..."
        />
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <select
            className="chat-input"
            style={{ width: 110, fontSize: 11 }}
            value={newCat}
            onChange={e => setNewCat(e.target.value)}
          >
            {CATS.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <button className="chip active" onClick={addFact} style={{ fontSize: 9 }}>add</button>
        </div>
      </div>
    </div>
  )
}
