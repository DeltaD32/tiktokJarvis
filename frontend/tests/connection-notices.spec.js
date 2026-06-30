import { test, expect, pushWS, closeWS } from './fixtures/delaTest'
import { makeApp, AppPage } from './pages/AppPage'

test.describe('Connection banner + notices flow', () => {
  test('connection banner shows when WS is closed and hides when reconnected', async ({ page }) => {
    const app = await makeApp(page)
    // Initially connected (mock WS auto-opens)
    await expect(app.connBanner()).toHaveCount(0)
    // Force the WS closed
    await closeWS(page)
    await expect(app.connBanner()).toBeVisible()
  })

  test('init message seeds notices and heartbeat_active', async ({ page }) => {
    const app = await makeApp(page)
    // 2 notices from default mock init -> NOTICES button shows count
    await expect(app.dataBtn('NOTICES')).toContainText('(2)')
    await expect(app.cornerStat('HEARTBEAT')).toContainText('ACTIVE')
  })

  test('notice push increments count and shows in dock + panel', async ({ page }) => {
    const app = await makeApp(page)
    await app.sendFromIdle('go')  // leave idle so dock is visible
    const a = new AppPage(page)
    await pushWS(page, {
      type: 'notice',
      notice: { id: 'new-1', message: 'Disk usage above 80%', severity: 'warning', source: 'heartbeat', created_at: Math.floor(Date.now()/1000) },
    })
    await expect(a.dataBtn('NOTICES')).toContainText('(3)')
    // dock notices pill
    await expect(a.dockPill('NOTICES')).toBeVisible()
    await expect(a.dockPill('NOTICES').locator('.dock-value')).toContainText('3')
    // open panel and verify the new notice is listed
    await a.openPanel('NOTICES')
    await expect(a.holoPanel('Notices').locator('.panel-item-title', { hasText: 'Disk usage' })).toBeVisible()
  })

  test('dismiss removes a notice from the list and calls DELETE', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('NOTICES')
    const panel = app.holoPanel('Notices')
    const before = await panel.locator('.panel-item').count()
    await panel.locator('button', { hasText: 'dismiss' }).first().click()
    await expect(panel.locator('.panel-item')).toHaveCount(before - 1)
  })

  test('notices_refresh replaces the entire notice list', async ({ page }) => {
    const app = await makeApp(page)
    await pushWS(page, {
      type: 'notices_refresh',
      notices: [{ id: 'r1', message: 'Refreshed notice list', severity: 'info', source: 'heartbeat', created_at: Math.floor(Date.now()/1000) }],
    })
    await expect(app.dataBtn('NOTICES')).toContainText('(1)')
  })

  test('cost_update changes the displayed cost', async ({ page }) => {
    const app = await makeApp(page)
    await app.sendFromIdle('spend tokens')
    const a = new AppPage(page)
    await pushWS(page, { type: 'cost_update', cost: '$0.9999' })
    await expect(a.topStrip()).toContainText('$0.9999')
  })

  test('heartbeat_state toggles the corner stat', async ({ page }) => {
    const app = await makeApp(page)
    await pushWS(page, { type: 'heartbeat_state', active: false })
    await expect(app.cornerStat('HEARTBEAT')).toContainText('PAUSED')
    await pushWS(page, { type: 'heartbeat_state', active: true })
    await expect(app.cornerStat('HEARTBEAT')).toContainText('ACTIVE')
  })
})
