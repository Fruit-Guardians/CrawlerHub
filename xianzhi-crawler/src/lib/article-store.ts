import fs from 'node:fs/promises';
import path from 'node:path';
import type { NormalizedArticle } from './normalize.js';
import { listDirs, readJson, writeJson } from './fs.js';
import { PATHS } from '../config.js';

export interface ArticleMeta {
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
  textContentLength: number;
  rawHtmlPath: string;
  cleanHtmlPath: string;
  markdownPath: string;
}

export async function saveArticle(article: NormalizedArticle): Promise<ArticleMeta> {
  await fs.writeFile(article.rawHtmlPath, article.rawHtml, 'utf8');
  await fs.writeFile(article.cleanHtmlPath, `<!doctype html><html><body>${article.html}</body></html>\n`, 'utf8');
  await fs.writeFile(article.markdownPath, `${article.markdown.trim()}\n`, 'utf8');

  const meta: ArticleMeta = {
    id: article.id,
    slug: article.slug,
    url: article.url,
    title: article.title,
    excerpt: article.excerpt,
    byline: article.byline,
    siteName: article.siteName,
    publishedAt: article.publishedAt,
    fetchedAt: article.fetchedAt,
    wordCount: article.wordCount,
    textContentLength: article.textContent.length,
    rawHtmlPath: article.rawHtmlPath,
    cleanHtmlPath: article.cleanHtmlPath,
    markdownPath: article.markdownPath,
  };

  await writeJson(article.metaPath, meta);
  return meta;
}

export async function loadAllArticles(): Promise<ArticleMeta[]> {
  const dirs = await listDirs(PATHS.articles);
  const loaded = await Promise.all(
    dirs.map(async (dir) => readJson<ArticleMeta>(path.join(dir, 'meta.json'))),
  );

  return loaded.filter((item): item is ArticleMeta => item !== null);
}
