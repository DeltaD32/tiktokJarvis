// Canned REST responses for every /api/* endpoint the frontend talks to.
// Tests can override a specific route by calling page.route(...) AFTER
// installMockApi — later registrations run first in Playwright.

export const MOCK = {
  uplink: { status: 'connected', model: 'glm-5.2', latency_ms: 42, profile: 'personal' },
  agents: [
    { name: 'researcher', description: 'Web research, URL fetching, host checking', status: 'ready', tool_count: 2, dispatch_count: 3, last_task: null },
    { name: 'presenter', description: 'Presentation design, PPT generation', status: 'ready', tool_count: 4, dispatch_count: 0, last_task: null },
    { name: 'secretary', description: 'Coordination, blackboard, conflict resolution', status: 'busy', tool_count: 'all', dispatch_count: 12, last_task: 'Coordinating project plan' },
    { name: 'workflow_designer', description: 'Workflow brainstorm, design, refinement', status: 'ready', tool_count: 6, dispatch_count: 1, last_task: null },
    { name: 'system_expert', description: 'Codebase inspection, code implementation', status: 'error', tool_count: 4, dispatch_count: 2, last_task: 'Patch security finding' },
  ],
  tools: [
    { name: 'fetch_url', description: 'Fetch a URL and return its content', requires_confirmation: false, param_count: 1 },
    { name: 'check_host', description: 'Check if a host is reachable', requires_confirmation: false, param_count: 1 },
    { name: 'create_task', description: 'Create a project task', requires_confirmation: true, param_count: 2 },
    { name: 'delete_task', description: 'Delete a task permanently', requires_confirmation: true, param_count: 1 },
    { name: 'list_tasks', description: 'List all tasks', requires_confirmation: false, param_count: 0 },
  ],
  memory: [
    { id: 'm1', text: 'User prefers morning meetings.', category: 'preference' },
    { id: 'm2', text: 'User name is Bruce.', category: 'identity' },
  ],
  notices: [
    { id: 'n1', message: 'Heartbeat: uplink reachable.', severity: 'info', source: 'heartbeat', created_at: Math.floor(Date.now() / 1000) - 3600 },
    { id: 'n2', message: 'Security scan found 1 critical issue.', severity: 'critical', source: 'security', created_at: Math.floor(Date.now() / 1000) - 120 },
  ],
  tasks: [
    { id: 't1', title: 'Ship voice barge-in fix', status: 'open', due: '2026-07-05' },
    { id: 't2', title: 'Write security audit doc', status: 'open', due: null },
    { id: 't3', title: 'Set up Ollama profile', status: 'done', due: '2026-06-20' },
  ],
  audit: { log: '[2026-06-29 10:00:00] gate granted: create_task\n[2026-06-29 10:01:00] tool: fetch_url', cost: 'Total cost: $0.0123 (4 calls)' },
  analytics: {
    model_calls: 12, estimated_cost_usd: 0.0123, tool_calls: 7, gate_granted: 3, gate_denied: 1,
    tool_breakdown: { fetch_url: 3, create_task: 2, check_host: 2 }, heartbeat_notices: 4, kill_switch_events: 0,
    recent_events: [
      { ts: '2026-06-29 10:01:00', type: 'tool', name: 'fetch_url' },
      { ts: '2026-06-29 10:00:00', type: 'gate', verdict: 'granted' },
    ],
  },
  models: { status: 'ok', models: ['glm-5.2', 'glm-4.5', 'qwen2.5-72b'], current: 'glm-5.2', count: 3, connection: 'env' },
  ollama: { status: 'not_running', models: [], model_count: 0 },
  status: { heartbeat_active: true, cost: '$0.0123', notice_count: 2 },
  stateTypes: [
    { type: 'memory', items: 2, description: 'Durable facts' },
    { type: 'notices', items: 2, description: 'Proactive notices' },
    { type: 'tasks', items: 3, description: 'Project tasks' },
  ],
  stateMemory: { data: { m1: 'User prefers morning meetings.', m2: 'User name is Bruce.' } },
  stateNotices: { items: MOCK_NOTICES_AS_ITEMS() },
  stateSearch: [
    { type: 'memory', id: 'm1', snippet: 'User prefers morning meetings.' },
  ],
  security: {
    score: 78,
    summary: { total: 5, critical: 1, warning: 2, ok: 1, info: 1 },
    findings: [
      { title: 'Hardcoded secret in config', detail: 'api_key found in config.json', category: 'secrets', severity: 'critical', priority: 'P0' },
      { title: 'No prompt-injection filter', detail: 'Inbound content not treated as data', category: 'injection', severity: 'warning', priority: 'P2' },
      { title: 'Audit log enabled', detail: 'All actions recorded', category: 'audit', severity: 'ok', priority: 'P4' },
    ],
  },
  vulnKb: {
    item_count: 2, cached: true, fetched_at: Math.floor(Date.now() / 1000) - 3600,
    items: [
      { id: 'LLM01', title: 'Prompt Injection', description: 'Injecting instructions.', remediation: 'Treat inbound as data.' },
      { id: 'CWE-79', title: 'XSS', description: 'Cross-site scripting.', remediation: 'Encode output.' },
    ],
    whitelisted_domains: ['owasp.org', 'cwe.mitre.org'],
  },
  workflows: [
    { name: 'morning-briefing', description: 'Daily summary of notices and tasks', steps: 2, schedule: '0 9 * * *' },
    { name: 'security-sweep', description: 'Run a full security scan', steps: 1, schedule: '' },
  ],
  workflowDetail: {
    name: 'morning-briefing', description: 'Daily summary of notices and tasks', schedule: '0 9 * * *',
    steps: [
      { id: 's1', name: 'gather', agent: 'researcher', task: 'Collect overnight notices', depends_on: [] },
      { id: 's2', name: 'report', agent: 'presenter', task: 'Format the briefing', depends_on: ['s1'] },
    ],
  },
  settings: {
    profile: {
      current: 'personal',
      available: [
        { name: 'personal', description: 'Full access, standard security', cors_origins: ['*'], tools_blocked: [], injection_level: 'standard', wiz_enabled: false },
        { name: 'work', description: 'Restricted, max injection defense', cors_origins: ['http://localhost:5173'], tools_blocked: ['fetch_url'], injection_level: 'maximum', wiz_enabled: true },
        { name: 'offline', description: 'Fully local with Ollama', cors_origins: ['http://localhost:5173'], tools_blocked: ['fetch_url', 'check_host'], injection_level: 'standard', wiz_enabled: false },
      ],
    },
    model: { name: 'Dela', model: 'glm-5.2', base_url: 'https://api.example.com/v1' },
    live: { model_router_enabled: 'false', model_fast: '', model_premium: '', thinking_level: '', whisper_model: 'small.en', whisper_device: 'cuda', piper_voice: 'en_US-amy-medium', vad_aggressiveness: 2 },
    live_overrides: {},
    voice: { whisper_model: 'small.en', whisper_device: 'cuda', whisper_compute: 'float16', piper_voice: 'en_US-amy-medium', vad_aggressiveness: 2 },
    tracing: { provider: 'none' },
    runtime: { tools_count: 47, agents_count: 5, python_version: '3.12.3' },
    heartbeat: { interval: 3600, checks: { uplink: { enabled: true }, security: { enabled: true } } },
  },
  connections: { connections: [], assignments: {} },
  oauthStatus: { monitor_running: false, refresh_margin_s: 600, tokens: {} },
  routerClassify: { tier: 'default', score: 1, reason: 'standard query' },
}

