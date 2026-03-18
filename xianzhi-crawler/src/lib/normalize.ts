import fs from 'node:fs/promises';
import path from 'node:path';
import { Readability } from '@mozilla/readability';
import { JSDOM } from 'jsdom';
import TurndownService from 'turndown';
import { CONFIG, DEFAULT_HEADERS, PATHS } from '../config.js';
import {
  articleIdFromUrl,
  ensureDir,
  relativePath,
  slugifyArticle,
  stripTags,
  timestamp,
  toAbsoluteUrl,
} from './utils.js';

export interface NormalizedArticle {
  id: string;
  slug: string;
  url: string;
  title: string;
  excerpt: string;
  byline: string | null;
  siteName: string | null;
  publishedAt: string | null;
  fetchedAt: string;
  wordCount: number;
  textContent: string;
  rawHtml: string;
  html: string;
  markdown: string;
  articleDir: string;
  rawHtmlPath: string;
  cleanHtmlPath: string;
  markdownPath: string;
  metaPath: string;
}

interface XianzhiNewsDetail {
  title?: string | null;
  subject?: string | null;
  content?: string | null;
  author?: string | null;
  pub_at?: string | null;
  category?: {
    name?: string | null;
  } | null;
}

interface ExtractedContent {
  html: string;
  title: string | null;
  byline: string | null;
  publishedAt: string | null;
  excerpt: string;
  siteName: string | null;
}

function stringOrNull(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }

  const normalized = value.trim();
  return normalized ? normalized : null;
}

function buildExcerpt(textContent: string, fallback?: string | null): string {
  const source = textContent || fallback || '';
  return source.replace(/\s+/g, ' ').trim().slice(0, 180);
}

function findBalancedJsonObject(source: string, startIndex: number): string | null {
  let depth = 0;
  let inString = false;
  let escaped = false;
  let started = false;

  for (let index = startIndex; index < source.length; index += 1) {
    const char = source[index];

    if (!started) {
      if (char === '{') {
        started = true;
        depth = 1;
      }
      continue;
    }

    if (inString) {
      if (escaped) {
        escaped = false;
      } else if (char === '\\') {
        escaped = true;
      } else if (char === '"') {
        inString = false;
      }
      continue;
    }

    if (char === '"') {
      inString = true;
      continue;
    }

    if (char === '{') {
      depth += 1;
      continue;
    }

    if (char === '}') {
      depth -= 1;
      if (depth === 0) {
        return source.slice(startIndex, index + 1);
      }
    }
  }

  return null;
}

function extractNewsDetailPayload(rawHtml: string): XianzhiNewsDetail | null {
  const marker = 'let newsDetail=';
  const markerIndex = rawHtml.indexOf(marker);
  if (markerIndex < 0) {
    return null;
  }

  const objectStart = rawHtml.indexOf('{', markerIndex + marker.length);
  if (objectStart < 0) {
    return null;
  }

  const jsonText = findBalancedJsonObject(rawHtml, objectStart);
  if (!jsonText) {
    return null;
  }

  try {
    return JSON.parse(jsonText) as XianzhiNewsDetail;
  } catch {
    return null;
  }
}

function extractPublishedAt(doc: Document): string | null {
  const selectors = [
    'meta[property="article:published_time"]',
    'meta[name="publish-date"]',
    'meta[name="pubdate"]',
    'meta[name="date"]',
    'time[datetime]',
  ];

  for (const selector of selectors) {
    const node = doc.querySelector(selector);
    if (!node) {
      continue;
    }

    const value = node.getAttribute('content') ?? node.getAttribute('datetime') ?? node.textContent ?? '';
    const normalized = value.trim();
    if (normalized) {
      return normalized;
    }
  }

  for (const script of doc.querySelectorAll('script[type="application/ld+json"]')) {
    const text = script.textContent?.trim();
    if (!text) {
      continue;
    }

    try {
      const parsed = JSON.parse(text) as Record<string, unknown> | Record<string, unknown>[];
      const queue = Array.isArray(parsed) ? parsed : [parsed];
      for (const item of queue) {
        const value = typeof item.datePublished === 'string' ? item.datePublished : null;
        if (value) {
          return value;
        }
      }
    } catch {
      // Ignore invalid JSON-LD.
    }
  }

  return null;
}

