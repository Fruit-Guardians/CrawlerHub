import * as cheerio from "cheerio";
import { JSDOM } from "jsdom";
import { Readability } from "@mozilla/readability";
import TurndownService from "turndown";
import { sha256 } from "../utils/hash.js";
import { cleanText, normalizeMarkdownWhitespace, truncate } from "../utils/text.js";

function createTurndownService() {
  const service = new TurndownService({
    headingStyle: "atx",
    bulletListMarker: "-",
    codeBlockStyle: "fenced"
  });

  service.addRule("fencedCodeBlocks", {
    filter(node) {
      return node.nodeName === "PRE";
    },
    replacement(_content, node) {
      const codeNode = node.querySelector("code");
      const className = codeNode?.getAttribute("class") || "";
      const language =
        className.match(/language-([\w-]+)/i)?.[1] ||
        className.match(/lang(?:uage)?-([\w-]+)/i)?.[1] ||
        "";
      const text = codeNode?.textContent || node.textContent || "";
      return `\n\n\`\`\`${language}\n${String(text).trimEnd()}\n\`\`\`\n\n`;
    }
  });

  service.addRule("imagePreserveAlt", {
    filter(node) {
      return node.nodeName === "IMG";
    },
    replacement(_content, node) {
      const alt = node.getAttribute("alt") || "image";
      const src = node.getAttribute("src") || "";
      return src ? `![${alt}](${src})` : "";
    }
  });

  return service;
}

const turndown = createTurndownService();

function parseJsonLd($) {
  const blocks = [];

  $('script[type="application/ld+json"]').each((_, element) => {
    const raw = $(element).contents().text();
    if (!raw) {
      return;
    }

    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        blocks.push(...parsed);
      } else {
        blocks.push(parsed);
      }
    } catch {
      // Ignore broken JSON-LD.
    }
  });

  return blocks;
}

function pickArticleFromJsonLd(blocks) {
  return (
    blocks.find((item) => item?.["@type"] === "Article" || item?.["@type"] === "NewsArticle") ||
    blocks.find((item) => item?.headline || item?.articleBody) ||
    null
  );
}

function extractMeta($, selectors) {
  for (const selector of selectors) {
    const node = $(selector).first();
    const value = node.attr("content") || node.attr("datetime") || node.text();
    if (cleanText(value)) {
      return cleanText(value);
    }
  }

  return "";
}

function cleanKanxueTitle(rawTitle) {
  return cleanText(rawTitle)
    .replace(/-.*?看雪.*$/i, "")
    .replace(/-看雪.*$/i, "")
    .replace(/-软件逆向.*$/i, "")
    .replace(/-移动安全.*$/i, "")
    .replace(/-二进制漏洞.*$/i, "")
    .trim();
}

function isGenericKanxueTitle(title) {
  const value = cleanText(title);
  return !value || /看雪安全社区|专业技术交流与安全研究论坛/.test(value);
}

function extractTitle($, articleJsonLd) {
  const candidates = [
    cleanText(articleJsonLd?.headline),
    cleanText($("h3.break-all.subject").first().text()),
    cleanText($("h3.subject").first().text()),
    cleanText($("h1").first().text()),
    cleanText($(".subject").first().text()),
    extractMeta($, ['meta[name="application-name"]']),
    extractMeta($, ['meta[name="keywords"]']),
    extractMeta($, ['meta[name="description"]']),
    extractMeta($, ['meta[property="og:title"]']),
    extractMeta($, ["title"])
  ];

  for (const candidate of candidates) {
    const cleaned = cleanKanxueTitle(candidate);
    if (cleaned && !isGenericKanxueTitle(cleaned)) {
      return cleaned;
    }
  }

  return cleanKanxueTitle(candidates.find(Boolean) || "");
}

function extractAuthor($, articleJsonLd) {
  return (
    cleanText(articleJsonLd?.author?.name || articleJsonLd?.author?.[0]?.name) ||
    extractMeta($, [
      ".authi .xw1",
      ".authi a.xw1",
      ".article-author",
      ".username",
      "a[href*='space-uid']",
      ".pi .authi a"
    ])
  );
}

