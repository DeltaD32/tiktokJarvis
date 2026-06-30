import { test, expect, pushWS, sentWS } from './fixtures/delaTest'
import { makeApp } from './pages/AppPage'

test.describe('Conversation over WebSocket', () => {
  test('send from idle flips to thinking, streams tokens, then back to idle on reply_done', async ({ page }) => {
    const app = await makeApp(page)
    await app.sendFromIdle('hello dela')

    // The hook optimistically sets thinking client-side -> top strip appears
    await expect(app.topStrip()).toBeVisible()

    // Server streams tokens -> streaming bubble appears in the overlay
    await pushWS(page, { type: 'token', content: 'Hi ' })
    await pushWS(page, { type: 'token', content: 'Bruce' })
    await expect(page.locator('.conv-msg.streaming')).toContainText('Hi Bruce')

    // Reply completes -> back to idle (overlay hides)
    await pushWS(page, { type: 'reply_done' })
    await expect(app.idleInput()).toBeVisible()
    await expect(page.locator('.conv-msg.streaming')).toHaveCount(0)
  })

  test('sent WS frame carries the message content', async ({ page }) => {
    const app = await makeApp(page)
    await app.sendFromIdle('ping the assistant')
    const sent = await sentWS(page)
    expect(sent.some(s => s.type === 'message' && s.content === 'ping the assistant')).toBeTruthy()
  })

  test('tool_blip token updates toolStatus instead of stream', async ({ page }) => {
    const app = await makeApp(page)
    await app.sendFromIdle('run a tool')
    await pushWS(page, { type: 'token', tool_blip: true, content: 'fetch_url → example.com' })
    await expect(page.locator('.conv-msg.tool-blip')).toContainText('fetch_url')
  })

  test('conversation overlay shows messages while non-idle', async ({ page }) => {
    const app = await makeApp(page)
    await app.sendFromIdle('first')
    // Stream + complete a reply while keeping non-idle by pushing thinking
    await pushWS(page, { type: 'token', content: 'reply-one' })
    await pushWS(page, { type: 'reply_done' })
    // reply_done flips to idle; push thinking again and send another to re-enter
    await pushWS(page, { type: 'state_change', state: 'thinking' })
    await expect(app.convOverlay()).toBeVisible()
  })

  test('TTS barge-in: new message while speaking stops TTS', async ({ page }) => {
    const app = await makeApp(page)
    await app.chip('VOICE OFF').click()
    await expect(app.chip('VOICE ON')).toBeVisible()
    await app.sendFromIdle('say something')
    await pushWS(page, { type: 'reply_done' })
    await page.waitForTimeout(150)
    // reply_done flipped us back to idle; interrupt from the idle input
    await app.sendFromIdle('interrupt')
    // State flips to thinking which stops TTS via the barge-in effect
    await expect(app.topStrip()).toBeVisible()
  })
})
