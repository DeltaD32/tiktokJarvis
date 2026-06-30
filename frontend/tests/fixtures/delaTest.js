import { test as base, expect } from '@playwright/test'
import { installMockApi } from './mockApi'
import { MOCK_WS_INIT_SCRIPT } from './mockWS'

// `page` here is auto-wired with REST mocks + a mock WebSocket before any app
// code runs. Specs that import { test, expect } from this file get mocks for
// free; specs that want the real backend should import from '@playwright/test'
// directly and live under tests/e2e/.
export const test = base.extend({
  page: async ({ page }, use) => {
    await installMockApi(page)
    await page.addInitScript(MOCK_WS_INIT_SCRIPT)
    await use(page)
  },
})

export { expect }

// Convenience: push a server-style WS message into the app from a test.
export async function pushWS(page, msg) {
  await page.evaluate(m => window.__mockWSPush(m), msg)
}

export async function sentWS(page) {
  return page.evaluate(() => window.__mockWSGetSent())
}

export async function closeWS(page) {
  await page.evaluate(() => window.__mockWSCloseLast())
}

export async function setWSInit(page, initMsg) {
  await page.evaluate(m => { window.__mockWSInit = m }, initMsg)
}
