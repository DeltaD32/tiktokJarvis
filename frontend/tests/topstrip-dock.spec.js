import { test, expect, pushWS } from './fixtures/delaTest'
import { makeApp, AppPage } from './pages/AppPage'

test.describe('Top strip + dock (non-idle state)', () => {
  test.beforeEach(async ({ page }) => {
    const app = await makeApp(page)
    await app.sendFromIdle('activate')
  })

  test('top strip shows state label, input, RUN, cost', async ({ page }) => {
    const app = new AppPage(page)
    await expect(app.topStrip()).toBeVisible()
    await expect(app.topStrip()).toContainText('DELA')
    await expect(app.topStripInput()).toBeVisible()
    await expect(app.runBtn()).toBeVisible()
    // cost from init = '$0.0000'
    await expect(app.topStrip()).toContainText('COST')
  })

  test('dock shows heartbeat, hive, stream, sandbox pills', async ({ page }) => {
    const app = new AppPage(page)
    await expect(app.dockPill('HEARTBEAT')).toBeVisible()
    await expect(app.dockPill('THE HIVE')).toBeVisible()
    await expect(app.dockPill('THE STREAM')).toBeVisible()
    await expect(app.dockPill('SANDBOX')).toBeVisible()
  })

  test('heartbeat pill toggles ON/OFF via click and calls /api/heartbeat/kill', async ({ page }) => {
    const app = new AppPage(page)
    const pill = app.dockPill('HEARTBEAT')
    await expect(pill.locator('.dock-value')).toHaveText('ON')
    await pill.click()
    await expect(pill.locator('.dock-value')).toHaveText('OFF')
    // clicking again resumes
    await pill.click()
    await expect(pill.locator('.dock-value')).toHaveText('ON')
  })

  test('dock pills toggle their floating windows', async ({ page }) => {
    const app = new AppPage(page)
    await app.dockPill('THE HIVE').click()
    await expect(app.floatWindow('THE HIVE')).toBeVisible()
    await app.dockPill('THE HIVE').click()
    await expect(app.floatWindow('THE HIVE')).toHaveCount(0)
  })

  test('MINIMIZE ALL closes every open floating window', async ({ page }) => {
    const app = new AppPage(page)
    await app.dockPill('THE HIVE').click()
    await app.dockPill('SANDBOX').click()
    await expect(app.floatWindow('THE HIVE')).toBeVisible()
    await expect(app.floatWindow('SANDBOX')).toBeVisible()
    await page.locator('.dock-pill', { hasText: 'MINIMIZE ALL' }).click()
    await expect(app.floatWindow('THE HIVE')).toHaveCount(0)
    await expect(app.floatWindow('SANDBOX')).toHaveCount(0)
  })

  test('NOTICES pill appears in dock when noticeCount > 0', async ({ page }) => {
    const app = new AppPage(page)
    await pushWS(page, { type: 'notice', notice: { id: 'x1', message: 'Test notice', severity: 'info', source: 'test', created_at: Math.floor(Date.now()/1000) } })
    await expect(app.dockPill('NOTICES')).toBeVisible()
  })
})
