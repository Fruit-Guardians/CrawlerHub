import { PlaywrightCrawler, RequestQueue } from 'crawlee';
import type { Page } from 'playwright';
import { CONFIG, DEFAULT_HEADERS, QUEUES } from '../config.js';
import { saveArticle } from '../lib/article-store.js';
import { normalizeArticle } from '../lib/normalize.js';
import { articleIdFromUrl, sleep } from '../lib/utils.js';

export interface CrawlArticleDetailsOptions {
  queueName?: string;
  maxRequestsPerCrawl?: number;
}

async function resolveChallenge(page: Page): Promise<string> {
  let html = '';

  for (let attempt = 1; attempt <= 3; attempt += 1) {
    await page.waitForLoadState('domcontentloaded', { timeout: 15000 }).catch(() => undefined);
    await page.waitForTimeout(2000);
    html = await page.content();

    const looksLikeChallenge =
      html.includes('aliyunwaf_') ||
      html.includes('acw_sc__v2') ||
      html.includes('name="aliyun_waf_');

    const looksLikeArticle =
      /<article[\s>]/i.test(html) ||
      /detail_body/i.test(html) ||
      /news/i.test(await page.title()) ||
      html.length > 40000;

    if (!looksLikeChallenge || looksLikeArticle) {
      return html;
    }

    await sleep(1500 * attempt);
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 20000 }).catch(() => undefined);
  }

  return html;
}

export async function crawlArticleDetails(
  options: CrawlArticleDetailsOptions = {},
): Promise<void> {
  const requestQueue = await RequestQueue.open(options.queueName ?? QUEUES.details);

  const crawler = new PlaywrightCrawler({
    requestQueue,
    maxConcurrency: CONFIG.detailConcurrency,
    maxRequestsPerCrawl: options.maxRequestsPerCrawl ?? CONFIG.maxArticleRequests,
    requestHandlerTimeoutSecs: 180,
    maxRequestRetries: 2,
    useSessionPool: true,
    browserPoolOptions: {
      useFingerprints: false,
    },
    launchContext: {
      launchOptions: {
        headless: CONFIG.headless,
      },
    },
    preNavigationHooks: [
      async ({ page }) => {
        await page.context().setExtraHTTPHeaders({
          ...DEFAULT_HEADERS,
          'user-agent': CONFIG.userAgent,
        });

        await page.route('**/*', async (route) => {
          const type = route.request().resourceType();
          if (type === 'font' || type === 'image' || type === 'media' || type === 'stylesheet') {
            await route.abort();
            return;
          }
          await route.continue();
        });
      },
    ],
    async requestHandler({ page, request, log }) {
      const url = request.url;
      const id = articleIdFromUrl(url);
      log.info(`Fetching article ${id}`);

      await page.setDefaultNavigationTimeout(CONFIG.browserTimeoutMs);
      await page.setExtraHTTPHeaders({
        ...DEFAULT_HEADERS,
        'user-agent': CONFIG.userAgent,
      });

      const html = await resolveChallenge(page);
      const normalized = await normalizeArticle(html, url);

      if (normalized.textContent.length < CONFIG.minArticleTextLength) {
        throw new Error(
          `Extracted content too short for ${url} (${normalized.textContent.length} chars)`,
        );
      }

      const meta = await saveArticle(normalized);
      log.info(`Saved ${meta.slug} (${meta.wordCount} chars)`);
    },
    async failedRequestHandler({ request, log, error }) {
      const message = error instanceof Error ? error.message : String(error);
      log.error(`Failed ${request.url}: ${message}`);
    },
  });

  await crawler.run();
}
