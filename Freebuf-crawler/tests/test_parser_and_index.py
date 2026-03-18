import importlib.util
import logging
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "freebuf_crawler.py"
SPEC = importlib.util.spec_from_file_location("freebuf_crawler_mod", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("failed to load freebuf_crawler.py")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

ArticleParser = MODULE.ArticleParser
ArticleBrief = MODULE.ArticleBrief
ArticleStore = MODULE.ArticleStore
CrawlStats = MODULE.CrawlStats


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("freebuf_test")
        self.parser = ArticleParser("https://www.freebuf.com/", self.logger)

    def test_parse_category_page(self):
        html = """
        <div class="article-item">
          <div class="title-left">
            <a href="/articles/web/500001.html"><span class="title">Web 漏洞实战</span></a>
          </div>
          <div class="item-top"><div class="text">一篇关于注入与绕过的文章</div></div>
          <div class="item-bottom">
            <a href="/author/1">Alice</a>
            <span>2026-03-01 08:00:00</span>
          </div>
        </div>
        """
        rows = self.parser.parse_category_page(html, "articles/web", "Web安全")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].article_id, 500001)
        self.assertEqual(rows[0].title, "Web 漏洞实战")
        self.assertEqual(rows[0].author, "Alice")

    def test_parse_detail_page_to_markdown(self):
        long_text = "这是一段用于测试 Markdown 转换的正文。" * 20
        html = f"""
        <html><head>
          <meta name="description" content="摘要信息" />
        </head><body>
          <div class="artical-header">
            <span class="title-span">标题测试 - FreeBuf网络安全行业门户</span>
            <span class="date">2026-03-01 12:00:00</span>
            <div class="author-info"><span class="author">Bob</span></div>
          </div>
          <div class="tabs-panel"><div class="tab"><a href="/articles/web">Web安全</a></div></div>
          <div class="tags-panel"><a class="txt">XSS</a><a class="txt">SQLi</a></div>
          <div class="content-detail">
            <h2>章节一</h2>
            <p>{long_text}</p>
            <pre class="language-python">print('ok')</pre>
            <img src="https://img.example.org/poc.png" alt="PoC图" />
          </div>
        </body></html>
        """
        brief = ArticleBrief(
            url="https://www.freebuf.com/articles/web/500002.html",
            article_id=500002,
            category_slug="articles/web",
            category_name="Web安全",
            source="unit_test",
        )
        article = self.parser.parse_detail_page(
            html,
            brief,
            image_to_md=lambda src, alt: f"![{alt}]({src})",
        )
        self.assertIsNotNone(article)
        assert article is not None
        self.assertEqual(article["title"], "标题测试")
        self.assertEqual(article["author"], "Bob")
        self.assertEqual(article["category_slug"], "web")
        self.assertIn("章节一", article["content"])
        self.assertIn("```python", article["content"])
        self.assertIn("![PoC图](https://img.example.org/poc.png)", article["content"])


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("freebuf_test")

    def test_flush_indexes_builds_sqlite_fts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = ArticleStore(root, self.logger)

            store.save_article(
                {
                    "url": "https://www.freebuf.com/articles/web/1.html",
                    "article_id": 1,
                    "title": "SQL 注入复盘",
                    "summary": "这是摘要",
                    "author": "Alice",
                    "publish_time": "2026-03-01 10:00:00",
                    "category_slug": "web",
                    "category_name": "Web安全",
                    "tags": ["SQLi", "Bypass"],
                    "content": "正文内容 关键字 注入 绕过",
                    "source": "unit_test",
                    "crawled_at": "2026-03-18T12:00:00",
                }
            )
            store.save_article(
                {
                    "url": "https://www.freebuf.com/articles/network/2.html",
                    "article_id": 2,
                    "title": "流量审计笔记",
                    "summary": "这是网络摘要",
                    "author": "Bob",
                    "publish_time": "2026-03-02 10:00:00",
                    "category_slug": "network",
                    "category_name": "网络安全",
                    "tags": ["pcap"],
                    "content": "tcp 三次握手分析",
                    "source": "unit_test",
                    "crawled_at": "2026-03-18T12:01:00",
                }
            )

            store.flush_indexes(CrawlStats())

            sqlite_path = root / "index.sqlite"
            self.assertTrue(sqlite_path.exists())

            conn = sqlite3.connect(sqlite_path)
            try:
                n = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
                self.assertEqual(n, 2)
                fts_hits = conn.execute(
                    "SELECT COUNT(*) FROM articles_fts WHERE articles_fts MATCH ?",
                    ("注入",),
                ).fetchone()[0]
                self.assertGreaterEqual(fts_hits, 1)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
