import { test as base, expect } from '@playwright/test'

const BACKEND_UP = process.env.DELA_E2E_AVAILABLE === '1'

// Real-backend specs. These run against `python start_dela.py` (or any Dela
// backend on :8000) plus the vite dev server. They're skipped automatically
// when the backend isn't reachable, so `npx playwright test` always works
// for the mocked suite; run the e2e suite with the backend up:
//
//   python start_dela.py         # in another terminal
//   npx playwright test --project=e2e

const test = base.extend({})

test.beforeAll(() => {
  test.skip(!BACKEND_UP, 'Dela backend not reachable on :8000 — run `python start_dela.py`')
})

test.describe('E2E smoke against real backend', () => {
  test('app loads, idle view renders, uplink stat is populated', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('.app')).toBeVisible()
    await expect(page.locator('.idle-logo')).toHaveText('DELA')
    // Wait for /api/uplink to resolve (status text appears)
    await expect(page.locator('.idle-corner-stat', { has: page.locator('.label', { hasText: 'UPLINK' }) })).toBeVisible({ timeout: 15000 })
  })

  test('tools count from real /api/tools', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('.app')).toBeVisible()
    const toolsStat = page.locator('.idle-corner-stat', { has: page.locator('.label', { hasText: 'TOOLS' }) })
    await expect(toolsStat).toBeVisible({ timeout: 15000 })
    const value = (await toolsStat.locator('.value').innerText()).trim()
    expect(Number(value)).toBeGreaterThan(0)
  })

  test('opening the MEMORY panel hits the real /api/memory', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('.app')).toBeVisible()
    const memResp = page.waitForResponse(r => r.url().includes('/api/memory') && r.request().method() === 'GET')
    await page.locator('.data-btn', { hasText: /^MEMORY/ }).click()
    const resp = await memResp
    expect(resp.ok()).toBeTruthy()
    await expect(page.locator('.holo-panel', { has: page.locator('.panel-title', { hasText: 'Memory' }) })).toBeVisible()
  })
})