function decodeCardValue(value: string | null): Record<string, unknown> | null {
  if (!value) {
    return null;
  }

  const raw = value.startsWith('data:') ? value.slice(5) : value;

  try {
    return JSON.parse(decodeURIComponent(raw)) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function stripNoiseNodes(document: Document): void {
  for (const node of document.querySelectorAll('script, style, noscript, iframe')) {
    node.remove();
  }
}

function sanitizeContentDom(document: Document, pageUrl: string): void {
  stripNoiseNodes(document);

  for (const element of document.querySelectorAll<HTMLElement>('*')) {
    if (element.hasAttribute('src')) {
      element.setAttribute('src', toAbsoluteUrl(pageUrl, element.getAttribute('src') ?? ''));
    }

    if (element.hasAttribute('href')) {
      element.setAttribute('href', toAbsoluteUrl(pageUrl, element.getAttribute('href') ?? ''));
    }

    for (const attribute of [...element.attributes]) {
      const attributeName = attribute.name.toLowerCase();

      if (attributeName === 'style' || attributeName === 'fid') {
        element.removeAttribute(attribute.name);
        continue;
      }

      if (attributeName === 'id' && /^u[a-z0-9-]+$/i.test(attribute.value)) {
        element.removeAttribute(attribute.name);
        continue;
      }

      if (attributeName.startsWith('data-') && attributeName !== 'data-language') {
        element.removeAttribute(attribute.name);
        continue;
      }

      if (
        attributeName === 'class' &&
        element.tagName !== 'CODE' &&
        element.tagName !== 'PRE' &&
        element.tagName !== 'FIGURE'
      ) {
        element.removeAttribute(attribute.name);
      }
    }
  }
}

function renderImageCard(document: Document, payload: Record<string, unknown>, pageUrl: string): HTMLElement | null {
  const src = stringOrNull(payload.src);
  if (!src) {
    return null;
  }

  const image = document.createElement('img');
  image.setAttribute('src', toAbsoluteUrl(pageUrl, src));

  const alt = stringOrNull(payload.title) ?? stringOrNull(payload.name);
  if (alt) {
    image.setAttribute('alt', alt);
  }

  const figure = document.createElement('figure');
  figure.append(image);

  const caption = stringOrNull(payload.title);
  if (caption) {
    const figcaption = document.createElement('figcaption');
    figcaption.textContent = caption;
    figure.append(figcaption);
  }

  return figure;
}

function renderCodeBlockCard(document: Document, payload: Record<string, unknown>): HTMLElement | null {
  const codeText = typeof payload.code === 'string' ? payload.code : null;
  if (!codeText) {
    return null;
  }

  const language = stringOrNull(payload.mode) ?? stringOrNull(payload.language);
  const pre = document.createElement('pre');
  const code = document.createElement('code');
  code.textContent = codeText;

  if (language) {
    pre.setAttribute('data-language', language);
    code.setAttribute('data-language', language);
    code.className = `language-${language}`;
  }

  pre.append(code);
  return pre;
}

function renderFileCard(document: Document, payload: Record<string, unknown>, pageUrl: string): HTMLElement | null {
  const src =
    stringOrNull(payload.src) ??
    stringOrNull(payload.url) ??
    stringOrNull(payload.downloadUrl) ??
    stringOrNull(payload.fileUrl);

  if (!src) {
    return null;
  }

  const link = document.createElement('a');
  link.href = toAbsoluteUrl(pageUrl, src);
  link.textContent = stringOrNull(payload.name) ?? '附件下载';
  return link;
}

function renderCard(document: Document, card: Element, pageUrl: string): HTMLElement | null {
  const payload = decodeCardValue(card.getAttribute('value'));
  const name = card.getAttribute('name')?.toLowerCase() ?? '';

  if (!payload) {
    return null;
  }

  if (name === 'image') {
    return renderImageCard(document, payload, pageUrl);
  }

  if (name === 'codeblock') {
    return renderCodeBlockCard(document, payload);
  }

  if (name === 'file' || name === 'attachment') {
    return renderFileCard(document, payload, pageUrl);
  }

  const fallbackLink = renderFileCard(document, payload, pageUrl);
  return fallbackLink;
}

function renderPayloadContent(content: string, pageUrl: string): string | null {
  const dom = new JSDOM(`<article>${content}</article>`, { url: pageUrl });
  const document = dom.window.document;

  for (const card of [...document.querySelectorAll('card')]) {
    const rendered = renderCard(document, card, pageUrl);
    if (rendered) {
      card.replaceWith(rendered);
    } else {
      card.remove();
    }
  }

  sanitizeContentDom(document, pageUrl);

  const appRoot = document.querySelector('#app');
  const html = (appRoot?.innerHTML ?? document.body.innerHTML).trim();
  return html || null;
}

function extractRenderedBody(document: Document, pageUrl: string): string | null {
  const body = document.querySelector('#markdown-body');
  if (!body) {
    return null;
  }

  const dom = new JSDOM(`<article>${body.innerHTML}</article>`, { url: pageUrl });
  sanitizeContentDom(dom.window.document, pageUrl);

  const html = dom.window.document.body.innerHTML.trim();
  return html || null;
}

function extractReadabilityContent(rawHtml: string, pageUrl: string): ExtractedContent | null {
  const dom = new JSDOM(rawHtml, { url: pageUrl });
  const reader = new Readability(dom.window.document);
  const parsed = reader.parse();

  if (!parsed?.content || !parsed.textContent?.trim()) {
    return null;
  }

  return {
    html: parsed.content,
    title: parsed.title?.trim() || null,
    byline: parsed.byline?.trim() || null,
    publishedAt: null,
    excerpt: parsed.excerpt?.trim() ?? '',
    siteName: parsed.siteName?.trim() || null,
  };
}

function extractDomTitle(document: Document): string | null {
  const selectors = [
    '.detail_title',
    'meta[property="og:title"]',
    'title',
  ];

  for (const selector of selectors) {
    const node = document.querySelector(selector);
    if (!node) {
      continue;
    }

    const value = node.getAttribute('content') ?? node.textContent ?? '';
    const normalized = value.trim();
    if (normalized) {
      return normalized;
    }
  }

  return null;
}

function extractDomByline(document: Document): string | null {
  const selectors = ['.detail_info .username', '.username', '[rel="author"]'];

  for (const selector of selectors) {
    const node = document.querySelector(selector);
    const normalized = node?.textContent?.trim();
    if (normalized) {
      return normalized;
    }
  }

  return null;
}

async function mirrorAssets(html: string, articleDir: string, pageUrl: string): Promise<string> {
  const dom = new JSDOM(html, { url: pageUrl });
  const document = dom.window.document;
  const assetDir = path.join(articleDir, 'assets');
  await ensureDir(assetDir);

  const downloadTasks: Array<Promise<void>> = [];
  let assetIndex = 0;

  const extensionFromContentType = (contentType: string | null): string | null => {
    if (!contentType) {
      return null;
    }

    if (contentType.includes('image/png')) {
      return '.png';
    }
    if (contentType.includes('image/jpeg')) {
      return '.jpg';
    }
    if (contentType.includes('image/webp')) {
      return '.webp';
    }
    if (contentType.includes('image/gif')) {
      return '.gif';
    }
    if (contentType.includes('application/pdf')) {
      return '.pdf';
    }
    if (contentType.includes('application/zip')) {
      return '.zip';
    }

    return null;
  };

  const download = async (url: string, fileStem: string): Promise<string> => {
    const response = await fetch(url, {
      headers: {
        ...DEFAULT_HEADERS,
        'user-agent': CONFIG.userAgent,
        referer: pageUrl,
      },
      redirect: 'follow',
    });
    if (!response.ok) {
      throw new Error(`Failed to download asset ${url}: ${response.status}`);
    }

    const buffer = Buffer.from(await response.arrayBuffer());
    const responseUrl = new URL(response.url);
    const extension =
      path.extname(responseUrl.pathname) ||
      extensionFromContentType(response.headers.get('content-type')) ||
      path.extname(new URL(url).pathname) ||
      '.bin';
    const targetPath = path.join(assetDir, `${fileStem}${extension}`);
    await fs.writeFile(targetPath, buffer);
    return targetPath;
  };

  const replaceAttribute = (selector: string, attribute: 'src' | 'href'): void => {
    for (const node of document.querySelectorAll<HTMLElement>(selector)) {
      const original = node.getAttribute(attribute);
      if (!original) {
        continue;
      }

      const absolute = toAbsoluteUrl(pageUrl, original);
      if (!/^https?:/i.test(absolute)) {
        continue;
      }

      const fileStem = String(assetIndex += 1).padStart(3, '0');

      downloadTasks.push(
        (async () => {
          try {
            const targetPath = await download(absolute, fileStem);
            node.setAttribute(attribute, relativePath(path.join(articleDir, 'article.html'), targetPath));
          } catch (error) {
            node.setAttribute(attribute, absolute);
            const message = error instanceof Error ? error.message : String(error);
            console.warn(`[asset] ${absolute} -> ${message}`);
          }
        })(),
      );
    }
  };

  replaceAttribute('img[src]', 'src');
  replaceAttribute('a[href*="/api/v2/files/"]', 'href');
  replaceAttribute('a[href$=".pdf"]', 'href');
  replaceAttribute('a[href$=".zip"]', 'href');

  await Promise.all(downloadTasks);
  return document.body.innerHTML;
}

function createTurndownService(): TurndownService {
  const turndown = new TurndownService({
    codeBlockStyle: 'fenced',
    headingStyle: 'atx',
  });

  turndown.addRule('preservePreCode', {
    filter: (node) => node.nodeName === 'PRE',
    replacement: (_content, node) => {
      const pre = node as HTMLElement;
      const code = pre.querySelector('code');
      const classLanguage = code?.className
        ?.split(/\s+/)
        .find((token) => token.startsWith('language-'))
        ?.replace(/^language-/, '');
      const language =
        code?.getAttribute('data-language') ??
        pre.getAttribute('data-language') ??
        classLanguage ??
        '';
      const body = code?.textContent ?? pre.textContent ?? '';
      const fence = language ? `\`\`\`${language}` : '```';
      return `\n\n${fence}\n${body.trimEnd()}\n\`\`\`\n\n`;
    },
  });

  return turndown;
}

export async function normalizeArticle(rawHtml: string, pageUrl: string): Promise<NormalizedArticle> {
  const dom = new JSDOM(rawHtml, { url: pageUrl });
  const document = dom.window.document;
  const payload = extractNewsDetailPayload(rawHtml);
  const readability = extractReadabilityContent(rawHtml, pageUrl);

  const extractedHtml =
    (payload?.content ? renderPayloadContent(payload.content, pageUrl) : null) ??
    extractRenderedBody(document, pageUrl) ??
    readability?.html ??
    null;

  if (!extractedHtml) {
    throw new Error(`Could not extract article content from ${pageUrl}`);
  }

  const id = articleIdFromUrl(pageUrl);
  const title =
    stringOrNull(payload?.title) ??
    extractDomTitle(document) ??
    readability?.title ??
    `article-${id}`;
  const byline =
    stringOrNull(payload?.author) ??
    extractDomByline(document) ??
    readability?.byline ??
    null;
  const publishedAt =
    stringOrNull(payload?.pub_at) ??
    extractPublishedAt(document) ??
    readability?.publishedAt ??
    null;

  const slug = slugifyArticle(id, title);
  const articleDir = path.join(PATHS.articles, slug);
  const rawHtmlPath = path.join(articleDir, 'raw.html');
  const cleanHtmlPath = path.join(articleDir, 'article.html');
  const markdownPath = path.join(articleDir, 'article.md');
  const metaPath = path.join(articleDir, 'meta.json');

  await ensureDir(articleDir);

  const cleanBody = await mirrorAssets(extractedHtml, articleDir, pageUrl);
  const cleanDom = new JSDOM(`<article>${cleanBody}</article>`, { url: pageUrl });
  stripNoiseNodes(cleanDom.window.document);

  const html = cleanDom.window.document.body.innerHTML.trim();
  const textContent =
    cleanDom.window.document.body.textContent?.replace(/\s+/g, ' ').trim() || stripTags(html);

  if (!textContent) {
    throw new Error(`Extracted content is empty after cleanup for ${pageUrl}`);
  }

  const excerpt = buildExcerpt(textContent, payload?.subject ?? readability?.excerpt ?? null);
  const turndown = createTurndownService();
  const markdown = [
    `# ${title}`,
    '',
    `- 原文链接: ${pageUrl}`,
    `- 抓取时间: ${timestamp()}`,
    publishedAt ? `- 发布时间: ${publishedAt}` : null,
    byline ? `- 作者: ${byline}` : null,
    payload?.category?.name ? `- 分类: ${payload.category.name}` : null,
    '',
    turndown.turndown(html).trim(),
    '',
  ]
    .filter((item): item is string => Boolean(item))
    .join('\n');

  return {
    id,
    slug,
    url: pageUrl,
    title,
    excerpt,
    byline,
    siteName: CONFIG.siteName,
    publishedAt,
    fetchedAt: timestamp(),
    wordCount: textContent.length,
    textContent,
    rawHtml,
    html,
    markdown,
    articleDir,
    rawHtmlPath,
    cleanHtmlPath,
    markdownPath,
    metaPath,
  };
}
