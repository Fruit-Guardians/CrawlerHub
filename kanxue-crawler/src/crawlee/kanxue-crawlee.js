import { Dataset, PlaywrightCrawler, RequestQueue } from "crawlee";
import { config } from "../config.js";
import { classifyUrl } from "../discovery/url-classifier.js";
import { buildMarkdownDocument, extractLinks, parseArticle } from "../parser/article-parser.js";
import { FileStore } from "../store/file-store.js";
import { DEFAULT_SEEDS } from "../seeds/kanxue.js";
import { ensureDir } from "../utils/fs.js";
import { logger } from "../utils/logger.js";
import { nowIso } from "../utils/time.js";
import { getContextOptions, getLaunchOptions } from "../browser/playwright-options.js";

process.env.CRAWLEE_STORAGE_DIR = process.env.CRAWLEE_STORAGE_DIR || config.paths.crawleeDir;
ensureDir(config.paths.crawleeDir);

function detectBlockedPage({ title, bodyText, statusCode }) {
  const text = `${title || ""}\n${bodyText || ""}`.toLowerCase();
  return (
    (statusCode && statusCode >= 400) ||
    text.includes("安全验证") ||
    text.includes("请确认您不是机器人") ||
    text.includes("开始验证") ||
    text.includes("验证后1小时内无需重复验证")
  );
}

function normalizeSeedRequest(seed) {
  return {
    url: seed.url,
    userData: {
      label: "LIST",
      type: "list",
      depth: seed.depth ?? 0,
      source: seed.source ?? "seed"
    }
  };
}

export class KanxueCrawleeService {
  constructor({ db }) {
    this.db = db;
    this.fileStore = new FileStore();
  }

  async createCrawler({ mode }) {
    const requestQueue = await RequestQueue.open(`kanxue-${mode}-${Date.now()}`);

    const crawler = new PlaywrightCrawler({
      requestQueue,
      maxRequestRetries: config.retry.maxAttempts - 1,
      requestHandlerTimeoutSecs: config.crawl.requestHandlerTimeoutSecs,
      navigationTimeoutSecs: config.crawl.navigationTimeoutSecs,
      maxRequestsPerCrawl:
        mode === "crawl" ? config.crawl.maxArticleRequestsPerRun : config.crawl.maxRequestsPerRun,
      launchContext: {
        launchOptions: getLaunchOptions(),
        launchContextOptions: getContextOptions({ lightweight: false })
      },
      preNavigationHooks: [
        async ({ page }) => {
          await page.addInitScript(() => {
            Object.defineProperty(navigator, "webdriver", {
              get: () => undefined
            });
          });
        }
      ],
      failedRequestHandler: async ({ request, error }) => {
        logger.error({ url: request.url, error: error.message }, "Crawlee 请求失败");
        this.db.markTaskFailed(request.url, error.message);
      },
      requestHandler: async (context) => {
        if ((context.request.label || "LIST") === "DETAIL") {
          await this.handleDetail(context);
          return;
        }

        await this.handleList(context, mode);
      }
    });

    return { crawler, requestQueue };
  }

  async seedDiscoveryQueue(requestQueue) {
    this.db.seedTasks(DEFAULT_SEEDS);

    for (const seed of DEFAULT_SEEDS) {
      await requestQueue.addRequest(normalizeSeedRequest(seed));
    }
  }

  async seedDetailQueue(requestQueue, limit = config.crawl.maxArticleRequestsPerRun) {
    const tasks = this.db.listPendingTasks("detail", limit);

    for (const task of tasks) {
      await requestQueue.addRequest({
        url: task.url,
        userData: {
          label: "DETAIL",
          type: "detail",
          depth: task.depth ?? 0,
          source: task.source ?? "sqlite",
          parentUrl: task.parent_url ?? null
        }
      });
    }

    return tasks.length;
  }

