import fs from "node:fs";
import path from "node:path";
import { parseArticle } from "../parser/article-parser.js";
import { FileStore } from "../store/file-store.js";

function recoverRawPath(row) {
  if (row.raw_html_path && fs.existsSync(row.raw_html_path)) {
    return row.raw_html_path;
  }

  if (row.markdown_path) {
    const recovered = row.markdown_path
      .replace(`${path.sep}markdown${path.sep}`, `${path.sep}raw${path.sep}`)
      .replace(/\.md$/i, ".html");

    if (fs.existsSync(recovered)) {
      return recovered;
    }
  }

  return "";
}

export class RawRefreshService {
  constructor({ db }) {
    this.db = db;
    this.fileStore = new FileStore();
  }

  run() {
    const rows = this.db.listArticles();
    let refreshed = 0;

    for (const row of rows) {
      const rawPath = recoverRawPath(row);
      if (!rawPath) {
        continue;
      }

      const html = fs.readFileSync(rawPath, "utf8");
      const article = parseArticle({
        url: row.url,
        finalUrl: row.canonical_url || row.url,
        html
      });

      article.crawledAt = row.crawled_at;

      const jsonPath = this.fileStore.saveJson({
        channel: article.channel,
        title: article.title,
        articleId: article.articleId,
        url: article.url,
        payload: {
          ...article,
          rawHtmlPath: rawPath,
          markdownPath: row.markdown_path
        }
      });

      this.db.saveArticle({
        ...article,
        raw_html_path: rawPath,
        json_path: jsonPath,
        markdown_path: row.markdown_path
      });

      refreshed += 1;
    }

    return { refreshed };
  }
}