function extractPublishedAt($, articleJsonLd, fullText) {
  const direct =
    cleanText(articleJsonLd?.datePublished) ||
    extractMeta($, [
      'meta[property="article:published_time"]',
      "time[datetime]",
      ".authi em",
      ".article-time"
    ]);

  if (direct) {
    const matched = direct.match(/\d{4}-\d{1,2}-\d{1,2}(?:\s+\d{1,2}:\d{2})?/);
    return matched?.[0] || direct;
  }

  return fullText.match(/发表于[:：]?\s*(\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2})/)?.[1] || "";
}

function extractCategory($) {
  const appName = extractMeta($, ['meta[name="application-name"]', "title"]);
  const appNameMatched = appName.match(/.+-([^-]+)-看雪/i);
  if (appNameMatched?.[1]) {
    return cleanText(appNameMatched[1]);
  }

  const breadcrumbs = [];
  $(".pt a, .z a, .breadcrumb a").each((_, element) => {
    const text = cleanText($(element).text());
    if (text && !["首页", "社区", "发新帖"].includes(text)) {
      breadcrumbs.push(text);
    }
  });

  if (breadcrumbs.length) {
    return breadcrumbs[breadcrumbs.length - 1];
  }

  return extractMeta($, ['meta[property="article:section"]', ".category"]);
}

function extractTags($, articleJsonLd) {
  const tags = [];

  if (Array.isArray(articleJsonLd?.keywords)) {
    tags.push(...articleJsonLd.keywords);
  } else if (typeof articleJsonLd?.keywords === "string") {
    tags.push(...articleJsonLd.keywords.split(/[，,]/));
  }

  $('meta[name="keywords"]').each((_, element) => {
    tags.push(...String($(element).attr("content") || "").split(/[，,]/));
  });

  $("[rel='tag'], .tag a, .tags a").each((_, element) => {
    tags.push($(element).text());
  });

  return [...new Set(tags.map((tag) => cleanText(tag)).filter(Boolean))];
}

function stripNoise(root, $) {
  root.find("script, style, form, iframe, noscript").remove();
  root.find(".aimg_tip, .quote, .pstatus, .pob, .sign, .tip_4, .jammer").remove();
  root.find(".expandNoteBox, .login_btn, .my-3, .kx-thread-hidden, .hidden-post-container").remove();
  root.find("svg, .modal, .reward, .thumb_list_box, #collection_thumb").remove();
  root.find("img").each((_, element) => {
    const node = $(element);
    const src =
      node.attr("src") ||
      node.attr("file") ||
      node.attr("data-src") ||
      node.attr("zoomfile") ||
      "";

    if (src) {
      node.attr("src", src);
    }
  });
}

function extractArticleRoot($) {
  const candidates = [
    ".message.message_md_type[isfirst='1']",
    ".message.message_md_type",
    ".message",
    ".pcb .t_f",
    ".t_f",
    "#article_content",
    ".article-content",
    ".message.break-all",
    "article",
    ".content"
  ];

  for (const selector of candidates) {
    const node = $(selector).first();
    if (node.length && cleanText(node.text()).length > 120) {
      return node.clone();
    }
  }

  return $("body").clone();
}

function normalizeHtmlFragment(html, pageUrl) {
  const $ = cheerio.load(`<div id="root">${html || ""}</div>`);
  const root = $("#root");
  stripNoise(root, $);

  root.find("img").each((_, element) => {
    const node = $(element);
    const src =
      node.attr("src") ||
      node.attr("file") ||
      node.attr("data-src") ||
      node.attr("zoomfile") ||
      "";

    if (!src) {
      node.remove();
      return;
    }

    try {
      node.attr("src", new URL(src, pageUrl).toString());
    } catch {
      node.attr("src", src);
    }
  });

  root.find("a[href]").each((_, element) => {
    const node = $(element);
    try {
      node.attr("href", new URL(node.attr("href"), pageUrl).toString());
    } catch {
      // Ignore malformed href.
    }
  });

  return root.html() || "";
}

export function extractLinks(html, baseUrl) {
  const $ = cheerio.load(html);
  const links = [];

  $("a[href]").each((_, element) => {
    const href = $(element).attr("href");
    if (!href) {
      return;
    }

    try {
      const url = new URL(href, baseUrl);
      url.hash = "";
      links.push(url.toString());
    } catch {
      // Ignore malformed links.
    }
  });

  return [...new Set(links)];
}

export function convertHtmlToMarkdown(html) {
  return normalizeMarkdownWhitespace(turndown.turndown(html || ""));
}

