import { chromium } from "playwright";
import { config } from "../config.js";
import {
  applyAntiBotContext,
  getContextOptions,
  getLaunchOptions
} from "./playwright-options.js";
import { ensureDir } from "../utils/fs.js";

export class BrowserManager {
  constructor() {
    this.browser = null;
  }

  async start() {
    if (!this.browser) {
      this.browser = await chromium.launch(getLaunchOptions());
    }

    return this.browser;
  }

  buildContextOptions({ lightweight = true } = {}) {
    return getContextOptions({ lightweight });
  }

  async prepareContext(context) {
    await applyAntiBotContext(context);
  }

  async bootstrapSession(url = config.site.baseUrl) {
    ensureDir(config.paths.sessionDir);
    const context = await chromium.launchPersistentContext(config.paths.sessionDir, {
      ...this.buildContextOptions({ lightweight: false }),
      ...getLaunchOptions({ headless: false })
    });
    await this.prepareContext(context);
    const page = context.pages()[0] || (await context.newPage());
    page.setDefaultTimeout(config.browser.bootstrapTimeoutMs);
    await page.goto(url, { waitUntil: "domcontentloaded" });

    return {
      context,
      page,
      save: async () => {
        await context.storageState({ path: config.paths.storageStateFile });
      }
    };
  }

  async close() {
    if (this.browser) {
      await this.browser.close();
      this.browser = null;
    }
  }
}
