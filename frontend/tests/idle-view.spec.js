import { test, expect } from './fixtures/delaTest'
import { makeApp } from './pages/AppPage'

test.describe('Idle view', () => {
  test('renders logo, subtitle, input, and EXECUTE', async ({ page }) => {
    const app = await makeApp(page)
    await expect(page.locator('.idle-logo')).toHaveText('DELA')
    await expect(page.locator('.idle-subtitle')).toContainText('awaiting your directive')
    await expect(app.idleInput()).toBeVisible()
    await expect(app.executeBtn()).toBeVisible()
    await expect(app.micBtn()).toBeVisible()
  })

  test('shows four corner stats with live values', async ({ page }) => {
    const app = await makeApp(page)
    await expect(app.cornerStat('HEARTBEAT')).toContainText('ACTIVE')
    await expect(app.cornerStat('TOOLS')).toContainText('5')   // mock has 5 tools
    await expect(app.cornerStat('UPLINK')).toContainText('LINKED')
    await expect(app.cornerStat('UPLINK')).toContainText('glm-5.2')
    await expect(app.cornerStat('AGENTS')).toContainText('5')
  })

  test('renders agent roster with status dots and dispatch counts', async ({ page }) => {
    const app = await makeApp(page)
    await expect(app.agentRosterItem('researcher')).toBeVisible()
    await expect(app.agentRosterItem('secretary')).toBeVisible()
    await expect(app.agentRosterItem('secretary').locator('.agent-dispatch-count')).toHaveText('12')
  })

  test('quick-start chips are clickable', async ({ page }) => {
    const app = await makeApp(page)
    await expect(app.chip('What can you do?')).toBeVisible()
    await expect(app.chip('Search memory')).toBeVisible()
    await expect(app.chip('Analytics')).toBeVisible()
  })

  test('VOICE OFF chip toggles to VOICE ON and back', async ({ page }) => {
    const app = await makeApp(page)
    const off = app.chip('VOICE OFF')
    await expect(off).toBeVisible()
    await off.click()
    await expect(app.chip('VOICE ON')).toBeVisible()
    await app.chip('VOICE ON').click()
    await expect(app.chip('VOICE OFF')).toBeVisible()
  })

  test('What can you do? chip sends a message and leaves idle', async ({ page }) => {
    const app = await makeApp(page)
    await app.chip('What can you do?').click()
    // sendMessage sets orbState to 'thinking' immediately (client-side)
    await expect(page.locator('.top-strip')).toBeVisible()
  })
})
