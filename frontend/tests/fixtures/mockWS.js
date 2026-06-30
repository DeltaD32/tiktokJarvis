// Runs in the page BEFORE the app loads. Replaces window.WebSocket with a
// controllable mock so tests can push server messages and inspect sent frames
// without a real backend.
export const MOCK_WS_INIT_SCRIPT = `
(() => {
  const NOW = () => Math.floor(Date.now() / 1000)
  const DEFAULT_INIT = () => ({
    type: 'init',
    notices: [
      { id: 'n1', message: 'Heartbeat: uplink reachable.', severity: 'info', source: 'heartbeat', created_at: NOW() - 3600 },
      { id: 'n2', message: 'Security scan found 1 critical issue.', severity: 'critical', source: 'security', created_at: NOW() - 120 },
    ],
    heartbeat_active: true,
    cost: '$0.0000',
  })

  class MockWebSocket {
    constructor(url) {
      this.url = url
      this.readyState = 0
      this.onopen = null
      this.onmessage = null
      this.onclose = null
      this.onerror = null
      this._sent = []
      this._autoOpen = true
      window.__mockWSInstances.push(this)
      setTimeout(() => this._maybeOpen(), 0)
    }
    send(data) {
      try { this._sent.push(JSON.parse(data)) } catch { this._sent.push(data) }
      window.__mockWSSent = window.__mockWSInstances[window.__mockWSInstances.length - 1]._sent
    }
    close() {
      this.readyState = 3
      this._autoOpen = false
      if (this.onclose) this.onclose({ wasClean: true })
    }
    _maybeOpen() {
      if (!this._autoOpen) return
      this.readyState = 1
      if (this.onopen) this.onopen()
      const init = window.__mockWSInit || DEFAULT_INIT()
      this._deliver(init)
    }
    _deliver(msg) {
      if (this.onmessage) this.onmessage({ data: JSON.stringify(msg) })
    }
  }
  // Real WebSocket exposes these as static constants; the hook checks
  // readyState === WebSocket.OPEN, so they must exist on the mock too.
  MockWebSocket.CONNECTING = 0
  MockWebSocket.OPEN = 1
  MockWebSocket.CLOSING = 2
  MockWebSocket.CLOSED = 3
  window.WebSocket = MockWebSocket
  window.__mockWSInstances = []
  window.__mockWSSent = []
  window.__mockWSInit = null
  window.__mockWSPush = (msg) => {
    const ws = window.__mockWSInstances[window.__mockWSInstances.length - 1]
    if (ws) ws._deliver(msg)
  }
  window.__mockWSGetSent = () => {
    const ws = window.__mockWSInstances[window.__mockWSInstances.length - 1]
    return ws ? ws._sent.slice() : []
  }
  window.__mockWSCloseLast = () => {
    const ws = window.__mockWSInstances[window.__mockWSInstances.length - 1]
    if (ws) ws.close()
  }
  window.__mockWSCount = () => window.__mockWSInstances.length
})();
`
