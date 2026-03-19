import path from "node:path";
import * as cheerio from "cheerio";
import { config } from "../config.js";
import { buildMarkdownDocument, convertHtmlToMarkdown } from "../parser/article-parser.js";
import { FileStore } from "../store/file-store.js";
import { logger } from "../utils/logger.js";

function pickAssetExtension(response, url) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("png")) return ".png";
  if (contentType.includes("jpeg")) return ".jpg";
  if (contentType.includes("gif")) return ".gif";
  if (contentType.includes("webp")) return ".webp";

  try {
    return new URL(url).pathname.match(/\.[a-zA-Z0-9]+$/)?.[0] || ".bin";
  } catch {
    return ".bin";
  }
}

async function localizeImages(article, fileStore) {
  if (!config.export.downloadAssets || !article.contentHtml) {
    return {
      contentHtml: article.contentHtml,
      downloadedAssets: 0
    };
  }

  const wrapped = `<div id="root">${article.contentHtml}</div>`;
  const $ = cheerio.load(wrapped);
  const markdownPath = fileStore.getMarkdownPath(article);
  let downloadedAssets = 0;
  let index = 0;

  for (const element of $("img").toArray()) {
    const node = $(element);
    const src = node.attr("src");
    if (!src) {
      continue;
    }

    let assetUrl = src;
    try {
      assetUrl = new URL(src, article.canonicalUrl || article.url).toString();
    } catch {
      continue;
    }

    try {
      const response = await fetch(assetUrl, {
        headers: {
          "user-agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        }
      });

      if (!response.ok) {
        continue;
      }

      const payload = Buffer.from(await response.arrayBuffer());
      index += 1;
      const ext = pickAssetExtension(response, assetUrl);
      const fileName = `img-${String(index).padStart(3, "0")}${ext}`;
      const assetPath = fileStore.saveAsset({
        channel: article.channel,
        title: article.title,
        articleId: article.articleId,
        url: article.url,
        fileName,
        payload
      });

      const relativePath = path.relative(path.dirname(markdownPath), assetPath).replace(/\\/g, "/");
      node.attr("src", relativePath);
      downloadedAssets += 1;
    } catch (error) {
      logger.warn({ assetUrl, error: error.message }, "图片下载失败，保留原链接");
    }
  }

  return {
    contentHtml: $("#root").html() || article.contentHtml,
    downloadedAssets
  };
}

export class MarkdownExporter {
  constructor({ db }) {
    this.db = db;
    this.fileStore = new FileStore();
  }

  async run() {
    const rows = this.db.listArticles();
    let count = 0;
    let assetCount = 0;

    for (const row of rows) {
      const article = {
        url: row.url,
        canonicalUrl: row.canonical_url,
        articleId: row.article_id,
        channel: row.channel,
        title: row.title,
        author: row.author,
        publishedAt: row.published_at,
        updatedAtSource: row.updated_at_source,
        category: row.category,
        tags: JSON.parse(row.tags_json || "[]"),
        summary: row.summary,
        coverUrl: row.cover_url,
        contentHash: row.content_hash,
        crawledAt: row.crawled_at,
        contentHtml: row.content_html,
        contentText: row.content_text,
        contentMarkdown: row.content_markdown,
        raw_html_path: row.raw_html_path,
        json_path: row.json_path
      };

      const localized = await localizeImages(article, this.fileStore);
      const markdown = buildMarkdownDocument({
        ...article,
        contentMarkdown: localized.contentHtml
          ? convertHtmlToMarkdown(localized.contentHtml)
          : article.contentMarkdown
      });

      const markdownPath = this.fileStore.saveMarkdown({
        channel: article.channel,
        title: article.title,
        articleId: article.articleId,
        url: article.url,
        markdown
      });

      this.db.saveArticle({
        ...article,
        contentMarkdown: localized.contentHtml
          ? convertHtmlToMarkdown(localized.contentHtml)
          : article.contentMarkdown,
        raw_html_path: article.raw_html_path,
        json_path: article.json_path,
        markdown_path: markdownPath
      });

      count += 1;
      assetCount += localized.downloadedAssets;
    }

    return { exported: count, downloadedAssets: assetCount };
  }
}
