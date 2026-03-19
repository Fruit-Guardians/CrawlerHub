import fs from "node:fs";
import { config } from "../config.js";

export function getLaunchOptions({ headless = config.browser.headless } = {}) {
  const launchOptions = {
    headless,
    args: config.browser.launchArgs
  };

  if (config.browser.channel) {
    launchOptions.channel = config.browser.channel;
  }

  if (config.browser.executablePath) {
    launchOptions.executablePath = config.browser.executablePath;
  }

  return launchOptions;
}

export function getContextOptions({ lightweight = true } = {}) {
  const options = {
    locale: config.browser.locale,
    timezoneId: config.browser.timezoneId,
    userAgent: config.browser.userAgent,
    viewport: lightweight ? config.browser.viewport : { width: 1600, height: 1200 }
  };

  if (fs.existsSync(config.paths.storageStateFile)) {
    options.storageState = config.paths.storageStateFile;
  }

  return options;
}

export async function applyAntiBotContext(context) {
  await context.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", {
      get: () => undefined
    });

    Object.defineProperty(navigator, "languages", {
      get: () => ["zh-CN", "zh", "en-US", "en"]
    });

    Object.defineProperty(navigator, "plugins", {
      get: () => [1, 2, 3, 4, 5]
    });

    window.chrome = window.chrome || { runtime: {} };
  });
}
