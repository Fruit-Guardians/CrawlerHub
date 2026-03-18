import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export const ROOT_DIR = path.resolve(__dirname, '..');

export const PATHS = {
  root: ROOT_DIR,
  storage: path.join(ROOT_DIR, 'storage'),
  crawleeStorage: path.join(ROOT_DIR, 'storage', 'crawlee'),
  articles: path.join(ROOT_DIR, 'storage', 'articles'),
  feeds: path.join(ROOT_DIR, 'storage', 'feeds'),
  reports: path.join(ROOT_DIR, 'storage', 'reports'),
  sqlite: path.join(ROOT_DIR, 'storage', 'sqlite'),
  dist: path.join(ROOT_DIR, 'dist'),
  site: path.join(ROOT_DIR, 'dist', 'site'),
};

process.env.CRAWLEE_STORAGE_DIR = PATHS.crawleeStorage;

export const CONFIG = {
  siteName: '先知社区',
  siteUrl: 'https://xz.aliyun.com',
  newsListUrl: 'https://xz.aliyun.com/news',
  feedUrl: 'https://xz.aliyun.com/feed',
  defaultListPages: Number(process.env.XZ_LIST_PAGES ?? '10'),
  detailConcurrency: Number(process.env.XZ_DETAIL_CONCURRENCY ?? '1'),
  maxArticleRequests:
    process.env.XZ_MAX_ARTICLES === undefined
      ? undefined
      : Number(process.env.XZ_MAX_ARTICLES),
  headless: process.env.XZ_HEADLESS !== 'false',
  browserTimeoutMs: Number(process.env.XZ_BROWSER_TIMEOUT_MS ?? '45000'),
  minArticleTextLength: Number(process.env.XZ_MIN_ARTICLE_TEXT_LENGTH ?? '180'),
  userAgent:
    process.env.XZ_USER_AGENT ??
    [
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
      'AppleWebKit/537.36 (KHTML, like Gecko)',
      'Chrome/135.0.0.0 Safari/537.36',
    ].join(' '),
};

export const QUEUES = {
  history: 'xianzhi-history-pages',
  details: 'xianzhi-article-details',
};

export const DEFAULT_HEADERS = {
  'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
  'cache-control': 'no-cache',
  pragma: 'no-cache',
  'upgrade-insecure-requests': '1',
};
