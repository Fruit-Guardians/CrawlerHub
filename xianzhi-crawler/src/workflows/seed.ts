import path from 'node:path';
import { CheerioCrawler, RequestQueue } from 'crawlee';
import { XMLParser } from 'fast-xml-parser';
import { CONFIG, DEFAULT_HEADERS, PATHS, QUEUES } from '../config.js';
import { writeJson } from '../lib/fs.js';
import { articleIdFromUrl, unique } from '../lib/utils.js';

interface FeedEntry {
  title: string;
  link: string;
  published: string;
  updated: string;
  summary?: string;
}

function xmlText(value: unknown): string {
  if (typeof value === 'string') {
    return value.trim();
  }
  if (value && typeof value === 'object' && '#text' in value) {
    const text = (value as { '#text'?: unknown })['#text'];
    return typeof text === 'string' ? text.trim() : '';
  }
  return '';
}

function normalizeNewsUrl(href: string): string | null {
  try {
    const url = new URL(href, CONFIG.siteUrl);
    if (!/^\/news\/\d+$/.test(url.pathname)) {
      return null;
    }
    return url.toString();
  } catch {
    return null;
  }
}

async function seedFromFeed(detailQueue: RequestQueue): Promise<FeedEntry[]> {
  const response = await fetch(CONFIG.feedUrl, {
    headers: {
      ...DEFAULT_HEADERS,
      'user-agent': CONFIG.userAgent,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch feed: ${response.status}`);
  }

  const xml = await response.text();
  const parser = new XMLParser({
    ignoreAttributes: false,
    attributeNamePrefix: '',
    parseTagValue: false,
    trimValues: true,
  });
  const parsed = parser.parse(xml) as {
    feed?: {
      entry?: Array<{
        title?: string;
        link?: { href?: string };
        published?: string;
        updated?: string;
        summary?: string | { '#text'?: string };
      }> | {
        title?: string;
        link?: { href?: string };
        published?: string;
        updated?: string;
        summary?: string | { '#text'?: string };
      };
    };
  };

  const entries = parsed.feed?.entry
    ? Array.isArray(parsed.feed.entry)
      ? parsed.feed.entry
      : [parsed.feed.entry]
    : [];

  const normalized: FeedEntry[] = [];
  for (const entry of entries) {
    if (!entry.link?.href) {
      continue;
    }
    const url = normalizeNewsUrl(entry.link.href);
    if (!url) {
      continue;
    }
    normalized.push({
      title: xmlText(entry.title) || articleIdFromUrl(url),
      link: url,
      published: xmlText(entry.published),
      updated: xmlText(entry.updated),
      summary: xmlText(entry.summary),
    });
  }

  await detailQueue.addRequests(
    normalized.map((entry) => ({
      url: entry.link,
      uniqueKey: `news:${articleIdFromUrl(entry.link)}`,
    })),
  );

  await writeJson(path.join(PATHS.feeds, 'feed.json'), {
    fetchedAt: new Date().toISOString(),
    count: normalized.length,
    entries: normalized,
  });

  return normalized;
}

async function seedFromHistory(detailQueue: RequestQueue, maxPages: number): Promise<string[]> {
  const listRequests = [];
  for (let page = 1; page <= maxPages; page += 1) {
    const url = page === 1 ? CONFIG.newsListUrl : `${CONFIG.newsListUrl}?page=${page}`;
    listRequests.push({
      url,
      uniqueKey: `list:${page}`,
      userData: { page },
    });
  }

  const discovered = new Set<string>();
  const crawler = new CheerioCrawler({
    maxConcurrency: 4,
    requestHandlerTimeoutSecs: 90,
    async requestHandler({ $, request, log }) {
      const pageNo = String(request.userData.page ?? '?');
      const links = new Set<string>();
      $('a[href]').each((_index, element) => {
        const href = $(element).attr('href');
        if (!href) {
          return;
        }
        const url = normalizeNewsUrl(href);
        if (url) {
          links.add(url);
        }
      });

      if (links.size === 0) {
        log.warning(`No article links found on list page ${pageNo}`);
        return;
      }

      const urls = [...links];
      urls.forEach((url) => discovered.add(url));
      await detailQueue.addRequests(
        urls.map((url) => ({
          url,
          uniqueKey: `news:${articleIdFromUrl(url)}`,
        })),
      );
      log.info(`Discovered ${urls.length} article links from list page ${pageNo}`);
    },
  });

  await crawler.run(listRequests);

  const urls = unique([...discovered]);
  await writeJson(path.join(PATHS.reports, 'history-seed.json'), {
    fetchedAt: new Date().toISOString(),
    listPages: maxPages,
    count: urls.length,
    urls,
  });

  return urls;
}

export async function seedWorkflows(maxPages = CONFIG.defaultListPages): Promise<{
  feedEntries: FeedEntry[];
  historyUrls: string[];
}> {
  const detailQueue = await RequestQueue.open(QUEUES.details);
  const feedEntries = await seedFromFeed(detailQueue);
  const historyUrls = await seedFromHistory(detailQueue, maxPages);
  return { feedEntries, historyUrls };
}