export function parseArticle({ url, finalUrl, html }) {
  const $ = cheerio.load(html);
  const jsonLdBlocks = parseJsonLd($);
  const articleJsonLd = pickArticleFromJsonLd(jsonLdBlocks);
  const pageUrl = finalUrl || url;
  const articleRoot = extractArticleRoot($);
  const articleHtml = normalizeHtmlFragment(articleRoot.html() || "", pageUrl);
  const readableDoc = new JSDOM(html, { url: pageUrl });
  const readabilityArticle = new Readability(readableDoc.window.document).parse();
  const readableHtml = normalizeHtmlFragment(readabilityArticle?.content || "", pageUrl);
  const preferredHtml =
    cleanText(articleRoot.text()).length >= 120 ? articleHtml : readableHtml || articleHtml;
  const contentText = cleanText(
    readabilityArticle?.textContent || cheerio.load(preferredHtml).text() || articleRoot.text()
  );
  const canonicalUrl = cleanText($('link[rel="canonical"]').first().attr("href")) || pageUrl;
  const fullText = cleanText($("body").text());

  const extractedTitle = extractTitle($, articleJsonLd);
  const extractedSummary =
    cleanText(articleJsonLd?.description) ||
    extractMeta($, ['meta[name="description"]', 'meta[property="og:description"]']);

  return {
    url,
    canonicalUrl,
    articleId:
      canonicalUrl.match(/thread-(\d+)/i)?.[1] ||
      canonicalUrl.match(/article-(\d+)/i)?.[1] ||
      url.match(/thread-(\d+)/i)?.[1] ||
      url.match(/article-(\d+)/i)?.[1] ||
      "",
    channel: canonicalUrl.includes("/thread-") ? "thread" : "article",
    title: extractedTitle || "Untitled",
    author: extractAuthor($, articleJsonLd),
    publishedAt: extractPublishedAt($, articleJsonLd, fullText),
    updatedAtSource: cleanText(articleJsonLd?.dateModified),
    category: extractCategory($),
    tags: extractTags($, articleJsonLd),
    summary:
      (!extractedSummary ||
      extractedSummary === extractedTitle ||
      cleanText(extractMeta($, ['meta[name="keywords"]'])) === extractedSummary)
        ? truncate(contentText, 180)
        : extractedSummary,
    coverUrl: extractMeta($, ['meta[property="og:image"]', 'meta[name="twitter:image"]']),
    contentHtml: preferredHtml,
    contentText,
    contentMarkdown: convertHtmlToMarkdown(preferredHtml),
    contentHash: sha256(`${extractedTitle}\n${contentText}`)
  };
}

function quoteValue(value) {
  return String(value || "").replace(/"/g, '\\"');
}

export function buildMarkdownDocument(article) {
  const frontMatter = [
    "---",
    `title: "${quoteValue(article.title)}"`,
    `url: "${article.url || ""}"`,
    `canonical_url: "${article.canonicalUrl || article.url || ""}"`,
    `article_id: "${article.articleId || ""}"`,
    `channel: "${article.channel || ""}"`,
    `author: "${quoteValue(article.author)}"`,
    `published_at: "${article.publishedAt || ""}"`,
    `updated_at_source: "${article.updatedAtSource || ""}"`,
    `category: "${quoteValue(article.category)}"`,
    "tags:"
  ];

  for (const tag of article.tags || []) {
    frontMatter.push(`  - "${quoteValue(tag)}"`);
  }

  frontMatter.push(`summary: "${quoteValue(article.summary)}"`);
  frontMatter.push(`cover_url: "${article.coverUrl || ""}"`);
  frontMatter.push(`content_hash: "${article.contentHash || ""}"`);
  frontMatter.push(`crawled_at: "${article.crawledAt || ""}"`);
  frontMatter.push("---", "");
  frontMatter.push(`# ${article.title || "Untitled"}`, "");
  frontMatter.push("| 字段 | 值 |");
  frontMatter.push("|---|---|");
  frontMatter.push(`| 作者 | ${article.author || "未知"} |`);
  frontMatter.push(`| 发布时间 | ${article.publishedAt || "未知"} |`);
  frontMatter.push(`| 分类 | ${article.category || "未分类"} |`);
  frontMatter.push(`| 原文链接 | ${article.url || ""} |`);
  frontMatter.push("");
  frontMatter.push(article.contentMarkdown || article.contentText || "");
  frontMatter.push("");

  return frontMatter.join("\n");
}
