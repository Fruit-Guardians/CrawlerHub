import { config } from "../config.js";

const THREAD_DETAIL_PATTERN = /^\/thread-(\d+)(?:-\d+)?\.htm$/i;
const ARTICLE_DETAIL_PATTERN = /^\/article-(\d+)\.htm$/i;
const STATIC_ASSET_PATTERN =
  /\.(?:jpg|jpeg|png|gif|svg|webp|css|js|woff2?|ttf|ico|xml|rss|pdf|zip|rar|7z)$/i;
const LIST_PATH_PATTERNS = [
  /^\/$/i,
  /^\/index(?:-[\w_]+)?\.htm$/i,
  /^\/forum/i,
  /^\/threadindex/i,
  /^\/plate/i,
  /^\/category/i
];
const IGNORE_PATH_PATTERNS = [
  /^\/elink@/i,
  /^\/mrt\.htm$/i,
  /^\/member/i,
  /^\/space/i,
  /^\/job/i,
  /^\/download/i,
  /^\/passport/i,
  /^\/attach/i,
  /^\/misc/i,
  /^\/search/i
];

export function normalizeUrl(rawUrl) {
  try {
    const url = new URL(rawUrl, config.site.baseUrl);
    url.hash = "";
    return url;
  } catch {
    return null;
  }
}

function normalizeThreadDetailUrl(url) {
  const articleId = url.pathname.match(THREAD_DETAIL_PATTERN)?.[1] || "";
  const normalized = new URL(`https://bbs.kanxue.com/thread-${articleId}.htm`);
  normalized.searchParams.set("style", "1");

  return {
    url: normalized.toString(),
    articleId,
    channel: "thread"
  };
}

function normalizeArticleDetailUrl(url) {
  const articleId = url.pathname.match(ARTICLE_DETAIL_PATTERN)?.[1] || "";
  const normalized = new URL(url.toString());
  normalized.search = "";
  normalized.hash = "";

  return {
    url: normalized.toString(),
    articleId,
    channel: "article"
  };
}

export function classifyUrl(rawUrl) {
  const url = normalizeUrl(rawUrl);

  if (!url) {
    return { type: "ignore", reason: "invalid-url" };
  }

  if (!config.site.allowedHosts.includes(url.hostname)) {
    return { type: "ignore", reason: "foreign-host", url: url.toString() };
  }

  if (STATIC_ASSET_PATTERN.test(url.pathname)) {
    return { type: "ignore", reason: "static-asset", url: url.toString() };
  }

  if (IGNORE_PATH_PATTERNS.some((pattern) => pattern.test(url.pathname))) {
    return { type: "ignore", reason: "ignored-path", url: url.toString() };
  }

  if (url.hostname === "bbs.kanxue.com" && THREAD_DETAIL_PATTERN.test(url.pathname)) {
    return {
      type: "detail",
      ...normalizeThreadDetailUrl(url)
    };
  }

  if (url.hostname === "bbs.kanxue.com" && ARTICLE_DETAIL_PATTERN.test(url.pathname)) {
    return {
      type: "detail",
      ...normalizeArticleDetailUrl(url)
    };
  }

  if (LIST_PATH_PATTERNS.some((pattern) => pattern.test(url.pathname))) {
    return { type: "list", url: url.toString() };
  }

  if (url.hostname === "bbs.kanxue.com" && (!url.pathname.includes(".") || url.pathname.endsWith(".htm"))) {
    return { type: "list", url: url.toString() };
  }

  return { type: "ignore", reason: "out-of-scope", url: url.toString() };
}
