import path from "node:path";
import { config } from "../config.js";
import { ensureDir, writeBuffer, writeJson, writeUtf8 } from "../utils/fs.js";
import { sha1 } from "../utils/hash.js";
import { normalizeFilename } from "../utils/text.js";

export class FileStore {
  constructor() {
    ensureDir(config.paths.rawDir);
    ensureDir(config.paths.jsonDir);
    ensureDir(config.paths.markdownDir);
    ensureDir(config.paths.assetDir);
  }

  buildArticleBase(channel, title, articleId, url) {
    const shard = channel || "uncategorized";
    const slug = normalizeFilename(title || articleId || sha1(url).slice(0, 12));
    const safeId = articleId || sha1(url).slice(0, 12);
    const baseName = `${safeId}-${slug}`;

    return {
      shard,
      baseName
    };
  }

  getMarkdownPath({ channel, title, articleId, url }) {
    const { shard, baseName } = this.buildArticleBase(channel, title, articleId, url);
    return path.join(config.paths.markdownDir, shard, `${baseName}.md`);
  }

  saveRawHtml({ channel, title, articleId, url, html }) {
    const { shard, baseName } = this.buildArticleBase(channel, title, articleId, url);
    const filePath = path.join(config.paths.rawDir, shard, `${baseName}.html`);
    writeUtf8(filePath, html);
    return filePath;
  }

  saveJson({ channel, title, articleId, url, payload }) {
    const { shard, baseName } = this.buildArticleBase(channel, title, articleId, url);
    const filePath = path.join(config.paths.jsonDir, shard, `${baseName}.json`);
    writeJson(filePath, payload);
    return filePath;
  }

  saveMarkdown({ channel, title, articleId, url, markdown }) {
    const filePath = this.getMarkdownPath({ channel, title, articleId, url });
    writeUtf8(filePath, markdown);
    return filePath;
  }

  saveAsset({ channel, title, articleId, url, fileName, payload }) {
    const { shard, baseName } = this.buildArticleBase(channel, title, articleId, url);
    const filePath = path.join(config.paths.assetDir, shard, baseName, fileName);
    writeBuffer(filePath, payload);
    return filePath;
  }
}
