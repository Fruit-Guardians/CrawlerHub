import path from 'node:path';
import { RequestQueue } from 'crawlee';
import { buildArtifacts } from './build.js';
import { crawlArticleDetails } from './crawl.js';
import { CONFIG, DEFAULT_HEADERS, PATHS } from '../config.js';
import { loadAllArticles } from '../lib/article-store.js';
import { writeJson } from '../lib/fs.js';

interface ApiNewsItem {
  id: number;
  title?: string | null;
  pub_at?: string | null;
  created_at?: string | null;
}

const API_PAGE_SIZE = 100;
const BACKFILL_QUEUE_PREFIX = 'xianzhi-backfill-until-';

function parseLocalCutoffDate(dateText: string): Date {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateText)) {
    throw new Error(`Invalid cutoff date: ${dateText}. Use YYYY-MM-DD.`);
  }

  return new Date(`${dateText}T00:00:00+08:00`);
}

async function fetchNewsApiPage(page: number, limit: number): Promise<ApiNewsItem[]> {
  const url = new URL('/api/v2/news', CONFIG.siteUrl);
  url.searchParams.set('page', String(page));
  url.searchParams.set('limit', String(limit));

  const response = await fetch(url, {
    headers: {
      ...DEFAULT_HEADERS,
      'user-agent': CONFIG.userAgent,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.status}`);
  }

  const parsed = (await response.json()) as unknown;
  if (!Array.isArray(parsed)) {
    throw new Error(`Unexpected response for ${url}`);
  }

  return parsed as ApiNewsItem[];
}

export async function backfillUntilDate(untilDateText: string): Promise<{
  untilDate: string;
  untilDateUtc: string;
  queueName: string;
  seededPages: number;
  queuedUrls: number;
  skippedExisting: number;
  articleCount: number;
  sqlitePath: string;
}> {
  const cutoffDate = parseLocalCutoffDate(untilDateText);
  const queueName = `${BACKFILL_QUEUE_PREFIX}${untilDateText}`;
  const queue = await RequestQueue.open(queueName);
  const existingIds = new Set((await loadAllArticles()).map((article) => article.id));

  let seededPages = 0;
  let queuedUrls = 0;
  let skippedExisting = 0;
  let reachedCutoff = false;

  for (let page = 1; page <= 500; page += 1) {
    const items = await fetchNewsApiPage(page, API_PAGE_SIZE);
    if (items.length === 0) {
      break;
    }

    seededPages = page;
    const requests = [];

    for (const item of items) {
      const publishedAt = item.pub_at ?? item.created_at;
      if (!publishedAt) {
        continue;
      }

      const publishedTime = new Date(publishedAt).getTime();
      if (Number.isNaN(publishedTime)) {
        continue;
      }

      if (publishedTime < cutoffDate.getTime()) {
        reachedCutoff = true;
        break;
      }

      const articleId = String(item.id);
      if (existingIds.has(articleId)) {
        skippedExisting += 1;
        continue;
      }

      requests.push({
        url: `${CONFIG.siteUrl}/news/${articleId}`,
        uniqueKey: `news:${articleId}`,
      });
    }

    if (requests.length > 0) {
      await queue.addRequests(requests);
      queuedUrls += requests.length;
    }

    if (reachedCutoff) {
      break;
    }
  }

  await writeJson(path.join(PATHS.reports, `backfill-${untilDateText}.json`), {
    fetchedAt: new Date().toISOString(),
    untilDateLocal: untilDateText,
    untilDateUtc: cutoffDate.toISOString(),
    queueName,
    seededPages,
    queuedUrls,
    skippedExisting,
  });

  await crawlArticleDetails({
    queueName,
  });

  const built = await buildArtifacts();

  return {
    untilDate: untilDateText,
    untilDateUtc: cutoffDate.toISOString(),
    queueName,
    seededPages,
    queuedUrls,
    skippedExisting,
    articleCount: built.articleCount,
    sqlitePath: built.sqlitePath,
  };
}
