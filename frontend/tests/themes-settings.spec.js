import { test, expect } from './fixtures/delaTest'
import { makeApp } from './pages/AppPage'

const THEMES = ['JARVIS', 'ULTRAVIOLET', 'SOLAR', 'FOREST', 'CRIMSON']

test.describe('Themes + settings tabs', () => {
  test('settings THEME tab shows all 5 themes', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('SETTINGS')
    const panel = app.holoPanel('Settings')
    await panel.locator('button.sandbox-tab', { hasText: 'THEME' }).click()
    for (const name of THEMES) {
      await expect(panel.locator('div', { hasText: new RegExp(`^${name}$`) }).first()).toBeVisible()
    }
  })

  test('clicking a theme applies it and persists to localStorage', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('SETTINGS')
    const panel = app.holoPanel('Settings')
    await panel.locator('button.sandbox-tab', { hasText: 'THEME' }).click()
    // Click the CRIMSON theme card (text inside a div)
    await panel.locator('div', { hasText: /^CRIMSON$/ }).first().click()
    const stored = await page.evaluate(() => localStorage.getItem('dela-theme'))
    expect(stored).toBe('crimson')
    // accent rgb should now be crimson idle color (255,80,80)
    const accent = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--accent-rgb').trim())
    expect(accent).toBe('255,80,80')
  })

  test('theme persists across reloads', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('SETTINGS')
    const panel = app.holoPanel('Settings')
    await panel.locator('button.sandbox-tab', { hasText: 'THEME' }).click()
    await panel.locator('div', { hasText: /^FOREST$/ }).first().click()
    await page.reload()
    await expect(page.locator('.app')).toBeVisible()
    const stored = await page.evaluate(() => localStorage.getItem('dela-theme'))
    expect(stored).toBe('forest')
  })

  test('PROFILE tab lists 3 profiles with ACTIVE badge on personal', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('SETTINGS')
    const panel = app.holoPanel('Settings')
    await panel.locator('button.sandbox-tab', { hasText: 'PROFILE' }).click()
    await expect(panel.getByText('PERSONAL', { exact: true })).toBeVisible()
    await expect(panel.getByText('WORK', { exact: true })).toBeVisible()
    await expect(panel.getByText('OFFLINE', { exact: true })).toBeVisible()
    await expect(panel.getByText('ACTIVE', { exact: true })).toBeVisible()
  })

  test('CONNECTIONS tab renders the per-profile assignment matrix', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('SETTINGS')
    const panel = app.holoPanel('Settings')
    await panel.locator('button.sandbox-tab', { hasText: 'CONNECTIONS' }).click()
    await expect(panel.getByText('API CONNECTIONS')).toBeVisible()
    // three profile rows
    await expect(panel.locator('select.chat-input')).toHaveCount(3)
  })

  test('ROUTER tab shows router-enabled live toggle', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('SETTINGS')
    const panel = app.holoPanel('Settings')
    await panel.locator('button.sandbox-tab', { hasText: 'ROUTER' }).click()
    await expect(panel.getByText('ROUTER ENABLED', { exact: true })).toBeVisible()
    await expect(panel.getByText('FAST MODEL', { exact: true })).toBeVisible()
    await expect(panel.getByText('PREMIUM MODEL', { exact: true })).toBeVisible()
  })

  test('VOICE tab shows whisper + piper live fields', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('SETTINGS')
    const panel = app.holoPanel('Settings')
    await panel.locator('button.sandbox-tab', { hasText: 'VOICE' }).click()
    await expect(panel.getByText('WHISPER MODEL', { exact: true })).toBeVisible()
    await expect(panel.getByText('PIPER VOICE', { exact: true })).toBeVisible()
    await expect(panel.getByText('VAD AGGRESSIVENESS', { exact: true })).toBeVisible()
  })

  test('HEARTBEAT tab shows interval + enabled checks', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('SETTINGS')
    const panel = app.holoPanel('Settings')
    await panel.locator('button.sandbox-tab', { hasText: 'HEARTBEAT' }).click()
    await expect(panel.getByText('INTERVAL (seconds)')).toBeVisible()
    await expect(panel.getByText('ENABLED CHECKS')).toBeVisible()
    await expect(panel.locator('.panel-item-title', { hasText: 'uplink' })).toBeVisible()
  })

  test('ENV VARS tab rejects keys not starting with DELA_', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('SETTINGS')
    const panel = app.holoPanel('Settings')
    await panel.locator('button.sandbox-tab', { hasText: 'ENV VARS' }).click()
    const inputs = panel.locator('input.chat-input')
    await inputs.nth(0).fill('BAD_KEY')
    await inputs.nth(1).fill('x')
    await panel.locator('button', { hasText: 'save (restart required)' }).click()
    await expect(panel.locator('text=Key must start with DELA_')).toBeVisible()
  })
})
