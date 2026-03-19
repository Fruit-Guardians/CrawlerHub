import test from "node:test";
import assert from "node:assert/strict";
import {
  buildMarkdownDocument,
  convertHtmlToMarkdown,
  extractLinks,
  parseArticle
} from "../src/parser/article-parser.js";
import { classifyUrl } from "../src/discovery/url-classifier.js";

const html = `
<!doctype html>
<html lang="zh-cn">
  <head>
    <title>[原创] 一次完整的 Android 签名逆向分析 -看雪安全社区</title>
    <meta property="og:title" content="[原创] 一次完整的 Android 签名逆向分析">
    <meta name="description" content="从抓包到 SO 层的完整逆向过程。">
    <meta name="keywords" content="Android, Frida, Hook">
  </head>
  <body>
    <div class="pt">
      <a href="/">首页</a>
      <a href="/forum-161.htm">移动安全</a>
    </div>
    <h1>[原创] 一次完整的 Android 签名逆向分析</h1>
    <div class="authi">
      <a class="xw1" href="https://bbs.kanxue.com/space-uid-1.htm">FinSectech</a>
      <em>发表于 2026-03-18 10:31</em>
    </div>
    <div class="pcb">
      <div class="t_f">
        <p>第一段内容，说明抓包线索。第二段内容，说明 Java 层定位方法。第三段内容，确保正文足够长。</p>
        <pre><code class="language-javascript">Java.perform(function() {
  console.log("hook");
});</code></pre>
        <p><img src="/data/attachment/forum/202603/test.png" alt="流程图"></p>
      </div>
    </div>
    <a href="/thread-290009-1.htm">详情页</a>
    <a href="/article-20744.htm">文章页</a>
  </body>
</html>
`;

test("classifyUrl should normalize kanxue detail links", () => {
  const thread = classifyUrl("https://bbs.kanxue.com/thread-290009-1.htm");
  assert.equal(thread.type, "detail");
  assert.equal(thread.url, "https://bbs.kanxue.com/thread-290009.htm?style=1");

  const article = classifyUrl("https://bbs.kanxue.com/article-20744.htm");
  assert.equal(article.type, "detail");
  assert.equal(article.articleId, "20744");
});

test("parseArticle should extract kanxue fields", () => {
  const article = parseArticle({
    url: "https://bbs.kanxue.com/thread-290009.htm?style=1",
    finalUrl: "https://bbs.kanxue.com/thread-290009.htm?style=1",
    html
  });

  assert.equal(article.title, "[原创] 一次完整的 Android 签名逆向分析");
  assert.equal(article.author, "FinSectech");
  assert.equal(article.articleId, "290009");
  assert.equal(article.channel, "thread");
  assert.equal(article.category, "移动安全");
  assert.match(article.contentMarkdown, /```javascript/);
  assert.match(article.contentMarkdown, /!\[流程图\]/);
});

test("extractLinks should normalize internal links", () => {
  const links = extractLinks(html, "https://bbs.kanxue.com/thread-290009.htm?style=1");
  assert(links.includes("https://bbs.kanxue.com/thread-290009-1.htm"));
  assert(links.includes("https://bbs.kanxue.com/article-20744.htm"));
});

test("buildMarkdownDocument should include metadata table", () => {
  const markdown = buildMarkdownDocument({
    url: "https://bbs.kanxue.com/thread-290009.htm?style=1",
    canonicalUrl: "https://bbs.kanxue.com/thread-290009.htm?style=1",
    articleId: "290009",
    channel: "thread",
    title: "测试标题",
    author: "测试作者",
    publishedAt: "2026-03-18 10:31",
    updatedAtSource: "",
    category: "移动安全",
    tags: ["Android", "Frida"],
    summary: "摘要",
    coverUrl: "",
    contentHash: "hash",
    crawledAt: "2026-03-18T12:00:00.000Z",
    contentMarkdown: convertHtmlToMarkdown("<p>正文</p>")
  });

  assert.match(markdown, /^\-\-\-/);
  assert.match(markdown, /\| 字段 \| 值 \|/);
  assert.match(markdown, /\# 测试标题/);
});
