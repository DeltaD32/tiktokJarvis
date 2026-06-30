const E2E_BASE_URL = process.env.DELA_E2E_BASE_URL || 'http://localhost:8000'

export default async function e2eGate() {
  let up = false
  try {
    const res = await fetch(`${E2E_BASE_URL}/api/status`, { signal: AbortSignal.timeout(1500) })
    up = res.ok
  } catch {
    up = false
  }
  process.env.DELA_E2E_AVAILABLE = up ? '1' : '0'
  if (!up) console.log(`[e2e] backend not reachable at ${E2E_BASE_URL} — e2e specs will skip`)
}
