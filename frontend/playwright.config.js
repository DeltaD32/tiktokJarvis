import { defineConfig } from '@playwright/test'

const E2E_BASE_URL = process.env.DELA_E2E_BASE_URL || 'http://localhost:8000'

async function e2eGate() {
  let up = false
  try {
    const res = await fetch(`${E2E_BASE_URL}/api/status`, { signal: AbortSignal.timeout(1500) })
    up = res.ok
  } catch {
    up = false
  }
  process.env.DELA_E2E_AVAILABLE = up ? '1' : '0'
  if (!up) console.log(`[e2e] backend not reachable at ${E2E_BASE_URL} — skipping e2e suite`)
}

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['list'], ['html', { open: 'never' }]],
  expect: { timeout: 5000 },
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 8000,
  },
  projects: [
    {
      name: 'mocked',
      testMatch: /tests\/(?!e2e\/).*\.spec\.js$/,
      use: { browserName: 'chromium' },
    },
    {
      name: 'e2e',
      testMatch: /tests\/e2e\/.*\.spec\.js$/,
      globalSetup: './tests/e2e/globalSetup.js',
      use: { browserName: 'chromium' },
    },
  ],
  webServer: {
    command: 'npm.cmd run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 60000,
    cwd: '.',
  },
})

export { e2eGate }
