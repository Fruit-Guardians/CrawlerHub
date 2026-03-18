import fs from 'node:fs/promises';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { JSDOM } from 'jsdom';
import { PATHS, CONFIG } from '../config.js';
import type { ArticleMeta } from './article-store.js';
import { ensureDir, formatCount, relativePath } from './utils.js';

const execFileAsync = promisify(execFile);

function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function renderShell(title: string, content: string, stylesheetHref: string): string {
  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(title)}</title>
  <link rel="stylesheet" href="${escapeHtml(stylesheetHref)}">
</head>
<body>
  <div class="page-shell">
    ${content}
  </div>
</body>
</html>
`;
}

async function writeStyles(): Promise<void> {
  const css = `:root {
  --bg: #f4f0e8;
  --panel: rgba(255, 251, 245, 0.92);
  --text: #1e1c19;
  --muted: #74695f;
  --accent: #ae3d27;
  --accent-soft: #f2d7c6;
  --border: rgba(30, 28, 25, 0.12);
  --shadow: 0 20px 50px rgba(82, 49, 24, 0.12);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  color: var(--text);
  background:
    radial-gradient(circle at top left, rgba(174, 61, 39, 0.14), transparent 24rem),
    radial-gradient(circle at right 10%, rgba(48, 108, 150, 0.14), transparent 20rem),
    linear-gradient(180deg, #f9f6f1 0%, var(--bg) 100%);
  font-family: "Source Han Serif SC", "Noto Serif SC", Georgia, serif;
}
a { color: inherit; }
.page-shell {
  width: min(1100px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 32px 0 80px;
}
.hero, .article, .search-panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 28px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(12px);
}
.hero {
  padding: 32px;
  margin-bottom: 24px;
}
.hero h1, .article h1 {
  margin: 0 0 12px;
  font-size: clamp(2rem, 4vw, 3.2rem);
  line-height: 1.06;
}
.hero p, .article-meta, .article-nav, .article-summary {
  color: var(--muted);
}
.search-panel {
  padding: 24px 32px;
  margin-bottom: 24px;
}
.article-list {
  display: grid;
  gap: 16px;
}
.article-card {
  display: block;
  text-decoration: none;
  padding: 22px 24px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(30, 28, 25, 0.08);
  border-radius: 22px;
  transition: transform 180ms ease, box-shadow 180ms ease;
}
.article-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 30px rgba(82, 49, 24, 0.08);
}
.article-card h2 {
  margin: 0 0 10px;
  font-size: 1.28rem;
}
.article {
  padding: 32px;
}
.article-content {
  font-size: 1.05rem;
  line-height: 1.84;
}
.article-content pre {
  overflow-x: auto;
  padding: 16px;
  border-radius: 18px;
  background: #181512;
  color: #fef9f2;
}
.article-content code {
  font-family: "JetBrains Mono", "SFMono-Regular", monospace;
}
.article-content img {
  max-width: 100%;
  border-radius: 18px;
}
.pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 0.92rem;
  font-weight: 600;
}
.topbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.back-link {
  text-decoration: none;
  color: var(--accent);
  font-weight: 700;
}
.meta-grid {
  display: grid;
  gap: 10px;
  margin: 20px 0 24px;
  padding: 0;
  list-style: none;
}
@media (min-width: 900px) {
  .meta-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
#search {
  min-height: 150px;
}
`;
  await fs.writeFile(path.join(PATHS.site, 'styles.css'), css, 'utf8');
}

async function copyLinkedFile(sourcePath: string, targetPath: string): Promise<void> {
  await ensureDir(path.dirname(targetPath));
  await fs.copyFile(sourcePath, targetPath);
}

async function localizeBodyAssets(article: ArticleMeta, destinationHtmlPath: string): Promise<string> {
  const rawHtml = await fs.readFile(article.cleanHtmlPath, 'utf8');
  const body = rawHtml.match(/<body>([\s\S]*)<\/body>/i)?.[1]?.trim() ?? rawHtml;
  const dom = new JSDOM(`<body>${body}</body>`);
  const document = dom.window.document;
  const sourceDir = path.dirname(article.cleanHtmlPath);
  const siteAssetDir = path.join(PATHS.site, 'article-assets', article.slug);

  const nodes = document.querySelectorAll<HTMLElement>('img[src], a[href]');
  for (const node of nodes) {
    const attribute = node.hasAttribute('src') ? 'src' : 'href';
    const original = node.getAttribute(attribute);
    if (!original || /^https?:/i.test(original) || original.startsWith('data:')) {
      continue;
    }

    const sourcePath = path.resolve(sourceDir, original);
    const fileName = path.basename(sourcePath);
    const targetPath = path.join(siteAssetDir, fileName);

    try {
      await copyLinkedFile(sourcePath, targetPath);
      node.setAttribute(attribute, relativePath(destinationHtmlPath, targetPath));
    } catch {
      // Keep original reference if copying fails.
    }
  }

  return document.body.innerHTML;
}

async function renderArticlePage(article: ArticleMeta): Promise<void> {
  const htmlPath = path.join(PATHS.site, 'articles', `${article.slug}.html`);
  const body = await localizeBodyAssets(article, htmlPath);
  const siteSourceDir = path.join(PATHS.site, 'source', article.slug);
  const copiedMarkdownPath = path.join(siteSourceDir, 'article.md');
  const copiedHtmlPath = path.join(siteSourceDir, 'article.html');
  const copiedRawHtmlPath = path.join(siteSourceDir, 'raw.html');

  await copyLinkedFile(article.markdownPath, copiedMarkdownPath);
  await copyLinkedFile(article.cleanHtmlPath, copiedHtmlPath);
  await copyLinkedFile(article.rawHtmlPath, copiedRawHtmlPath);

  const markdownRelative = relativePath(htmlPath, copiedMarkdownPath);
  const htmlRelative = relativePath(htmlPath, copiedHtmlPath);
  const rawRelative = relativePath(htmlPath, copiedRawHtmlPath);

  const shell = renderShell(
    article.title,
    `
    <div class="topbar">
      <a class="back-link" href="../index.html">返回资料索引</a>
      <span class="pill">本地离线副本</span>
    </div>
    <article class="article">
      <h1>${escapeHtml(article.title)}</h1>
      <p class="article-summary">${escapeHtml(article.excerpt || '无摘要')}</p>
      <ul class="meta-grid">
        <li><strong>ID：</strong>${escapeHtml(article.id)}</li>
        <li><strong>发布时间：</strong>${escapeHtml(article.publishedAt ?? '未知')}</li>
        <li><strong>抓取时间：</strong>${escapeHtml(article.fetchedAt)}</li>
        <li><strong>作者：</strong>${escapeHtml(article.byline ?? '未知')}</li>
        <li><strong>字数：</strong>${escapeHtml(String(article.wordCount))}</li>
        <li><strong>原文：</strong><a href="${escapeHtml(article.url)}">${escapeHtml(article.url)}</a></li>
      </ul>
      <p class="article-nav">
        <a href="${escapeHtml(markdownRelative)}">Markdown</a>
        ·
        <a href="${escapeHtml(htmlRelative)}">清洗后 HTML</a>
        ·
        <a href="${escapeHtml(rawRelative)}">原始 HTML</a>
      </p>
      <div class="article-content">${body}</div>
    </article>
    `,
    '../styles.css',
  );

  await ensureDir(path.dirname(htmlPath));
  await fs.writeFile(htmlPath, shell, 'utf8');
}

export async function buildStaticSite(articles: ArticleMeta[]): Promise<void> {
  await fs.rm(PATHS.site, { recursive: true, force: true });
  await ensureDir(PATHS.site);
  await writeStyles();

  const sorted = [...articles].sort((a, b) => {
    const aTime = new Date(a.publishedAt ?? a.fetchedAt).getTime();
    const bTime = new Date(b.publishedAt ?? b.fetchedAt).getTime();
    return bTime - aTime;
  });

  await Promise.all(sorted.map((article) => renderArticlePage(article)));

  const cards = sorted
    .map(
      (article) => `
      <a class="article-card" href="./articles/${encodeURIComponent(article.slug)}.html">
        <div class="pill">#${escapeHtml(article.id)}</div>
        <h2>${escapeHtml(article.title)}</h2>
        <p>${escapeHtml(article.excerpt || '无摘要')}</p>
        <p class="article-meta">
          ${escapeHtml(article.publishedAt ?? article.fetchedAt)}
          ·
          ${escapeHtml(article.byline ?? '未知作者')}
          ·
          ${escapeHtml(String(article.wordCount))} 字
        </p>
      </a>
    `,
    )
    .join('\n');

  const indexHtml = renderShell(
    `${CONFIG.siteName} 离线资料库`,
    `
    <section class="hero">
      <span class="pill">离线资料站</span>
      <h1>${escapeHtml(CONFIG.siteName)} 本地检索库</h1>
      <p>当前共收录 ${escapeHtml(formatCount(sorted.length))} 篇文章。这个页面完全基于本地导出内容构建，适合赛前备份与线下检索。</p>
    </section>
    <section class="search-panel">
      <h2>全文搜索</h2>
      <p>如果你用本地静态服务打开本站，Pagefind 搜索会自动加载。</p>
      <div id="search"></div>
    </section>
    <section class="article-list">
      ${cards}
    </section>
    <script src="./pagefind/pagefind-ui.js"></script>
    <script>
      if (window.PagefindUI) {
        new window.PagefindUI({
          element: '#search',
          showSubResults: true,
          excerptLength: 22,
          resetStyles: false
        });
      }
    </script>
    `,
    './styles.css',
  );

  await fs.writeFile(path.join(PATHS.site, 'index.html'), indexHtml, 'utf8');
}

export async function runPagefind(): Promise<void> {
  const pagefindBin = path.join(PATHS.root, 'node_modules', '.bin', process.platform === 'win32' ? 'pagefind.cmd' : 'pagefind');
  await execFileAsync(pagefindBin, ['--site', PATHS.site, '--output-subdir', 'pagefind'], {
    cwd: PATHS.root,
  });
}
