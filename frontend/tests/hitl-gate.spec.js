import { test, expect, pushWS, sentWS } from './fixtures/delaTest'
import { makeApp, AppPage } from './pages/AppPage'

test.describe('HITL confirmation gate', () => {
  test('confirmation_request shows the gate with description and APPROVE/DENY', async ({ page }) => {
    const app = await makeApp(page)
    await pushWS(page, {
      type: 'confirmation_request',
      id: 'cf-1',
      description: 'Permanently delete task "Ship voice barge-in fix"?',
    })
    await expect(app.hitlGate()).toBeVisible()
    await expect(app.hitlGate()).toContainText('HUMAN-IN-THE-LOOP GATE')
    await expect(app.hitlGate()).toContainText('delete task')
    await expect(app.hitlApprove()).toBeVisible()
    await expect(app.hitlDeny()).toBeVisible()
  })

  test('APPROVE sends confirm:true and clears the gate', async ({ page }) => {
    const app = await makeApp(page)
    await pushWS(page, { type: 'confirmation_request', id: 'cf-2', description: 'Send an email?' })
    await app.hitlApprove().click()
    await expect(app.hitlGate()).toHaveCount(0)
    const sent = await sentWS(page)
    expect(sent.some(s => s.type === 'confirm' && s.id === 'cf-2' && s.approved === true)).toBeTruthy()
  })

  test('DENY sends confirm:false and clears the gate', async ({ page }) => {
    const app = await makeApp(page)
    await pushWS(page, { type: 'confirmation_request', id: 'cf-3', description: 'Spend $50?' })
    await app.hitlDeny().click()
    await expect(app.hitlGate()).toHaveCount(0)
    const sent = await sentWS(page)
    expect(sent.some(s => s.type === 'confirm' && s.id === 'cf-3' && s.approved === false)).toBeTruthy()
  })

  test('SPACE key approves the active gate', async ({ page }) => {
    const app = await makeApp(page)
    await pushWS(page, { type: 'confirmation_request', id: 'cf-4', description: 'Delete data?' })
    await expect(app.hitlGate()).toBeVisible()
    await page.keyboard.press('Space')
    await expect(app.hitlGate()).toHaveCount(0)
    const sent = await sentWS(page)
    expect(sent.some(s => s.type === 'confirm' && s.id === 'cf-4' && s.approved === true)).toBeTruthy()
  })

  test('no gate renders without a confirmation_request', async ({ page }) => {
    await makeApp(page)
    const app = new AppPage(page)
    await expect(app.hitlGate()).toHaveCount(0)
  })
})
