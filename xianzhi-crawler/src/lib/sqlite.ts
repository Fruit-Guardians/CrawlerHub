import fs from 'node:fs';
import path from 'node:path';
import Database from 'better-sqlite3';
import { PATHS } from '../config.js';
import type { ArticleMeta } from './article-store.js';

export function rebuildSqliteIndex(articles: ArticleMeta[]): string {
  const dbPath = path.join(PATHS.sqlite, 'articles.db');
  fs.mkdirSync(PATHS.sqlite, { recursive: true });
  fs.rmSync(dbPath, { force: true });

  const db = new Database(dbPath);
  db.exec(`
    PRAGMA journal_mode = WAL;

    CREATE TABLE articles (
      id TEXT PRIMARY KEY,
      slug TEXT NOT NULL UNIQUE,
      url TEXT NOT NULL UNIQUE,
      title TEXT NOT NULL,
      excerpt TEXT,
      byline TEXT,
      site_name TEXT,
      published_at TEXT,
      fetched_at TEXT NOT NULL,
      word_count INTEGER NOT NULL,
      markdown_path TEXT NOT NULL,
      clean_html_path TEXT NOT NULL,
      raw_html_path TEXT NOT NULL,
      text_content TEXT NOT NULL
    );

    CREATE VIRTUAL TABLE article_fts USING fts5(
      id UNINDEXED,
      title,
      excerpt,
      byline,
      text_content,
      tokenize = 'unicode61 remove_diacritics 2'
    );
  `);

  const insertArticle = db.prepare(`
    INSERT INTO articles (
      id, slug, url, title, excerpt, byline, site_name, published_at,
      fetched_at, word_count, markdown_path, clean_html_path, raw_html_path, text_content
    ) VALUES (
      @id, @slug, @url, @title, @excerpt, @byline, @siteName, @publishedAt,
      @fetchedAt, @wordCount, @markdownPath, @cleanHtmlPath, @rawHtmlPath, @textContent
    )
  `);

  const insertFts = db.prepare(`
    INSERT INTO article_fts (id, title, excerpt, byline, text_content)
    VALUES (@id, @title, @excerpt, @byline, @textContent)
  `);

  const selectMarkdown = db.prepare(`SELECT markdown_path FROM articles WHERE id = ?`);
  void selectMarkdown;

  const transaction = db.transaction((rows: ArticleMeta[]) => {
    for (const article of rows) {
      const textContent = fs.readFileSync(article.markdownPath, 'utf8');
      insertArticle.run({
        ...article,
        siteName: article.siteName,
        publishedAt: article.publishedAt,
        cleanHtmlPath: article.cleanHtmlPath,
        rawHtmlPath: article.rawHtmlPath,
        markdownPath: article.markdownPath,
        textContent,
      });
      insertFts.run({
        id: article.id,
        title: article.title,
        excerpt: article.excerpt,
        byline: article.byline,
        textContent,
      });
    }
  });

  transaction(articles);
  db.close();
  return dbPath;
}
