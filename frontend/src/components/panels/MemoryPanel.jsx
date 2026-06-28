import { useState, useEffect } from 'react'
import { HoloPanel } from '../HoloPanel'

export function MemoryPanel({ onClose, message }) {
  const [facts, setFacts]         = useState([])
  const [loading, setLoading]     = useState(true)
  const [editId, setEditId]       = useState(null)
  const [editText, setEditText]   = useState('')
  const [newText, setNewText]     = useState('')
  const [newCat, setNewCat]       = useState('general')

  const refresh = () => {
    fetch('/api/memory')
      .then(r => r.json())
      .then(data => { setFacts(data); setLoading(false) })
      .catch(() => setLoading(false))
  }

  useEffect(() => { refresh() }, [])

  const saveEdit = (id) => {
    fetch(`/api/memory/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: editText }),
    }).then(() => { setEditId(null); refresh() })
  }

  const deleteFact = (id) => {
    fetch(`/api/memory/${id}`, { method: 'DELETE' })
      .then(() => refresh())
  }

  const addFact = () => {
    if (!newText.trim()) return
    fetch('/api/memory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: newText, category: newCat }),
    }).then(() => { setNewText(''); refresh() })
  }

  return (
    <HoloPanel title="Memory" message={message} onClose={onClose}>
      {loading && <p className="panel-empty">Loading…</p>}

      {!loading && facts.length === 0 && (
        <p className="panel-empty">No stored facts yet.</p>
      )}

      {facts.map(f => (
        <div key={f.id} className="panel-item">
          {editId === f.id ? (
            <>
              <textarea
                className="chat-input"
                style={{ width: '100%', minHeight: 48, marginBottom: 6 }}
                value={editText}
                onChange={e => setEditText(e.target.value)}
              />
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="icon-btn" onClick={() => saveEdit(f.id)}>save</button>
                <button className="icon-btn" onClick={() => setEditId(null)}>cancel</button>
              </div>
            </>
          ) : (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                <span className={`badge badge-${f.category === 'identity' ? 'info' : f.category === 'preference' ? 'attention' : 'open'}`}>
                  {f.category}
                </span>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button className="icon-btn" onClick={() => { setEditId(f.id); setEditText(f.text) }}>edit</button>
                  <button className="icon-btn" onClick={() => deleteFact(f.id)}>delete</button>
                </div>
              </div>
              <div className="panel-item-title">{f.text}</div>
              <div className="panel-item-meta">id {f.id}</div>
            </>
          )}
        </div>
      ))}

      <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--panel-border)' }}>
        <div style={{ fontSize: 10, letterSpacing: '0.15em', color: 'var(--text-dim)', marginBottom: 8, fontFamily: 'Orbitron, monospace' }}>
          ADD NEW FACT
        </div>
        <textarea
          className="chat-input"
          style={{ width: '100%', minHeight: 40, marginBottom: 8 }}
          value={newText}
          onChange={e => setNewText(e.target.value)}
          placeholder="e.g. The user prefers morning meetings."
        />
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <select
            className="chat-input"
            style={{ width: 'auto', padding: '6px 8px', fontSize: 11 }}
            value={newCat}
            onChange={e => setNewCat(e.target.value)}
          >
            <option value="general">general</option>
            <option value="preference">preference</option>
            <option value="identity">identity</option>
            <option value="decision">decision</option>
            <option value="project">project</option>
          </select>
          <button className="icon-btn" onClick={addFact} style={{ borderColor: 'var(--cyan)', color: 'var(--cyan)' }}>
            add
          </button>
        </div>
      </div>
    </HoloPanel>
  )
}