function MOCK_NOTICES_AS_ITEMS() {
  return [
    { id: 'n1', name: 'Heartbeat: uplink reachable.', status: 'open' },
    { id: 'n2', name: 'Security scan found 1 critical issue.', status: 'open' },
  ]
}

// In-memory mutable state so POST/PUT/DELETE round-trip realistically.
function freshStore() {
  return {
    memory: JSON.parse(JSON.stringify(MOCK.memory)),
    notices: JSON.parse(JSON.stringify(MOCK.notices)),
    workflows: JSON.parse(JSON.stringify(MOCK.workflows)),
  }
}

export async function installMockApi(page) {
  const store = freshStore()

  await page.route('**/api/**', async (route) => {
    const req = route.request()
    const url = new URL(req.url())
    const path = url.pathname
    const method = req.method()
    const body = req.postDataJSON ? req.postDataJSON() : null

    const json = (obj) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(obj) })

    try {
      // Memory
      if (path === '/api/memory' && method === 'GET') return json(store.memory)
      if (path === '/api/memory' && method === 'POST') {
        const fact = { id: `m${Date.now()}`, text: body?.text || '', category: body?.category || 'general' }
        store.memory.push(fact)
        return json(fact)
      }
      if (/^\/api\/memory\/[^/]+$/.test(path) && method === 'PUT') return json({ ok: true })
      if (/^\/api\/memory\/[^/]+$/.test(path) && method === 'DELETE') {
        const id = path.split('/').pop()
        store.memory = store.memory.filter(m => m.id !== id)
        return json({ ok: true })
      }

      // Notices
      if (path === '/api/notices' && method === 'GET') return json(store.notices)
      if (/^\/api\/notices\/[^/]+$/.test(path) && method === 'DELETE') {
        const id = path.split('/').pop()
        store.notices = store.notices.filter(n => n.id !== id)
        return json({ ok: true })
      }

      // Heartbeat
      if (path === '/api/heartbeat/kill' && method === 'POST') return json({ ok: true })
      if (path === '/api/heartbeat/resume' && method === 'POST') return json({ ok: true })
      if (path === '/api/config/heartbeat' && method === 'GET') return json(MOCK.settings.heartbeat)
      if (path === '/api/config/heartbeat' && method === 'PUT') return json({ ok: true })

      // Tasks / Tools / Agents / Status / Analytics / Audit
      if (path === '/api/tasks' && method === 'GET') return json(MOCK.tasks)
      if (path === '/api/tools' && method === 'GET') return json(MOCK.tools)
      if (path === '/api/agents' && method === 'GET') return json(MOCK.agents)
      if (path === '/api/status' && method === 'GET') return json(MOCK.status)
      if (path === '/api/analytics' && method === 'GET') return json(MOCK.analytics)
      if (path === '/api/audit' && method === 'GET') return json(MOCK.audit)

      // Models / Uplink / Ollama
      if (path === '/api/models' && method === 'GET') return json(MOCK.models)
      if (path === '/api/uplink' && method === 'GET') return json(MOCK.uplink)
      if (path === '/api/ollama/status' && method === 'GET') return json(MOCK.ollama)

      // Voice
      if (path === '/api/voice/stt' && method === 'POST') return json({ text: 'hello dela' })
      if (path === '/api/voice/tts' && method === 'POST') return route.fulfill({ status: 200, contentType: 'audio/wav', body: Buffer.alloc(44) })

      // State browser
      if (path === '/api/state' && method === 'GET') return json(MOCK.stateTypes)
      if (path === '/api/state/search' && method === 'GET') return json(MOCK.stateSearch)
      if (/^\/api\/state\/memory$/.test(path) && method === 'GET') return json(MOCK.stateMemory)
      if (/^\/api\/state\/notices$/.test(path) && method === 'GET') return json(MOCK.stateNotices)
      if (/^\/api\/state\/[^/]+$/.test(path) && method === 'GET') return json({ items: [] })
      if (/^\/api\/state\/[^/]+\/[^/]+$/.test(path) && method === 'GET') return json({ id: path.split('/').pop() })
      if (/^\/api\/state\/[^/]+\/[^/]+$/.test(path) && method === 'PUT') return json({ ok: true })

      // Security
      if (path === '/api/security' && method === 'GET') return json(MOCK.security)
      if (path === '/api/security/scan' && method === 'POST') return json(MOCK.security)
      if (path === '/api/security/fix' && method === 'POST') return json({ result: 'Recommend adding an input filter at provider seam.' })
      if (path === '/api/vuln-kb' && method === 'GET') return json(MOCK.vulnKb)
      if (path === '/api/vuln-kb/refresh' && method === 'POST') return json({ ok: true })

      // Workflows
      if (path === '/api/workflows' && method === 'GET') return json(store.workflows)
      if (path === '/api/workflows' && method === 'POST') {
        const wf = { name: body?.name, description: body?.description || '', steps: (body?.steps || []).length, schedule: body?.schedule || '' }
        store.workflows.push(wf)
        return json({ ok: true })
      }
      if (/^\/api\/workflows\/[^/]+$/.test(path) && method === 'GET') return json(MOCK.workflowDetail)
      if (/^\/api\/workflows\/[^/]+$/.test(path) && method === 'DELETE') {
        const name = decodeURIComponent(path.split('/').pop())
        store.workflows = store.workflows.filter(w => w.name !== name)
        return json({ ok: true })
      }
      if (/^\/api\/workflows\/[^/]+\/run$/.test(path) && method === 'POST') return json({ completed: 2, total: 2, failed: 0, results: { s1: 'ok', s2: 'ok' } })

      // Model router
      if (path === '/api/model-router/classify' && method === 'GET') return json(MOCK.routerClassify)

      // Settings
      if (path === '/api/settings' && method === 'GET') return json(MOCK.settings)
      if (path === '/api/settings/heartbeat' && method === 'PUT') return json({ ok: true })
      if (path === '/api/settings/env' && method === 'PUT') return json({ ok: true })
      if (path === '/api/settings/profile' && method === 'PUT') return json({ ok: true })
      if (path === '/api/settings/live' && method === 'GET') return json(MOCK.settings.live)
      if (path === '/api/settings/live' && method === 'PUT') return json({ ok: true })
      if (/^\/api\/settings\/live\/[^/]+$/.test(path) && method === 'DELETE') return json({ ok: true })

      // Connections / OAuth
      if (path === '/api/connections' && method === 'GET') return json(MOCK.connections)
      if (path === '/api/connections' && method === 'POST') return json({ ok: true })
      if (path === '/api/connections/assign' && method === 'PUT') return json({ ok: true })
      if (/^\/api\/connections\/[^/]+\/test$/.test(path) && method === 'POST') return json({ ok: true, message: 'Connection OK', models: ['glm-5.2'] })
      if (/^\/api\/connections\/[^/]+$/.test(path) && method === 'GET') return json({ name: 'x', base_url: '', model: '', auth_type: 'simple' })
      if (/^\/api\/connections\/[^/]+$/.test(path) && method === 'DELETE') return json({ ok: true })
      if (path === '/api/oauth/status' && method === 'GET') return json(MOCK.oauthStatus)
      if (path === '/api/oauth/refresh' && method === 'POST') return json({ ok: true })

      return json({ ok: true, _unmocked: path })
    } catch (e) {
      return route.fulfill({ status: 500, body: `mock error: ${e.message}` })
    }
  })
}
