import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'

const AuthContext = createContext(null)

const TOKEN_KEY = 'dela_access_token'
const REFRESH_KEY = 'dela_refresh_token'
const USER_KEY = 'dela_user'

function loadPersisted() {
  try {
    const token = localStorage.getItem(TOKEN_KEY)
    const refresh = localStorage.getItem(REFRESH_KEY)
    const userJson = localStorage.getItem(USER_KEY)
    const user = userJson ? JSON.parse(userJson) : null
    if (token && user) return { token, refresh, user }
  } catch {}
  return { token: null, refresh: null, user: null }
}

function persist(token, refresh, user) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
    localStorage.setItem(REFRESH_KEY, refresh || '')
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  } else {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
    localStorage.removeItem(USER_KEY)
  }
}

export function AuthProvider({ children }) {
  const persisted = useRef(loadPersisted())
  const [user, setUser] = useState(persisted.current.user)
  const [token, setToken] = useState(persisted.current.token)

  const isAuthenticated = !!token && !!user
  const isAdmin = user?.role === 'admin'

  const login = useCallback(async (username, password) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    const data = await res.json()
    if (!data.ok) throw new Error(data.error || 'Login failed')
    setToken(data.access_token)
    setUser(data.user)
    persist(data.access_token, data.refresh_token, data.user)
    return data
  }, [])

  const logout = useCallback(async () => {
    try {
      if (token) {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        })
      }
    } catch {} // best-effort
    setToken(null)
    setUser(null)
    persist(null)
  }, [token])

  const authFetch = useCallback((url, options = {}) => {
    const headers = { ...options.headers }
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    return fetch(url, { ...options, headers })
  }, [token])

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated, isAdmin, login, logout, authFetch }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
