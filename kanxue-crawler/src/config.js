import path from "node:path";

const rootDir = process.cwd();
const dataDir = path.join(rootDir, "data");

export const config = {
  site: {
    name: "Kanxue",
    baseUrl: "https://www.kanxue.com/",
    allowedHosts: ["www.kanxue.com", "kanxue.com", "bbs.kanxue.com"]
  },
  paths: {
    rootDir,
    dataDir,
    crawleeDir: path.join(dataDir, "crawlee"),
    rawDir: path.join(dataDir, "raw"),
    jsonDir: path.join(dataDir, "json"),
    markdownDir: path.join(dataDir, "markdown"),
    assetDir: path.join(dataDir, "assets"),
    dbDir: path.join(dataDir, "db"),
    dbFile: path.join(dataDir, "db", "kanxue.sqlite"),
    logDir: path.join(rootDir, "logs"),
    sessionDir: path.join(dataDir, "session"),
    storageStateFile: path.join(dataDir, "session", "kanxue-storage-state.json")
  },
  browser: {
    headless: true,
    timeoutMs: 45000,
    navigationWaitUntil: "domcontentloaded",
    locale: "zh-CN",
    timezoneId: "Asia/Shanghai",
    channel: process.env.KANXUE_BROWSER_CHANNEL || "",
    executablePath: process.env.KANXUE_BROWSER_EXECUTABLE || "",
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    viewport: { width: 1440, height: 1200 },
    bootstrapTimeoutMs: 600000,
    launchArgs: [
      "--disable-blink-features=AutomationControlled",
      "--disable-dev-shm-usage",
      "--disable-features=IsolateOrigins,site-per-process",
      "--disable-infobars",
      "--no-default-browser-check",
      "--start-maximized"
    ]
  },
  concurrency: {
    discovery: 2,
    detail: 2
  },
  maxDiscoveryDepth: 2,
  crawl: {
    maxRequestsPerRun: 300,
    maxArticleRequestsPerRun: 80,
    requestHandlerTimeoutSecs: 90,
    navigationTimeoutSecs: 60
  },
  retry: {
    maxAttempts: 3
  },
  export: {
    downloadAssets: true
  }
};
