import { test, expect } from './fixtures/delaTest'
import { makeApp } from './pages/AppPage'

test.describe('Slide-in panels', () => {
  test.beforeEach(async ({ page }) => {
    await makeApp(page)
  })

  test('MEMORY panel lists facts, add/edit/delete controls render', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('MEMORY')
    const panel = app.holoPanel('Memory')
    await expect(panel).toBeVisible()
    await expect(panel.locator('.panel-item-title', { hasText: 'morning meetings' })).toBeVisible()
    await expect(panel.locator('.panel-item-title', { hasText: 'Bruce' })).toBeVisible()
    // add-new controls present
    await expect(panel.locator('textarea').last()).toBeVisible()
    await expect(panel.locator('button', { hasText: 'add' })).toBeVisible()
    await app.closePanel()
    await expect(panel).toHaveCount(0)
  })

  test('STATE BROWSER panel lists state types and search box', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('STATE')
    const panel = app.holoPanel('State Browser')
    await expect(panel).toBeVisible()
    await expect(panel.locator('.panel-item-title', { hasText: 'memory' })).toBeVisible()
    await expect(panel.locator('.panel-item-title', { hasText: 'notices' })).toBeVisible()
    await expect(panel.locator('input[placeholder="Search all state..."]')).toBeVisible()
  })

  test('TOOLS panel lists tools with SAFE/CONFIRM badges + agent tab', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('TOOLS')
    const panel = app.holoPanel('Tool Browser')
    await expect(panel).toBeVisible()
    await expect(panel.locator('.panel-item-title', { hasText: 'fetch_url' })).toBeVisible()
    await expect(panel.locator('.panel-item-title', { hasText: 'delete_task' })).toBeVisible()
    // switch to agents tab
    await panel.locator('button.data-btn', { hasText: 'AGENTS' }).click()
    await expect(panel.locator('.panel-item-title', { hasText: 'researcher' })).toBeVisible()
  })

  test('AUDIT panel shows log and cost', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('AUDIT')
    const panel = app.holoPanel('Audit Log')
    await expect(panel).toBeVisible()
    await expect(panel.locator('.audit-log')).toContainText('gate granted')
    await expect(panel).toContainText('Total cost')
  })

  test('NOTICES panel renders notices and dismiss button', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('NOTICES')
    const panel = app.holoPanel('Notices')
    await expect(panel).toBeVisible()
    await expect(panel.locator('.panel-item-title', { hasText: 'uplink reachable' })).toBeVisible()
    await expect(panel.locator('button', { hasText: 'dismiss' })).toHaveCount(2)
  })

  test('TASKS panel splits open vs done', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('TASKS')
    const panel = app.holoPanel('Task List')
    await expect(panel).toBeVisible()
    await expect(panel.locator('text=OPEN — 2')).toBeVisible()
    await expect(panel.locator('text=COMPLETED — 1')).toBeVisible()
    await expect(panel.locator('.panel-item-title', { hasText: 'Set up Ollama profile' })).toHaveCSS('text-decoration-line', 'line-through')
  })

  test('SECURITY panel shows score, summary, findings, checklist tab', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('SECURITY')
    const panel = app.holoPanel('Security Audit')
    await expect(panel).toBeVisible()
    await expect(panel.locator('text=78')).toBeVisible()  // score
    await expect(panel.locator('.panel-item-title', { hasText: 'Hardcoded secret' })).toBeVisible()
    // RECOMMEND FIX button present on actionable finding
    await expect(panel.locator('button', { hasText: 'RECOMMEND FIX' }).first()).toBeVisible()
    // switch to checklist tab
    await panel.locator('button.data-btn', { hasText: 'CHECKLIST' }).click()
    await expect(panel.locator('.panel-item-title', { hasText: 'Prompt Injection' })).toBeVisible()
  })

  test('SETTINGS panel renders 8 section tabs and general view', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('SETTINGS')
    const panel = app.holoPanel('Settings')
    await expect(panel).toBeVisible()
    for (const label of ['PROFILE', 'GENERAL', 'CONNECTIONS', 'ROUTER', 'VOICE', 'THEME', 'HEARTBEAT', 'ENV VARS']) {
      await expect(panel.locator('button.sandbox-tab', { hasText: label })).toBeVisible()
    }
    // General is the default section — assistant name field present
    await expect(panel.locator('text=ASSISTANT NAME')).toBeVisible()
  })

  test('ANALYTICS panel shows model calls, cost, tool usage', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('ANALYTICS')
    const panel = app.holoPanel('ANALYTICS')
    await expect(panel).toBeVisible()
    await expect(panel.locator('.analytics-label', { hasText: 'MODEL CALLS' })).toBeVisible()
    await expect(panel.locator('.analytics-label', { hasText: 'TOOL CALLS' })).toBeVisible()
    await expect(panel.locator('.analytics-label', { hasText: 'GATE DECISIONS' })).toBeVisible()
    await expect(panel.getByText('TOOL USAGE BREAKDOWN')).toBeVisible()
  })

  test('WORKFLOWS panel lists workflows and + NEW button', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('WORKFLOWS')
    const panel = app.holoPanel('Workflow Designer')
    await expect(panel).toBeVisible()
    await expect(panel.locator('.panel-item-title', { hasText: 'morning-briefing' })).toBeVisible()
    await expect(panel.locator('button', { hasText: /\+ NEW/ })).toBeVisible()
  })

  test('opening a second panel replaces the first (only one holo-panel at a time)', async ({ page }) => {
    const app = await makeApp(page)
    await app.openPanel('MEMORY')
    await expect(app.holoPanel('Memory')).toBeVisible()
    await app.openPanel('AUDIT')
    await expect(app.holoPanel('Audit Log')).toBeVisible()
    await expect(app.holoPanel('Memory')).toHaveCount(0)
  })
})
