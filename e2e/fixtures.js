import { expect, test as base } from "@playwright/test"

/**
 * Specs that sign in several people open extra pages with
 * browser.newContext(). Playwright closes only the built-in page's context, so
 * the rest stayed open for the whole run, each still polling the server and
 * re-rendering. On a CI runner the browser slowed until clicks took seconds and
 * some never finished. Every context a test opens is closed when it ends.
 */
export const test = base.extend({
  closeExtraContexts: [
    async ({ browser }, use) => {
      const before = new Set(browser.contexts())
      await use()
      const opened = browser.contexts().filter((context) => !before.has(context))
      await Promise.all(opened.map((context) => context.close()))
    },
    // Closing saves each context's trace: give that its own time, not the test's.
    { auto: true, timeout: 60000 },
  ],
})

export { expect }