  async handleList({ page, request, response, addRequests }, mode) {
    this.db.markTaskRunning(request.url);

    const title = await page.title().catch(() => "");
    const html = await page.content();
    const bodyText = await page.locator("body").innerText().catch(() => "");
    const finalUrl = page.url();

    if (detectBlockedPage({ title, bodyText, statusCode: response?.status() ?? null })) {
      throw new Error("页面触发验证，请先执行 bootstrap-session");
    }

    const links = extractLinks(html, finalUrl || request.url);
    const currentDepth = request.userData.depth ?? 0;
    const listRequests = [];
    const detailTasks = [];

    for (const link of links) {
      const classified = classifyUrl(link);
      if (classified.type === "ignore") {
        continue;
      }

      if (classified.type === "list") {
        const nextDepth = currentDepth + 1;
        if (nextDepth > config.maxDiscoveryDepth) {
          continue;
        }

        listRequests.push({
          url: classified.url,
          userData: {
            label: "LIST",
            type: "list",
            depth: nextDepth,
            source: request.url,
            parentUrl: request.url
          }
        });

        this.db.enqueueTasks([
          {
            url: classified.url,
            type: "list",
            depth: nextDepth,
            source: request.url,
            parentUrl: request.url,
            priority: 1
          }
        ]);
      }

      if (classified.type === "detail") {
        detailTasks.push({
          url: classified.url,
          type: "detail",
          depth: currentDepth,
          source: request.url,
          parentUrl: request.url,
          priority: 10
        });
      }
    }

    if (detailTasks.length) {
      this.db.enqueueTasks(detailTasks);
      await Dataset.pushData(
        detailTasks.map((task) => ({
          kind: "detail-task",
          url: task.url,
          source: task.source,
          discoveredAt: nowIso()
        }))
      );
    }

    if (mode === "discover" && listRequests.length) {
      await addRequests(listRequests, { forefront: false });
    }

    this.db.markTaskDone(request.url);
  }

  async handleDetail({ page, request, response }) {
    this.db.markTaskRunning(request.url);

    const title = await page.title().catch(() => "");
    const html = await page.content();
    const bodyText = await page.locator("body").innerText().catch(() => "");
    const finalUrl = page.url();

    if (detectBlockedPage({ title, bodyText, statusCode: response?.status() ?? null })) {
      throw new Error("详情页触发验证，请先执行 bootstrap-session");
    }

    const article = parseArticle({
      url: request.url,
      finalUrl,
      html
    });

    article.crawledAt = nowIso();
    const rawHtmlPath = this.fileStore.saveRawHtml({
      channel: article.channel,
      title: article.title,
      articleId: article.articleId,
      url: article.url,
      html
    });

    const markdown = buildMarkdownDocument(article);
    const markdownPath = this.fileStore.saveMarkdown({
      channel: article.channel,
      title: article.title,
      articleId: article.articleId,
      url: article.url,
      markdown
    });

    const jsonPath = this.fileStore.saveJson({
      channel: article.channel,
      title: article.title,
      articleId: article.articleId,
      url: article.url,
      payload: {
        ...article,
        rawHtmlPath,
        markdownPath
      }
    });

    this.db.saveArticle({
      ...article,
      raw_html_path: rawHtmlPath,
      json_path: jsonPath,
      markdown_path: markdownPath
    });

    await Dataset.pushData({
      kind: "article",
      url: article.url,
      articleId: article.articleId,
      title: article.title,
      crawledAt: article.crawledAt
    });

    this.db.markTaskDone(request.url);
  }

  async discover() {
    this.db.resetRunningTasks();
    const { crawler, requestQueue } = await this.createCrawler({ mode: "discover" });
    await this.seedDiscoveryQueue(requestQueue);
    await crawler.run();
    return { discovered: true };
  }

  async crawl() {
    this.db.resetRunningTasks();
    const { crawler, requestQueue } = await this.createCrawler({ mode: "crawl" });
    const count = await this.seedDetailQueue(requestQueue);
    if (!count) {
      logger.info("没有待抓取的详情任务。");
      return { crawled: 0 };
    }

    await crawler.run();
    return { queued: count };
  }
}
