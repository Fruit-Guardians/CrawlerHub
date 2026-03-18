# xianzhi-crawler

先知社区离线资料采集工具，采用 `Crawlee + Playwright + SQLite + Pagefind` 的混合方案。

它的目标不是只把页面爬下来，而是同时完成这几件事：

- 用 `https://xz.aliyun.com/feed` 做增量种子
- 用 `/news?page=n` 做历史回填
- 用真实浏览器处理详情页的 JS/WAF 挑战
- 输出 `raw.html + article.html + article.md`
- 生成 `SQLite FTS5` 全文库
- 生成本地静态资料站和 `Pagefind` 搜索索引

## 环境

- Node.js 20+
- npm 10+

首次安装后执行：

```bash
npm install
npx playwright install chromium
```

## 常用命令

只做种子发现：

```bash
npm run seed
```

只跑详情抓取：

```bash
npm run crawl
```

按截止日期继续回填：

```bash
npm run backfill -- 2025-04-23
```

只重建离线站点和索引：

```bash
npm run site
```

全流程：

```bash
npm run all
```

## 环境变量

默认值偏稳定，适合先知这种有挑战页的站点。

```bash
XZ_LIST_PAGES=10
XZ_DETAIL_CONCURRENCY=1
XZ_MAX_ARTICLES=20
XZ_HEADLESS=true
XZ_BROWSER_TIMEOUT_MS=45000
XZ_MIN_ARTICLE_TEXT_LENGTH=180
```

例子：

```bash
XZ_LIST_PAGES=50 XZ_DETAIL_CONCURRENCY=2 npm run all
```

只做一篇冒烟验证：

```bash
XZ_MAX_ARTICLES=1 npm run crawl
```

按上海时区日期截止回填：

```bash
XZ_UNTIL_DATE=2025-04-23 npm run backfill
```

## 产物目录

```text
storage/
  articles/<slug>/
    raw.html
    article.html
    article.md
    meta.json
    assets/
  feeds/feed.json
  reports/history-seed.json
  sqlite/articles.db
  crawlee/...

dist/site/
  index.html
  articles/*.html
  article-assets/
  source/
  pagefind/
```

## 离线使用

资料站生成后，建议在无网环境下用本地静态服务打开：

```bash
python3 -m http.server 8000 -d dist/site
```

然后访问：

```text
http://127.0.0.1:8000
```

说明：

- 文章页面可以直接离线浏览
- `Pagefind` 搜索在本地静态服务下可用
- `storage/sqlite/articles.db` 可以用于脚本检索或命令行查询

## SQLite 查询示例

看总文章数：

```bash
sqlite3 storage/sqlite/articles.db 'select count(*) from articles;'
```

按关键词搜标题和内容：

```bash
sqlite3 storage/sqlite/articles.db "
  select id, title
  from article_fts
  where article_fts match 'Java 反序列化'
  limit 20;
"
```

## 重新全量抓取

当前详情队列会持久化，适合断点续跑。

如果你想从头重来，可以删除这些目录：

```bash
rm -rf storage/articles storage/sqlite dist/site
rm -rf storage/crawlee/request_queues/xianzhi-article-details
```

然后重新执行：

```bash
npm run all
```

## 设计说明

- `src/workflows/seed.ts`
  : Feed + 历史列表发现
- `src/workflows/crawl.ts`
  : Playwright 详情抓取与挑战页处理
- `src/workflows/backfill.ts`
  : 基于 `/api/v2/news` 的按日期历史回填
- `src/lib/normalize.ts`
  : Readability 正文清洗、资源镜像、Markdown 转换
- `src/lib/sqlite.ts`
  : SQLite FTS5 索引构建
- `src/lib/site.ts`
  : 静态资料站与 Pagefind 产物生成

## 已验证内容

- `npm run check`
- `npm run seed`
- `XZ_MAX_ARTICLES=1 npm run crawl`
- `npm run site`

在当前工作区里，已经成功抓到先知文章并生成：

- Markdown
- HTML
- 资源镜像
- SQLite 全文库
- Pagefind 静态搜索站
