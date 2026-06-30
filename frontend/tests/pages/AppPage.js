import { expect } from '@playwright/test'

// Page object for the Dela/Jarvis Hub UI. Selectors are based on the
// className-based markup in frontend/src — the app has no data-testid hooks,
// so we lean on stable class names and text content.
export class AppPage {
  constructor(page) {
    this.page = page
  }

  async goto() {
    await this.page.goto('/')
    // Wait for the app shell to mount — the particle canvas is always present.
    await expect(this.page.locator('.app')).toBeVisible()
  }

  // --- Idle view -----------------------------------------------------------
  idleInput() { return this.page.locator('.idle-input') }
  micBtn() { return this.page.locator('.mic-btn') }
  executeBtn() { return this.page.locator('.execute-btn') }
  chip(text) { return this.page.locator('.chip', { hasText: text }) }
  cornerStat(label) {
    return this.page.locator('.idle-corner-stat', { has: this.page.locator('.label', { hasText: label }) })
  }
  agentRosterItem(name) {
    return this.page.locator('.agent-roster-item', { has: this.page.locator('.agent-name', { hasText: name }) })
  }

  async sendFromIdle(text) {
    await this.idleInput().fill(text)
    await this.idleInput().press('Enter')
  }

  // --- Top strip (non-idle) ------------------------------------------------
  topStrip() { return this.page.locator('.top-strip') }
  topStripInput() { return this.page.locator('.top-strip-input') }
  runBtn() { return this.page.locator('.run-btn') }

  async sendFromTopStrip(text) {
    await this.topStripInput().fill(text)
    await this.runBtn().click()
  }

  // --- Data panel buttons (top-right) -------------------------------------
  dataBtn(label) {
    return this.page.locator('.data-btn', { hasText: new RegExp(`^${label}`) })
  }
  async openPanel(label) { await this.dataBtn(label).click() }

  // --- Slide-in panel ------------------------------------------------------
  holoPanel(title) {
    return this.page.locator('.holo-panel', { has: this.page.locator('.panel-title', { hasText: title }) })
  }
  panelClose() { return this.page.locator('.panel-close') }
  async closePanel() { await this.panelClose().click() }

  // --- Dock + floating windows --------------------------------------------
  dock() { return this.page.locator('.dock') }
  dockPill(label) {
    return this.page.locator('.dock-pill', { has: this.page.locator('.dock-label', { hasText: label }) })
  }
  floatWindow(title) {
    return this.page.locator('.float-window', { has: this.page.locator('.float-title', { hasText: title }) })
  }
  floatClose(title) {
    return this.floatWindow(title).locator('.float-close')
  }
  floatHeader(title) {
    return this.floatWindow(title).locator('.float-header')
  }

  // --- HITL gate ----------------------------------------------------------
  hitlGate() { return this.page.locator('.hitl-overlay') }
  hitlApprove() { return this.page.locator('.hitl-approve') }
  hitlDeny() { return this.page.locator('.hitl-deny') }

  // --- Voice / connection banner ------------------------------------------
  voiceHud() { return this.page.locator('.voice-hud') }
  connBanner() { return this.page.locator('.conn-banner') }
  convOverlay() { return this.page.locator('.conv-overlay') }
  convMsg(role) { return this.page.locator(`.conv-msg.${role}`) }
}

export async function makeApp(page) {
  const app = new AppPage(page)
  await app.goto()
  return app
}
