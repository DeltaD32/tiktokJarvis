import { test, expect, pushWS } from './fixtures/delaTest'
import { makeApp, AppPage } from './pages/AppPage'

test.describe('Floating windows', () => {
  test.beforeEach(async ({ page }) => {
    const app = await makeApp(page)
    await app.sendFromIdle('activate')
  })

  test('THE HIVE opens, lists 5 agents with status badges, closes', async ({ page }) => {
    const app = new AppPage(page)
    await app.dockPill('THE HIVE').click()
    const win = app.floatWindow('THE HIVE')
    await expect(win).toBeVisible()
    await expect(win.locator('.agent-card')).toHaveCount(5)
    await expect(win.locator('.agent-card', { has: page.locator('.agent-name', { hasText: 'secretary' }) }).locator('.agent-status-badge')).toContainText('BUSY')
    await expect(win.locator('.agent-card', { has: page.locator('.agent-name', { hasText: 'system_expert' }) }).locator('.agent-status-badge')).toContainText('ERROR')
    await app.floatClose('THE HIVE').click()
    await expect(win).toHaveCount(0)
  })

  test('STREAM opens and shows conversation/stream content', async ({ page }) => {
    const app = new AppPage(page)
    // beforeEach left us thinking; push a streaming token so the stream window has content
    await pushWS(page, { type: 'token', content: 'streaming-reply' })
    await app.dockPill('THE STREAM').click()
    await expect(app.floatWindow('THE STREAM')).toBeVisible()
  })

  test('SANDBOX opens and closes', async ({ page }) => {
    const app = new AppPage(page)
    await app.dockPill('SANDBOX').click()
    const win = app.floatWindow('SANDBOX')
    await expect(win).toBeVisible()
    await app.floatClose('SANDBOX').click()
    await expect(win).toHaveCount(0)
  })

  test('focusing a window raises its z-index above others', async ({ page }) => {
    const app = new AppPage(page)
    await app.dockPill('THE HIVE').click()
    await app.dockPill('SANDBOX').click()
    const hive = app.floatWindow('THE HIVE')
    const sandbox = app.floatWindow('SANDBOX')
    // Both visible
    await expect(hive).toBeVisible()
    await expect(sandbox).toBeVisible()
    // Click hive header to focus it
    await app.floatHeader('THE HIVE').click()
    const hiveZ = await hive.evaluate(el => getComputedStyle(el).zIndex)
    const sandboxZ = await sandbox.evaluate(el => getComputedStyle(el).zIndex)
    expect(Number(hiveZ)).toBeGreaterThan(Number(sandboxZ))
  })

  test('dragging a window moves it', async ({ page }) => {
    const app = new AppPage(page)
    await app.dockPill('THE HIVE').click()
    const win = app.floatWindow('THE HIVE')
    const header = app.floatHeader('THE HIVE')
    const boxBefore = await win.boundingBox()
    const headerBox = await header.boundingBox()
    // Press on the header, then move by a known delta
    await page.mouse.move(headerBox.x + 20, headerBox.y + 8)
    await page.mouse.down()
    await page.mouse.move(headerBox.x + 20 + 120, headerBox.y + 8 + 60, { steps: 12 })
    await page.mouse.up()
    const boxAfter = await win.boundingBox()
    expect(Math.abs((boxAfter.x - boxBefore.x) - 120)).toBeLessThan(15)
    expect(Math.abs((boxAfter.y - boxBefore.y) - 60)).toBeLessThan(15)
  })
})
