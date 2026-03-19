import fs from "node:fs";
import Database from "better-sqlite3";
import { config } from "../config.js";
import { ensureDir } from "../utils/fs.js";
import { nowIso } from "../utils/time.js";

ensureDir(config.paths.dbDir);

export class CrawlDatabase {
  constructor(dbFile = config.paths.dbFile) {
    this.dbFile = dbFile;
    this.db = new Database(dbFile);
    this.db.pragma("journal_mode = WAL");
    this.db.pragma("foreign_keys = ON");
    this.migrate();
  }

  migrate() {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL UNIQUE,
        type TEXT NOT NULL,
        depth INTEGER NOT NULL DEFAULT 0,
        source TEXT,
        parent_url TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        priority INTEGER NOT NULL DEFAULT 0,
        attempts INTEGER NOT NULL DEFAULT 0,
        last_error TEXT,
        claimed_at TEXT,
        finished_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );

      CREATE INDEX IF NOT EXISTS idx_tasks_type_status ON tasks(type, status);
      CREATE INDEX IF NOT EXISTS idx_tasks_priority_status ON tasks(priority DESC, status);

      CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL UNIQUE,
        canonical_url TEXT,
        article_id TEXT,
        channel TEXT,
        title TEXT,
        author TEXT,
        published_at TEXT,
        updated_at_source TEXT,
        category TEXT,
        tags_json TEXT,
        summary TEXT,
        cover_url TEXT,
        content_html TEXT,
        content_text TEXT,
        content_markdown TEXT,
        content_hash TEXT,
        raw_html_path TEXT,
        json_path TEXT,
        markdown_path TEXT,
        crawl_status TEXT NOT NULL DEFAULT 'done',
        crawled_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );

      CREATE INDEX IF NOT EXISTS idx_articles_article_id ON articles(article_id);
      CREATE INDEX IF NOT EXISTS idx_articles_channel ON articles(channel);
      CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at);

      CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
        title,
        author,
        category,
        tags,
        summary,
        content_text,
        url UNINDEXED
      );
    `);
  }

  seedTasks(tasks) {
    const insert = this.db.prepare(`
      INSERT INTO tasks (url, type, depth, source, parent_url, status, priority, attempts, created_at, updated_at)
      VALUES (@url, @type, @depth, @source, @parent_url, 'pending', @priority, 0, @created_at, @updated_at)
      ON CONFLICT(url) DO NOTHING
    `);

    const now = nowIso();
    const tx = this.db.transaction((rows) => {
      for (const task of rows) {
        insert.run({
          url: task.url,
          type: task.type,
          depth: task.depth ?? 0,
          source: task.source ?? null,
          parent_url: task.parentUrl ?? null,
          priority: task.priority ?? 0,
          created_at: now,
          updated_at: now
        });
      }
    });

    tx(tasks);
  }

  enqueueTasks(tasks) {
    if (!tasks.length) {
      return 0;
    }

    const insert = this.db.prepare(`
      INSERT INTO tasks (url, type, depth, source, parent_url, status, priority, attempts, created_at, updated_at)
      VALUES (@url, @type, @depth, @source, @parent_url, 'pending', @priority, 0, @created_at, @updated_at)
      ON CONFLICT(url) DO UPDATE SET
        depth = MIN(tasks.depth, excluded.depth),
        priority = MAX(tasks.priority, excluded.priority),
        source = COALESCE(tasks.source, excluded.source),
        parent_url = COALESCE(tasks.parent_url, excluded.parent_url),
        updated_at = excluded.updated_at
    `);

    const now = nowIso();
    const tx = this.db.transaction((rows) => {
      for (const task of rows) {
        insert.run({
          url: task.url,
          type: task.type,
          depth: task.depth ?? 0,
          source: task.source ?? null,
          parent_url: task.parentUrl ?? null,
          priority: task.priority ?? 0,
          created_at: now,
          updated_at: now
        });
      }
    });

    tx(tasks);
    return tasks.length;
  }

  listPendingTasks(type, limit = 100) {
    return this.db
      .prepare(`
        SELECT *
        FROM tasks
        WHERE type = ? AND status = 'pending'
        ORDER BY priority DESC, depth ASC, id ASC
        LIMIT ?
      `)
      .all(type, limit);
  }

  markTaskRunning(url) {
    const now = nowIso();
    this.db
      .prepare(`
        UPDATE tasks
        SET status = 'running',
            attempts = attempts + 1,
            claimed_at = ?,
            updated_at = ?
        WHERE url = ?
      `)
      .run(now, now, url);
  }

  markTaskDone(url) {
    const now = nowIso();
    this.db
      .prepare(`
        UPDATE tasks
        SET status = 'done',
            last_error = NULL,
            finished_at = ?,
            updated_at = ?
        WHERE url = ?
      `)
      .run(now, now, url);
  }

  markTaskFailed(url, errorMessage) {
    const now = nowIso();
    this.db
      .prepare(`
        UPDATE tasks
        SET status = 'failed',
            last_error = ?,
            updated_at = ?
        WHERE url = ?
      `)
      .run(errorMessage, now, url);
  }

  resetRunningTasks() {
    const now = nowIso();
    this.db
      .prepare(`
        UPDATE tasks
        SET status = 'pending',
            claimed_at = NULL,
            updated_at = ?
        WHERE status = 'running'
      `)
      .run(now);
  }

  saveArticle(article) {
    const now = nowIso();
    this.db
      .prepare(`
        INSERT INTO articles (
          url, canonical_url, article_id, channel, title, author, published_at,
          updated_at_source, category, tags_json, summary, cover_url,
          content_html, content_text, content_markdown, content_hash,
          raw_html_path, json_path, markdown_path, crawl_status, crawled_at, updated_at
        ) VALUES (
          @url, @canonical_url, @article_id, @channel, @title, @author, @published_at,
          @updated_at_source, @category, @tags_json, @summary, @cover_url,
          @content_html, @content_text, @content_markdown, @content_hash,
          @raw_html_path, @json_path, @markdown_path, @crawl_status, @crawled_at, @updated_at
        )
        ON CONFLICT(url) DO UPDATE SET
          canonical_url = excluded.canonical_url,
          article_id = excluded.article_id,
          channel = excluded.channel,
          title = excluded.title,
          author = excluded.author,
          published_at = excluded.published_at,
          updated_at_source = excluded.updated_at_source,
          category = excluded.category,
          tags_json = excluded.tags_json,
          summary = excluded.summary,
          cover_url = excluded.cover_url,
          content_html = excluded.content_html,
          content_text = excluded.content_text,
          content_markdown = excluded.content_markdown,
          content_hash = excluded.content_hash,
          raw_html_path = excluded.raw_html_path,
          json_path = excluded.json_path,
          markdown_path = excluded.markdown_path,
          crawl_status = excluded.crawl_status,
          crawled_at = excluded.crawled_at,
          updated_at = excluded.updated_at
      `)
      .run({
        url: article.url,
        canonical_url: article.canonicalUrl || article.url,
        article_id: article.articleId || null,
        channel: article.channel || null,
        title: article.title || null,
        author: article.author || null,
        published_at: article.publishedAt || null,
        updated_at_source: article.updatedAtSource || null,
        category: article.category || null,
        tags_json: JSON.stringify(article.tags || []),
        summary: article.summary || null,
        cover_url: article.coverUrl || null,
        content_html: article.contentHtml || null,
        content_text: article.contentText || null,
        content_markdown: article.contentMarkdown || null,
        content_hash: article.contentHash || null,
        raw_html_path: article.raw_html_path || null,
        json_path: article.json_path || null,
        markdown_path: article.markdown_path || null,
        crawl_status: article.crawlStatus || "done",
        crawled_at: article.crawledAt || now,
        updated_at: now
      });

    const row = this.db.prepare(`SELECT id, tags_json FROM articles WHERE url = ?`).get(article.url);
    if (row?.id) {
      this.syncArticleFts(row.id);
    }
  }

  syncArticleFts(articleRowId) {
    const row = this.db
      .prepare(`
        SELECT id, title, author, category, tags_json, summary, content_text, canonical_url, url
        FROM articles
        WHERE id = ?
      `)
      .get(articleRowId);

    if (!row) {
      return;
    }

    this.db.prepare(`DELETE FROM articles_fts WHERE rowid = ?`).run(articleRowId);
    this.db
      .prepare(`
        INSERT INTO articles_fts(rowid, title, author, category, tags, summary, content_text, url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `)
      .run(
        articleRowId,
        row.title || "",
        row.author || "",
        row.category || "",
        JSON.parse(row.tags_json || "[]").join(" "),
        row.summary || "",
        row.content_text || "",
        row.canonical_url || row.url || ""
      );
  }

  listArticles() {
    return this.db.prepare(`SELECT * FROM articles ORDER BY published_at DESC, id DESC`).all();
  }

  searchArticles(query, limit = 10) {
    return this.db
      .prepare(`
        SELECT a.id, a.title, a.author, a.category, a.published_at, a.url, a.markdown_path,
               snippet(articles_fts, 5, '[', ']', '…', 18) AS snippet
        FROM articles_fts
        JOIN articles a ON a.id = articles_fts.rowid
        WHERE articles_fts MATCH ?
        ORDER BY bm25(articles_fts)
        LIMIT ?
      `)
      .all(query, limit);
  }

  getStats() {
    const taskRows = this.db
      .prepare(`SELECT type, status, COUNT(*) AS count FROM tasks GROUP BY type, status ORDER BY type, status`)
      .all();

    const articleRows = this.db
      .prepare(`SELECT channel, COUNT(*) AS count FROM articles GROUP BY channel ORDER BY count DESC`)
      .all();

    return {
      dbFile: this.dbFile,
      dbExists: fs.existsSync(this.dbFile),
      tasks: taskRows,
      articles: articleRows,
      articleTotal:
        this.db.prepare(`SELECT COUNT(*) AS count FROM articles`).get()?.count ?? 0
    };
  }
}
