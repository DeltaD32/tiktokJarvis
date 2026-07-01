import { useState, useEffect } from 'react'
import { HoloPanel } from '../HoloPanel'

export function AdminPanel({ onClose, token }) {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // New user form
  const [newUsername, setNewUsername] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newRole, setNewRole] = useState('user')
  const [newEmail, setNewEmail] = useState('')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState('')
  const [createOk, setCreateOk] = useState('')

  const authHeaders = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }

  const fetchUsers = () => {
    setLoading(true)
    setError('')
    fetch('/api/users', { headers: { 'Authorization': `Bearer ${token}` } })
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data)) setUsers(data)
        else if (data.users) setUsers(data.users)
        else setError(data.error || 'Failed to load users')
      })
      .catch(() => setError('Failed to load users'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchUsers() }, [])

  const handleCreate = (e) => {
    e.preventDefault()
    if (!newUsername.trim() || !newPassword) return
    setCreating(true)
    setCreateError('')
    setCreateOk('')
    fetch('/api/users', {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({
        username: newUsername.trim(),
        password: newPassword,
        role: newRole,
        email: newEmail.trim() || null,
      }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.ok) {
          setCreateOk(`User "${data.user?.username || newUsername}" created`)
          setNewUsername('')
          setNewPassword('')
          setNewEmail('')
          fetchUsers()
        } else {
          setCreateError(data.error || 'Failed to create user')
        }
      })
      .catch(() => setCreateError('Network error'))
      .finally(() => setCreating(false))
  }

  const handleDelete = (userId, username) => {
    if (!confirm(`Delete user "${username}"?`)) return
    fetch(`/api/users/${userId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(() => fetchUsers())
      .catch(() => {})
  }

  return (
    <HoloPanel title="User Management" onClose={onClose}>
      <div style={{ padding: '12px 16px', maxHeight: 'calc(100vh - 200px)', overflow: 'auto' }}>
        {loading && <div style={{ color: 'var(--text-dim)', fontSize: 12 }}>Loading users...</div>}
        {error && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 8 }}>{error}</div>}

        {/* User list */}
        {!loading && !error && (
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 10, color: 'var(--text-dim)', letterSpacing: '0.1em', marginBottom: 8, fontFamily: "'JetBrains Mono', monospace" }}>
              USERS ({users.length})
            </div>
            {users.length === 0 && (
              <div style={{ color: 'var(--text-faint)', fontSize: 11 }}>No users found</div>
            )}
            {users.map(u => (
              <div
                key={u.id}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '6px 8px', borderBottom: '1px solid var(--border)',
                  fontSize: 11,
                }}
              >
                <div>
                  <span style={{ color: 'var(--text)', fontFamily: "'JetBrains Mono', monospace" }}>
                    {u.username}
                  </span>
                  {u.role === 'admin' && (
                    <span style={{ color: 'var(--amber)', fontSize: 9, marginLeft: 6 }}>◆ ADMIN</span>
                  )}
                  <span style={{ color: 'var(--text-dim)', fontSize: 10, marginLeft: 8 }}>
                    {u.role}
                  </span>
                  {u.email && (
                    <span style={{ color: 'var(--text-faint)', fontSize: 9, marginLeft: 8 }}>
                      {u.email}
                    </span>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(u.id, u.username)}
                  style={{
                    background: 'none', border: '1px solid var(--text-dim)',
                    color: 'var(--text-dim)', borderRadius: 3,
                    padding: '1px 6px', fontSize: 9, cursor: 'pointer',
                    fontFamily: "'JetBrains Mono', monospace",
                  }}
                  title="Delete user"
                >
                  DEL
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Create user form */}
        <form onSubmit={handleCreate} style={{ borderTop: '1px solid var(--border)', paddingTop: 12 }}>
          <div style={{ fontSize: 10, color: 'var(--text-dim)', letterSpacing: '0.1em', marginBottom: 8, fontFamily: "'JetBrains Mono', monospace" }}>
            ADD USER
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <input
              className="login-input"
              type="text"
              value={newUsername}
              onChange={e => setNewUsername(e.target.value)}
              placeholder="Username"
              style={{ fontSize: 11, padding: '4px 8px' }}
            />
            <input
              className="login-input"
              type="password"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              placeholder="Password (min 8 chars)"
              style={{ fontSize: 11, padding: '4px 8px' }}
            />
            <input
              className="login-input"
              type="email"
              value={newEmail}
              onChange={e => setNewEmail(e.target.value)}
              placeholder="Email (optional)"
              style={{ fontSize: 11, padding: '4px 8px' }}
            />
            <select
              value={newRole}
              onChange={e => setNewRole(e.target.value)}
              style={{
                background: 'var(--bg)', color: 'var(--text)',
                border: '1px solid var(--border)', borderRadius: 4,
                padding: '4px 8px', fontSize: 11,
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              <option value="user">user</option>
              <option value="admin">admin</option>
              <option value="viewer">viewer</option>
            </select>
            <button
              type="submit"
              disabled={creating || !newUsername.trim() || !newPassword}
              className="run-btn"
              style={{ fontSize: 10, padding: '4px 8px', alignSelf: 'flex-start' }}
            >
              {creating ? 'CREATING...' : 'CREATE'}
            </button>
          </div>
          {createError && <div style={{ color: 'var(--red)', fontSize: 10, marginTop: 6 }}>{createError}</div>}
          {createOk && <div style={{ color: 'var(--green)', fontSize: 10, marginTop: 6 }}>{createOk}</div>}
        </form>
      </div>
    </HoloPanel>
  )
}
