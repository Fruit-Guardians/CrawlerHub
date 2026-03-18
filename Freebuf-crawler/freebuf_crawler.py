#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FreeBuf 网络安全文章爬虫（重构版）

核心能力：
1. 分类抓取（可并发）
2. 断点续爬（state.json）
3. 增量去重（manifest）
4. Markdown + 图片本地化
5. 离线检索索引（index.sqlite / index.jsonl / index.csv / summary.json）
6. 可选 ID 扫描模式（绕过前端分页限制）
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import logging
import random
import re
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
import orjson
import requests
import urllib3
from bs4 import BeautifulSoup, NavigableString, Tag
from pydantic import BaseModel, Field, ConfigDict
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from requests.adapters import HTTPAdapter
from selectolax.parser import HTMLParser as FastHTMLParser
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter
from urllib3.util import Retry

try:
    from curl_cffi import requests as curl_requests
except Exception:
    curl_requests = None


DEFAULT_CATEGORIES: List[str] = [
    "articles/container",
    "articles/ai-security",
    "articles/development",
    "articles/endpoint",
    "articles/database",
    "articles/web",
    "articles/network",
    "articles/es",
    "ics-articles",
    "articles/mobile",
    "articles/system",
    "articles/others-articles",
]

CATEGORY_LABELS: Dict[str, str] = {
    "articles/container": "容器安全",
    "articles/ai-security": "AI安全",
    "articles/development": "开发安全",
    "articles/endpoint": "终端安全",
    "articles/database": "数据安全",
    "articles/web": "Web安全",
    "articles/network": "网络安全",
    "articles/es": "企业安全",
    "ics-articles": "工控安全",
    "articles/mobile": "移动安全",
    "articles/system": "系统安全",
    "articles/others-articles": "其他安全",
}

ARTICLE_URL_RE = re.compile(
    r"https?://(?:www\.)?freebuf\.com/articles(?:/[\w-]+)?/(\d+)\.html",
    re.IGNORECASE,
)
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?")
INVALID_TITLE_RE = re.compile(r"^(404|405|403|502|503)$", re.IGNORECASE)
FREEBUF_TITLE_SUFFIX_RE = re.compile(r"\s*-\s*FreeBuf网络安全行业门户\s*$")

ORJSON_OPTS = (
    orjson.OPT_INDENT_2
    | orjson.OPT_NON_STR_KEYS
    | orjson.OPT_SERIALIZE_NUMPY
)


def read_json(path: Path) -> Dict[str, Any]:
    return orjson.loads(path.read_bytes())


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_bytes(orjson.dumps(payload, option=ORJSON_OPTS))


class CrawlConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    base_url: str = "https://www.freebuf.com/"
    output_dir: Path = Path("freebuf_data")
    categories: List[str] = Field(default_factory=lambda: list(DEFAULT_CATEGORIES))

    delay: float = 1.0
    jitter: float = 0.5
    timeout: int = 20
    retries: int = 3
    workers: int = 6

    max_pages_per_category: int = 50
    max_articles_total: Optional[int] = None

    download_images: bool = True
    resume: bool = True
    force: bool = False
    verify_ssl: bool = True

    scan_by_id: bool = False
    id_start: Optional[int] = None
    id_end: Optional[int] = None
    id_batch_size: int = 200


class CrawlStats(BaseModel):
    start_time: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    end_time: str = ""

    discovered: int = 0
    processed: int = 0
    saved: int = 0
    skipped: int = 0
    failed: int = 0
    images_downloaded: int = 0

    categories_finished: int = 0
    id_scan_requests: int = 0

    def as_dict(self) -> Dict[str, Any]:
        now = datetime.now()
        start = datetime.fromisoformat(self.start_time)
        elapsed = max((now - start).total_seconds(), 0.0)
        payload = self.model_dump()
        payload["elapsed_seconds"] = round(elapsed, 2)
        payload["articles_per_minute"] = round(self.saved / max(elapsed / 60.0, 0.1), 2)
        return payload


class ArticleBrief(BaseModel):
    model_config = ConfigDict(extra="ignore")

    url: str
    article_id: Optional[int] = None
    title: str = ""
    summary: str = ""
    author: str = ""
    publish_time: str = ""
    category_slug: str = ""
    category_name: str = ""
    source: str = ""


class HttpClient:
    """线程内复用三层传输客户端。

    顺序：
    1. httpx (http2)
    2. requests
    3. curl_cffi (浏览器指纹/TLS 栈，作为最后兜底)
    """

    def __init__(self, config: CrawlConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self._local = threading.local()
        self._requests_local = threading.local()
        self._curl_local = threading.local()
        self._clients: List[httpx.Client] = []
        self._request_sessions: List[requests.Session] = []
        self._curl_sessions: List[Any] = []
        self._client_lock = threading.Lock()
        self._requests_lock = threading.Lock()
        self._curl_lock = threading.Lock()
        self._force_requests = threading.Event()
        self._disable_curl = threading.Event()

        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }
        self._limits = httpx.Limits(max_connections=128, max_keepalive_connections=64)
        self._timeout = httpx.Timeout(
            connect=min(10.0, float(self.config.timeout)),
            read=float(self.config.timeout),
            write=float(self.config.timeout),
            pool=min(10.0, float(self.config.timeout)),
        )

        if not self.config.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _build_client(self) -> httpx.Client:
        client = httpx.Client(
            http2=True,
            verify=self.config.verify_ssl,
            follow_redirects=True,
            headers=self._headers,
            timeout=self._timeout,
            limits=self._limits,
        )
        with self._client_lock:
            self._clients.append(client)
        return client

    def _client(self) -> httpx.Client:
        if not hasattr(self._local, "client"):
            self._local.client = self._build_client()
        return self._local.client

    def _build_requests_session(self) -> requests.Session:
        session = requests.Session()
        retries = max(int(self.config.retries), 0)
        retry_policy = Retry(
            total=retries,
            connect=retries,
            read=retries,
            status=retries,
            backoff_factor=0.6,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET", "HEAD"}),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(
            pool_connections=128,
            pool_maxsize=128,
            max_retries=retry_policy,
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update(self._headers)
        with self._requests_lock:
            self._request_sessions.append(session)
        return session

    def _requests_session(self) -> requests.Session:
        if not hasattr(self._requests_local, "session"):
            self._requests_local.session = self._build_requests_session()
        return self._requests_local.session

    def _build_curl_session(self):
        if curl_requests is None:
            return None
        session = curl_requests.Session()
        session.headers.update(self._headers)
        with self._curl_lock:
            self._curl_sessions.append(session)
        return session

    def _curl_session(self):
        if curl_requests is None:
            return None
        if not hasattr(self._curl_local, "session"):
            self._curl_local.session = self._build_curl_session()
        return self._curl_local.session

    def _request_with_retry(self, url: str) -> httpx.Response:
        attempts = max(int(self.config.retries), 0) + 1
        retryer = Retrying(
            stop=stop_after_attempt(attempts),
            wait=wait_exponential_jitter(initial=0.5, max=8.0),
            retry=retry_if_exception_type(
                (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError, httpx.WriteError)
            ),
            reraise=True,
        )
        for attempt in retryer:
            with attempt:
                response = self._client().get(url)
                response.raise_for_status()
                return response
        raise RuntimeError("unreachable")

    def _request_with_requests(self, url: str) -> Optional[requests.Response]:
        try:
            resp = self._requests_session().get(
                url,
                timeout=float(self.config.timeout),
                verify=self.config.verify_ssl,
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            self.logger.debug("requests 请求失败: %s, error=%s", url, exc)
            return None

        if resp.status_code in {403, 404, 405}:
            return None
        if resp.status_code >= 400:
            self.logger.debug("requests HTTP 状态异常: %s (%s)", url, resp.status_code)
            return None
        return resp

    def _request_with_curl(self, url: str) -> Optional[Any]:
        if curl_requests is None or self._disable_curl.is_set():
            return None

        session = self._curl_session()
        if session is None:
            return None

        last_exc: Optional[Exception] = None
        for fp in ("chrome124", "chrome120", "safari17_0"):
            try:
                resp = session.get(
                    url,
                    timeout=float(self.config.timeout),
                    verify=self.config.verify_ssl,
                    allow_redirects=True,
                    impersonate=fp,
                )
            except Exception as exc:
                last_exc = exc
                continue

            status = int(getattr(resp, "status_code", 0) or 0)
            if status in {404, 405}:
                return None
            if status in {403}:
                continue
            if status >= 400:
                continue
            return resp

        if last_exc:
            msg = str(last_exc).lower()
            if "invalid library" in msg or "curl_cffi" in msg:
                self._disable_curl.set()
            self.logger.debug("curl_cffi 请求失败: %s, error=%s", url, last_exc)
        return None

    @staticmethod
    def _is_tls_eof(exc: httpx.HTTPError) -> bool:
        text = str(exc).lower()
        return "unexpected eof while reading" in text or "ssl: eof" in text

    def _fallback_request(self, url: str) -> Optional[Any]:
        resp = self._request_with_requests(url)
        if resp is not None:
            return resp
        return self._request_with_curl(url)

    def get(self, url: str) -> Optional[Any]:
        if self._force_requests.is_set():
            return self._fallback_request(url)

        try:
            return self._request_with_retry(url)
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if code in {404, 405}:
                return None
            self.logger.debug("httpx HTTP 状态异常，降级到后备链路: %s (%s)", url, code)
            return self._fallback_request(url)
        except httpx.HTTPError as exc:
            if self._is_tls_eof(exc):
                self._force_requests.set()
                self.logger.warning("检测到 TLS EOF，后续请求跳过 httpx，切换后备链路")
            else:
                self.logger.debug("httpx 请求失败，降级到后备链路: %s, error=%s", url, exc)
            return self._fallback_request(url)

    def fetch_text(self, url: str) -> Optional[str]:
        resp = self.get(url)
        if not resp:
            return None
        return resp.text

    def fetch_binary(self, url: str) -> Optional[tuple[bytes, str]]:
        resp = self.get(url)
        if not resp:
            return None
        content_type = resp.headers.get("Content-Type", "")
        return resp.content, content_type

    def close(self) -> None:
        with self._client_lock:
            clients = list(self._clients)
            self._clients.clear()
        for client in clients:
            try:
                client.close()
            except Exception:
                pass
        with self._requests_lock:
            sessions = list(self._request_sessions)
            self._request_sessions.clear()
        for session in sessions:
            try:
                session.close()
            except Exception:
                pass
        with self._curl_lock:
            curl_sessions = list(self._curl_sessions)
            self._curl_sessions.clear()
        for session in curl_sessions:
            try:
                session.close()
            except Exception:
                pass


class CrawlState:
    """断点状态：已爬 URL、分类分页进度、ID 扫描进度。"""

    def __init__(self, path: Path, resume: bool, logger: logging.Logger):
        self.path = path
        self.resume = resume
        self.logger = logger
        self.lock = threading.Lock()

        self.data: Dict[str, Any] = {
            "version": 2,
            "updated_at": "",
            "crawled_urls": [],
            "failed_urls": {},
            "category_next_page": {},
            "last_scanned_id": None,
        }
        self._crawled: Set[str] = set()

        self._load()

    def _load(self) -> None:
        if not self.resume or not self.path.exists():
            return
        try:
            payload = read_json(self.path)
            if isinstance(payload, dict):
                self.data.update(payload)
                self._crawled = set(self.data.get("crawled_urls", []))
                self.logger.info("已加载断点状态：%d 条 URL", len(self._crawled))
        except Exception as exc:
            self.logger.warning("读取 state 失败，使用空状态继续: %s", exc)

    def save(self) -> None:
        with self.lock:
            self.data["updated_at"] = datetime.now().isoformat(timespec="seconds")
            self.data["crawled_urls"] = sorted(self._crawled)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix(".tmp")
            write_json(temp, self.data)
            temp.replace(self.path)

    def is_crawled(self, url: str) -> bool:
        return url in self._crawled

    def mark_crawled(self, url: str) -> None:
        with self.lock:
            self._crawled.add(url)
            self.data.setdefault("failed_urls", {}).pop(url, None)

    def mark_failed(self, url: str, reason: str) -> None:
        with self.lock:
            self.data.setdefault("failed_urls", {})[url] = {
                "reason": reason,
                "time": datetime.now().isoformat(timespec="seconds"),
            }

    def next_page(self, category: str) -> int:
        return int(self.data.get("category_next_page", {}).get(category, 1))

    def set_next_page(self, category: str, page: int) -> None:
        with self.lock:
            self.data.setdefault("category_next_page", {})[category] = int(page)

    def set_last_scanned_id(self, article_id: int) -> None:
        with self.lock:
            self.data["last_scanned_id"] = int(article_id)


class ArticleStore:
    """文章存储 + 索引输出。"""

    def __init__(self, output_dir: Path, logger: logging.Logger):
        self.output_dir = output_dir
        self.logger = logger
        self.images_dir = self.output_dir / "images"
        self.logs_dir = self.output_dir / "logs"

        self.manifest_path = self.output_dir / "manifest.json"
        self.index_jsonl_path = self.output_dir / "index.jsonl"
        self.index_csv_path = self.output_dir / "index.csv"
        self.index_sqlite_path = self.output_dir / "index.sqlite"
        self.summary_path = self.output_dir / "summary.json"

        self.lock = threading.Lock()
        self.manifest: Dict[str, Any] = {
            "version": 2,
            "updated_at": "",
            "articles": {},
        }

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._load_manifest()

    def _load_manifest(self) -> None:
        if not self.manifest_path.exists():
            return
        try:
            payload = read_json(self.manifest_path)
            if isinstance(payload, dict) and "articles" in payload:
                self.manifest.update(payload)
                self.logger.info("已加载 manifest：%d 篇", len(self.manifest["articles"]))
        except Exception as exc:
            self.logger.warning("读取 manifest 失败，继续使用空 manifest: %s", exc)

    def has_url(self, url: str) -> bool:
        return url in self.manifest.get("articles", {})

    @staticmethod
    def safe_slug(text: str, max_len: int = 80) -> str:
        text = re.sub(r"[\\/:*?\"<>|]", "", text)
        text = re.sub(r"\s+", "_", text.strip())
        text = re.sub(r"_+", "_", text)
        text = text.strip("_")
        if not text:
            text = "untitled"
        return text[:max_len].rstrip("_")

    def _unique_path(self, folder: Path, base_name: str) -> Path:
        candidate = folder / f"{base_name}.md"
        if not candidate.exists():
            return candidate
        i = 1
        while True:
            cand = folder / f"{base_name}_{i}.md"
            if not cand.exists():
                return cand
            i += 1

    def save_article(self, article: Dict[str, Any], force: bool = False) -> Optional[Dict[str, Any]]:
        """保存 Markdown 并写入 manifest。"""
        url = article.get("url", "").strip()
        if not url:
            return None

        with self.lock:
            existing = self.manifest["articles"].get(url)
            if existing and not force:
                return existing

            category_slug = self.safe_slug(article.get("category_slug") or "uncategorized", max_len=40)
            category_dir = self.output_dir / category_slug
            category_dir.mkdir(parents=True, exist_ok=True)

            article_id = article.get("article_id")
            title = article.get("title") or f"article_{article_id or 'unknown'}"
            safe_title = self.safe_slug(title)
            if article_id:
                filename_base = f"{article_id}_{safe_title}"
            else:
                filename_base = safe_title

            if existing and force and existing.get("path"):
                path = self.output_dir / existing["path"]
            else:
                path = self._unique_path(category_dir, filename_base)

            markdown = self._build_markdown(article)
            path.write_text(markdown, encoding="utf-8")

            record = {
                "url": url,
                "article_id": article_id,
                "title": article.get("title", ""),
                "summary": article.get("summary", ""),
                "excerpt": self._build_excerpt(article.get("content", "")),
                "author": article.get("author", ""),
                "publish_time": article.get("publish_time", ""),
                "category_slug": category_slug,
                "category_name": article.get("category_name", ""),
                "tags": article.get("tags", []),
                "image_count": int(article.get("image_count", 0)),
                "source": article.get("source", ""),
                "path": str(path.relative_to(self.output_dir)),
                "crawled_at": article.get(
                    "crawled_at", datetime.now().isoformat(timespec="seconds")
                ),
            }

            self.manifest["articles"][url] = record
            return record

    def _build_markdown(self, article: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append(f"# {article.get('title', '无标题')}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"- URL: {article.get('url', '')}")
        lines.append(f"- 作者: {article.get('author') or '未知'}")
        lines.append(f"- 发布时间: {article.get('publish_time') or '未知'}")
        lines.append(f"- 分类: {article.get('category_name') or article.get('category_slug') or '未知'}")
        lines.append(f"- 爬取时间: {article.get('crawled_at', '')}")

        tags = article.get("tags") or []
        if tags:
            lines.append(f"- 标签: {' '.join(f'`{t}`' for t in tags)}")

        lines.append("")
        lines.append("---")
        lines.append("")

        summary = (article.get("summary") or "").strip()
        if summary:
            lines.append("## 摘要")
            lines.append("")
            lines.append(summary)
            lines.append("")

        lines.append("## 正文")
        lines.append("")
        lines.append((article.get("content") or "").strip())
        lines.append("")
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _build_excerpt(content: str, max_len: int = 600) -> str:
        text = re.sub(r"\s+", " ", (content or "")).strip()
        return text[:max_len]

    @staticmethod
    def _tags_to_text(tags: Any) -> str:
        if isinstance(tags, str):
            return tags
        if isinstance(tags, (list, tuple, set)):
            return "|".join(str(x) for x in tags if str(x).strip())
        return ""

    def _flush_sqlite_index(self, records: List[Dict[str, Any]]) -> None:
        self.index_sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.index_sqlite_path)
        try:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=NORMAL;
                PRAGMA temp_store=MEMORY;
                DROP TABLE IF EXISTS articles;
                DROP TABLE IF EXISTS articles_fts;
                CREATE TABLE articles (
                    url TEXT PRIMARY KEY,
                    article_id INTEGER,
                    title TEXT,
                    summary TEXT,
                    excerpt TEXT,
                    tags TEXT,
                    author TEXT,
                    publish_time TEXT,
                    category_slug TEXT,
                    category_name TEXT,
                    path TEXT,
                    crawled_at TEXT
                );
                CREATE VIRTUAL TABLE articles_fts USING fts5(
                    url UNINDEXED,
                    title,
                    summary,
                    excerpt,
                    tags,
                    author,
                    category_slug,
                    category_name,
                    tokenize='unicode61'
                );
                """
            )

            payload = []
            for row in records:
                payload.append(
                    (
                        row.get("url", ""),
                        row.get("article_id"),
                        row.get("title", ""),
                        row.get("summary", ""),
                        row.get("excerpt", ""),
                        self._tags_to_text(row.get("tags")),
                        row.get("author", ""),
                        row.get("publish_time", ""),
                        row.get("category_slug", ""),
                        row.get("category_name", ""),
                        row.get("path", ""),
                        row.get("crawled_at", ""),
                    )
                )

            conn.executemany(
                """
                INSERT OR REPLACE INTO articles (
                    url, article_id, title, summary, excerpt, tags, author, publish_time,
                    category_slug, category_name, path, crawled_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )
            conn.execute(
                """
                INSERT INTO articles_fts (
                    url, title, summary, excerpt, tags, author, category_slug, category_name
                )
                SELECT
                    url, title, summary, excerpt, tags, author, category_slug, category_name
                FROM articles
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_id ON articles(article_id DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category_slug)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_author ON articles(author)")
            conn.commit()
        finally:
            conn.close()

    def flush_indexes(self, stats: CrawlStats) -> None:
        with self.lock:
            self.manifest["updated_at"] = datetime.now().isoformat(timespec="seconds")
            temp = self.manifest_path.with_suffix(".tmp")
            write_json(temp, self.manifest)
            temp.replace(self.manifest_path)

            records = list(self.manifest["articles"].values())
            records.sort(key=lambda x: (x.get("article_id") or 0), reverse=True)

            with self.index_jsonl_path.open("wb") as fh:
                for row in records:
                    fh.write(orjson.dumps(row))
                    fh.write(b"\n")

            fieldnames = [
                "article_id",
                "title",
                "summary",
                "excerpt",
                "category_slug",
                "category_name",
                "author",
                "publish_time",
                "tags",
                "path",
                "url",
                "crawled_at",
            ]
            with self.index_csv_path.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                for row in records:
                    csv_row = dict(row)
                    csv_row["tags"] = self._tags_to_text(row.get("tags"))
                    writer.writerow({k: csv_row.get(k, "") for k in fieldnames})

            try:
                self._flush_sqlite_index(records)
            except Exception as exc:
                self.logger.warning("写入 SQLite 索引失败，已跳过: %s", exc)

            category_counter: Dict[str, int] = {}
            for row in records:
                slug = row.get("category_slug") or "uncategorized"
                category_counter[slug] = category_counter.get(slug, 0) + 1

            summary = {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "total_articles": len(records),
                "categories": category_counter,
                "index_files": {
                    "jsonl": str(self.index_jsonl_path),
                    "csv": str(self.index_csv_path),
                    "sqlite": str(self.index_sqlite_path),
                },
                "stats": stats.as_dict(),
            }
            write_json(self.summary_path, summary)


class ArticleParser:
    """FreeBuf 列表/详情解析 + HTML 转 Markdown。"""

    def __init__(self, base_url: str, logger: logging.Logger):
        self.base_url = base_url
        self.logger = logger

    def normalize_url(self, url: str) -> str:
        abs_url = urljoin(self.base_url, url)
        parsed = urlparse(abs_url)
        # 保留 path，去掉 query/fragment，保证去重稳定
        clean = parsed._replace(query="", fragment="")
        return urlunparse(clean)

    def extract_article_id(self, url: str) -> Optional[int]:
        m = ARTICLE_URL_RE.search(url)
        if not m:
            return None
        try:
            return int(m.group(1))
        except ValueError:
            return None

    def extract_category_slug_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 3 and parts[0] == "articles":
            return parts[1]
        return ""

    def parse_category_page(
        self,
        html: str,
        category_path: str,
        category_name: str,
    ) -> List[ArticleBrief]:
        results: List[ArticleBrief] = []
        seen: Set[str] = set()
        tree = FastHTMLParser(html)
        items = tree.css("div.article-item")

        for item in items:
            link = item.css_first(".title-left a[href*='/articles/']") or item.css_first(
                "a[href*='/articles/']"
            )
            href = (link.attributes.get("href") if link else "") or ""
            if not href:
                continue

            url = self.normalize_url(href)
            if url in seen:
                continue
            seen.add(url)

            title_node = item.css_first(".title-left .title")
            title = self._clean_text(
                title_node.text(strip=True) if title_node else (link.text(strip=True) if link else "")
            )

            summary_node = item.css_first(".item-top .text")
            summary = self._clean_text(summary_node.text(strip=True) if summary_node else "")

            author_node = item.css_first(".item-bottom a[href*='/author/']")
            author = self._clean_text(author_node.text(strip=True) if author_node else "")

            publish_time = ""
            for span in item.css(".item-bottom span"):
                text = self._clean_text(span.text(strip=True))
                m = DATE_RE.search(text)
                if m:
                    publish_time = m.group(0)

            results.append(
                ArticleBrief(
                    url=url,
                    article_id=self.extract_article_id(url),
                    title=title,
                    summary=summary,
                    author=author,
                    publish_time=publish_time,
                    category_slug=category_path,
                    category_name=category_name,
                    source="category_page",
                )
            )

        # 兜底：如果页面结构变化，至少通过 URL 正则拿到文章链接
        if not results:
            links = sorted(set(re.findall(r"/articles/[\w-]+/\d+\.html", html)))
            for href in links:
                url = self.normalize_url(href)
                if url in seen:
                    continue
                seen.add(url)
                results.append(
                    ArticleBrief(
                        url=url,
                        article_id=self.extract_article_id(url),
                        category_slug=category_path,
                        category_name=category_name,
                        source="category_regex_fallback",
                    )
                )

        return results

    def parse_detail_page(
        self,
        html: str,
        brief: ArticleBrief,
        image_to_md,
    ) -> Optional[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")

        title = self._extract_title(soup) or brief.title
        if not title:
            return None
        if INVALID_TITLE_RE.match(title):
            return None

        content_root = self._extract_content_root(soup)
        if not content_root:
            return None

        self._cleanup_content(content_root)

        content_markdown = self._to_markdown(content_root, image_to_md).strip()
        if len(content_markdown) < 30:
            fallback = self._extract_nuxt_post_content(html)
            if fallback:
                fallback_soup = BeautifulSoup(fallback, "html.parser")
                self._cleanup_content(fallback_soup)
                content_markdown = self._to_markdown(fallback_soup, image_to_md).strip()

        if len(content_markdown) < 30:
            return None

        publish_time = self._extract_publish_time(soup) or brief.publish_time
        author = self._extract_author(soup) or brief.author
        summary = self._extract_summary(soup) or brief.summary
        tags = self._extract_tags(soup)

        category_slug, category_name = self._extract_category_from_detail(soup)
        if not category_slug:
            category_slug = brief.category_slug or self.extract_category_slug_from_url(brief.url)
        if not category_name:
            category_name = brief.category_name or CATEGORY_LABELS.get(category_slug, "")

        crawled_at = datetime.now().isoformat(timespec="seconds")
        return {
            "url": brief.url,
            "article_id": brief.article_id or self.extract_article_id(brief.url),
            "title": title,
            "summary": summary,
            "author": author,
            "publish_time": publish_time,
            "category_slug": category_slug,
            "category_name": category_name,
            "tags": tags,
            "content": content_markdown,
            "source": brief.source,
            "crawled_at": crawled_at,
        }

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text or "").strip()
        return text

    def _extract_title(self, soup: BeautifulSoup) -> str:
        selectors = [
            ".artical-header .title-span",
            ".page-head-wrapper .title",
            "meta[property='og:title']",
            "meta[name='title']",
            "title",
        ]
        for sel in selectors:
            el = soup.select_one(sel)
            if not el:
                continue
            if el.name == "meta":
                text = self._clean_text(el.get("content", ""))
            else:
                text = self._clean_text(el.get_text(" ", strip=True))
            if not text:
                continue
            text = FREEBUF_TITLE_SUFFIX_RE.sub("", text).strip()
            if text:
                return text
        return ""

    def _extract_publish_time(self, soup: BeautifulSoup) -> str:
        selectors = [
            ".artical-header .date",
            ".author-info .date",
            ".date",
            "meta[property='article:published_time']",
        ]
        for sel in selectors:
            el = soup.select_one(sel)
            if not el:
                continue
            if el.name == "meta":
                text = self._clean_text(el.get("content", ""))
            else:
                text = self._clean_text(el.get_text(" ", strip=True))
            m = DATE_RE.search(text)
            if m:
                return m.group(0)
        return ""

    def _extract_author(self, soup: BeautifulSoup) -> str:
        selectors = [
            ".artical-header .author-info .author",
            ".author-info .author",
            ".author",
            ".name-info .name",
        ]
        for sel in selectors:
            el = soup.select_one(sel)
            if not el:
                continue
            text = self._clean_text(el.get_text(" ", strip=True))
            text = text.replace("所属地", "").strip()
            if text and len(text) <= 64 and "关注" not in text:
                return text
        return ""

    def _extract_summary(self, soup: BeautifulSoup) -> str:
        for sel in ["meta[name='description']", "meta[property='og:description']"]:
            el = soup.select_one(sel)
            if el:
                text = self._clean_text(el.get("content", ""))
                if text:
                    return text
        return ""

    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        tags: List[str] = []
        for el in soup.select(".tags-panel .txt, .tags a, .tag a"):
            text = self._clean_text(el.get_text(" ", strip=True)).lstrip("#").strip()
            if text and text not in tags:
                tags.append(text)
        return tags

    def _extract_category_from_detail(self, soup: BeautifulSoup) -> tuple[str, str]:
        link = soup.select_one(".tabs-panel .tab a[href*='/articles/']")
        if not link:
            return "", ""

        href = link.get("href", "")
        full = urljoin(self.base_url, href)
        parsed = urlparse(full)
        parts = [p for p in parsed.path.split("/") if p]

        slug = ""
        if len(parts) >= 2 and parts[0] == "articles":
            slug = parts[1]

        name = self._clean_text(link.get_text(" ", strip=True))
        return slug, name

    def _extract_content_root(self, soup: BeautifulSoup) -> Optional[Tag]:
        selectors = [
            ".content-detail",
            ".artical-body .payread-panel",
            ".artical-body",
            ".article-content",
            ".post-content",
            ".content-body",
        ]
        for sel in selectors:
            el = soup.select_one(sel)
            if not el:
                continue
            text_len = len(el.get_text(" ", strip=True))
            if text_len >= 120:
                return el
        return None

    def _cleanup_content(self, root: Tag) -> None:
        for node in root.select(
            "script, style, nav, footer, header, aside, .other-panel, .disclaimer-box, .recommend, .share, .related"
        ):
            node.decompose()

        # FreeBuf 页面里常见的空交互节点
        for node in root.select("button, input, textarea, select"):
            node.decompose()

    def _extract_nuxt_post_content(self, html: str) -> str:
        """从 window.__NUXT__ 里兜底提取 post_content。"""
        m = re.search(r"post_content:'(.*?)',is_original", html, flags=re.S)
        if not m:
            return ""
        raw = m.group(1)
        raw = raw.replace("\\/", "/")
        try:
            # 让 \n \uXXXX 等转义恢复
            decoded = bytes(raw, "utf-8").decode("unicode_escape")
            return decoded
        except Exception:
            return raw

    def _to_markdown(self, root: Tag, image_to_md) -> str:
        lines: List[str] = []
        children = list(root.children) if isinstance(root, Tag) else []
        for child in children:
            self._render_block(child, lines, image_to_md=image_to_md, list_level=0)

        # 清理空行
        cleaned: List[str] = []
        prev_blank = False
        for line in lines:
            blank = not line.strip()
            if blank and prev_blank:
                continue
            cleaned.append(line.rstrip())
            prev_blank = blank
        return "\n".join(cleaned).strip() + "\n"

    def _render_block(self, node, lines: List[str], image_to_md, list_level: int) -> None:
        if isinstance(node, NavigableString):
            text = self._clean_text(str(node))
            if text:
                lines.append(text)
                lines.append("")
            return

        if not isinstance(node, Tag):
            return

        name = node.name.lower()

        if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(name[1])
            text = self._inline(node, image_to_md).strip()
            if text:
                lines.append(f"{'#' * min(level + 1, 6)} {text}")
                lines.append("")
            return

        if name == "p":
            text = self._inline(node, image_to_md).strip()
            if text:
                lines.append(text)
                lines.append("")
            return

        if name == "blockquote":
            text = self._inline(node, image_to_md).strip()
            if text:
                for row in text.splitlines():
                    if row.strip():
                        lines.append(f"> {row.strip()}")
                lines.append("")
            return

        if name in {"ul", "ol"}:
            ordered = name == "ol"
            self._render_list(node, lines, image_to_md, ordered=ordered, list_level=list_level)
            lines.append("")
            return

        if name == "pre":
            text = node.get_text("\n", strip=False).strip("\n")
            if text:
                lang = ""
                for cls in node.get("class", []):
                    if cls.startswith("language-"):
                        lang = cls.replace("language-", "", 1)
                        break
                lines.append(f"```{lang}".rstrip())
                lines.append(text)
                lines.append("```")
                lines.append("")
            return

        if name == "table":
            table_lines = self._render_table(node)
            if table_lines:
                lines.extend(table_lines)
                lines.append("")
            return

        if name == "img":
            src = node.get("src") or node.get("data-src") or ""
            if src:
                md = image_to_md(src, node.get("alt", "图片"))
                if md:
                    lines.append(md)
                    lines.append("")
            return

        # 容器节点递归
        for child in node.children:
            self._render_block(child, lines, image_to_md=image_to_md, list_level=list_level)

    def _render_list(self, node: Tag, lines: List[str], image_to_md, ordered: bool, list_level: int) -> None:
        lis = [li for li in node.find_all("li", recursive=False)]
        for idx, li in enumerate(lis, start=1):
            prefix = f"{idx}. " if ordered else "- "
            text = self._inline(li, image_to_md).strip()
            indent = "  " * list_level
            if text:
                lines.append(f"{indent}{prefix}{text}")

            # 嵌套列表
            for sub in li.find_all(["ul", "ol"], recursive=False):
                self._render_list(
                    sub,
                    lines,
                    image_to_md=image_to_md,
                    ordered=(sub.name == "ol"),
                    list_level=list_level + 1,
                )

    def _render_table(self, table: Tag) -> List[str]:
        rows = table.find_all("tr")
        if not rows:
            return []

        parsed_rows: List[List[str]] = []
        for row in rows:
            cells = row.find_all(["th", "td"])
            if not cells:
                continue
            parsed_rows.append([self._clean_text(cell.get_text(" ", strip=True)) for cell in cells])

        if not parsed_rows:
            return []

        width = max(len(r) for r in parsed_rows)
        normalized = [r + [""] * (width - len(r)) for r in parsed_rows]

        out: List[str] = []
        out.append("| " + " | ".join(normalized[0]) + " |")
        out.append("| " + " | ".join(["---"] * width) + " |")
        for row in normalized[1:]:
            out.append("| " + " | ".join(row) + " |")
        return out

    def _inline(self, node: Tag, image_to_md) -> str:
        parts: List[str] = []
        for child in node.children:
            if isinstance(child, NavigableString):
                parts.append(str(child))
                continue
            if not isinstance(child, Tag):
                continue

            name = child.name.lower()
            if name in {"strong", "b"}:
                text = self._clean_text(self._inline(child, image_to_md))
                if text:
                    parts.append(f"**{text}**")
            elif name in {"em", "i"}:
                text = self._clean_text(self._inline(child, image_to_md))
                if text:
                    parts.append(f"*{text}*")
            elif name == "code":
                text = self._clean_text(child.get_text(" ", strip=True))
                if text:
                    parts.append(f"`{text}`")
            elif name == "a":
                href = child.get("href", "").strip()
                text = self._clean_text(self._inline(child, image_to_md) or child.get_text(" ", strip=True))
                if text and href:
                    parts.append(f"[{text}]({href})")
                elif text:
                    parts.append(text)
            elif name == "img":
                src = child.get("src") or child.get("data-src") or ""
                if src:
                    parts.append(image_to_md(src, child.get("alt", "图片")))
            elif name == "br":
                parts.append("\n")
            else:
                parts.append(self._inline(child, image_to_md))

        return self._clean_text("".join(parts).replace("\xa0", " "))


class FreeBufCrawler:
    """兼容旧接口的重构版爬虫。"""

    def __init__(
        self,
        base_url: str = "https://www.freebuf.com/",
        delay: float = 2,
        max_pages: int = 50,
        categories: Optional[List[str]] = None,
        output_dir: str = "freebuf_data",
        workers: int = 6,
        max_articles_total: Optional[int] = None,
        resume: bool = True,
        download_images: bool = True,
        force: bool = False,
        scan_by_id: bool = False,
        id_start: Optional[int] = None,
        id_end: Optional[int] = None,
        config: Optional[CrawlConfig] = None,
    ):
        if config is None:
            config = CrawlConfig(
                base_url=base_url,
                categories=self._normalize_categories(categories) if categories else list(DEFAULT_CATEGORIES),
                output_dir=Path(output_dir),
                delay=max(float(delay), 0.0),
                max_pages_per_category=max(1, int(max_pages)),
                workers=max(1, int(workers)),
                max_articles_total=max_articles_total,
                resume=resume,
                download_images=download_images,
                force=force,
                scan_by_id=scan_by_id,
                id_start=id_start,
                id_end=id_end,
            )
        self.config = config

        self.logger = self._init_logger(self.config.output_dir)
        self.stats = CrawlStats()
        self.stats_lock = threading.Lock()

        self.http = HttpClient(self.config, self.logger)
        self.state = CrawlState(self.config.output_dir / "state.json", self.config.resume, self.logger)
        self.store = ArticleStore(self.config.output_dir, self.logger)
        self.parser = ArticleParser(self.config.base_url, self.logger)

        self._executor: Optional[ThreadPoolExecutor] = None
        self._image_cache: Dict[str, str] = {}
        self._image_lock = threading.Lock()

        # 旧字段兼容
        self.article_count = 0
        self.category_names = dict(CATEGORY_LABELS)
        self.crawled_urls = set(self.state.data.get("crawled_urls", []))

    @staticmethod
    def _normalize_categories(categories: Optional[Sequence[str]]) -> List[str]:
        if not categories:
            return list(DEFAULT_CATEGORIES)

        normalized: List[str] = []
        seen: Set[str] = set()
        for raw in categories:
            v = (raw or "").strip().strip("/")
            if not v:
                continue
            if v in CATEGORY_LABELS:
                key = v
            elif v == "ics-articles":
                key = v
            elif not v.startswith("articles/") and f"articles/{v}" in CATEGORY_LABELS:
                key = f"articles/{v}"
            else:
                key = v
            if key not in seen:
                seen.add(key)
                normalized.append(key)
        return normalized or list(DEFAULT_CATEGORIES)

    def _init_logger(self, output_dir: Path) -> logging.Logger:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "logs").mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("freebuf_crawler")
        logger.setLevel(logging.INFO)
        logger.propagate = False

        if logger.handlers:
            return logger

        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

        stream_h = logging.StreamHandler()
        stream_h.setFormatter(fmt)
        logger.addHandler(stream_h)

        file_h = logging.FileHandler(output_dir / "logs" / "freebuf_crawler.log", encoding="utf-8")
        file_h.setFormatter(fmt)
        logger.addHandler(file_h)

        return logger

    def _sleep(self) -> None:
        base = self.config.delay
        jitter = random.uniform(0.0, self.config.jitter) if self.config.jitter > 0 else 0.0
        total = base + jitter
        if total > 0:
            time.sleep(total)

    def _bump(self, field: str, value: int = 1) -> None:
        with self.stats_lock:
            setattr(self.stats, field, getattr(self.stats, field) + value)

    def _build_category_url(self, category: str, page: int) -> str:
        category = category.strip("/")
        if page <= 1:
            return urljoin(self.config.base_url, category)
        # FreeBuf SSR 对 ?page=N 大概率会回第一页，这里依然保留，方便未来站点改版直接生效。
        return urljoin(self.config.base_url, f"{category}?page={page}")

    def _extract_latest_id_hint(self) -> Optional[int]:
        max_id = None
        probe_categories = self.config.categories[: min(3, len(self.config.categories))]
        for category in probe_categories:
            url = self._build_category_url(category, 1)
            html = self.http.fetch_text(url)
            if not html:
                continue
            ids = [int(x) for x in re.findall(r"/articles(?:/[\w-]+)?/(\d+)\.html", html)]
            if ids:
                cand = max(ids)
                if max_id is None or cand > max_id:
                    max_id = cand
        return max_id

    def _resolve_id_range(self) -> Optional[tuple[int, int]]:
        if not self.config.scan_by_id:
            return None

        start = self.config.id_start
        end = self.config.id_end

        if start is None:
            start = self._extract_latest_id_hint()
            if start is None:
                self.logger.warning("无法自动识别 id_start，跳过 ID 扫描")
                return None

        if end is None:
            # 默认向下扫 3000 个 ID（可用命令行覆盖）
            end = max(1, start - 3000)

        if end > start:
            start, end = end, start

        return start, end

    def _process_briefs(self, briefs: Iterable[ArticleBrief]) -> None:
        if not self._executor:
            raise RuntimeError("executor 未初始化")

        todo: List[ArticleBrief] = []
        for brief in briefs:
            if self.config.max_articles_total and self.stats.saved >= self.config.max_articles_total:
                break

            if not brief.url:
                continue

            if not self.config.force:
                if self.state.is_crawled(brief.url) or self.store.has_url(brief.url):
                    self._bump("skipped")
                    continue

            todo.append(brief)

        if self.config.max_articles_total is not None:
            with self.stats_lock:
                remaining = self.config.max_articles_total - self.stats.saved
            if remaining <= 0:
                return
            todo = todo[:remaining]

        if not todo:
            return

        self._bump("discovered", len(todo))
        futures = {self._executor.submit(self._fetch_and_save_article, brief): brief for brief in todo}
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            transient=True,
            disable=len(todo) < 8,
        ) as progress:
            task = progress.add_task("详情抓取中", total=len(todo))
            for future in as_completed(futures):
                brief = futures[future]
                try:
                    result = future.result()
                    if result == "saved":
                        self._bump("saved")
                    elif result == "skipped":
                        self._bump("skipped")
                    else:
                        self._bump("failed")
                except Exception as exc:
                    self.logger.warning("处理文章失败: %s, error=%s", brief.url, exc)
                    self.state.mark_failed(brief.url, str(exc))
                    self._bump("failed")
                finally:
                    self._bump("processed")
                    progress.advance(task)

    def _fetch_and_save_article(self, brief: ArticleBrief) -> str:
        html = self.http.fetch_text(brief.url)
        if not html:
            self.state.mark_failed(brief.url, "fetch_detail_failed")
            return "failed"

        article = self.parser.parse_detail_page(html, brief, self._image_markdown)
        if not article:
            self.state.mark_failed(brief.url, "parse_detail_failed")
            return "failed"

        image_count = article.get("content", "").count("../images/")
        article["image_count"] = image_count

        saved = self.store.save_article(article, force=self.config.force)
        if not saved:
            self.state.mark_failed(brief.url, "save_failed")
            return "failed"

        self.state.mark_crawled(brief.url)
        self.article_count = self.stats.saved + 1
        self._sleep()
        return "saved"

    def _image_markdown(self, src: str, alt: str) -> str:
        alt = (alt or "图片").strip() or "图片"
        if not src:
            return f"![{alt}]()"

        if not self.config.download_images:
            full = urljoin(self.config.base_url, src)
            return f"![{alt}]({full})"

        filename = self._download_image(src)
        if not filename:
            full = urljoin(self.config.base_url, src)
            return f"![{alt}]({full})"

        return f"![{alt}](../images/{filename})"

    @staticmethod
    def _normalize_image_url(url: str, base_url: str) -> str:
        full = urljoin(base_url, url)
        parsed = urlparse(full)

        # FreeBuf 图片常见后缀: xxx.webp!small
        path = parsed.path.split("!", 1)[0]

        # 去掉追踪参数
        keep_params: List[str] = []
        for chunk in parsed.query.split("&"):
            if not chunk:
                continue
            lower = chunk.lower()
            if lower.startswith("utm_") or lower.startswith("from=") or lower.startswith("ref="):
                continue
            keep_params.append(chunk)

        clean = parsed._replace(path=path, query="&".join(keep_params), fragment="")
        return urlunparse(clean)

    @staticmethod
    def _guess_image_ext(url: str, content_type: str) -> str:
        path = urlparse(url).path.lower()
        for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".tiff", ".avif"]:
            if path.endswith(ext):
                return ".jpg" if ext == ".jpeg" else ext

        ct = (content_type or "").lower()
        mapping = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/svg+xml": ".svg",
            "image/bmp": ".bmp",
            "image/tiff": ".tiff",
            "image/avif": ".avif",
        }
        return mapping.get(ct.split(";", 1)[0].strip(), ".jpg")

    def _download_image(self, src: str) -> Optional[str]:
        url = self._normalize_image_url(src, self.config.base_url)
        with self._image_lock:
            if url in self._image_cache:
                return self._image_cache[url]

        blob = self.http.fetch_binary(url)
        if not blob:
            return None

        data, content_type = blob
        if not data:
            return None
        if content_type and not content_type.lower().startswith("image/"):
            return None

        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        ext = self._guess_image_ext(url, content_type)
        filename = f"{url_hash}{ext}"
        path = self.store.images_dir / filename

        if not path.exists():
            try:
                path.write_bytes(data)
                self._bump("images_downloaded")
            except Exception:
                return None

        with self._image_lock:
            self._image_cache[url] = filename
        return filename

    def _crawl_categories(self) -> None:
        for category in self.config.categories:
            if self.config.max_articles_total and self.stats.saved >= self.config.max_articles_total:
                break

            cat_path = category.strip("/")
            cat_name = CATEGORY_LABELS.get(cat_path, cat_path)

            start_page = self.state.next_page(cat_path) if self.config.resume else 1
            self.logger.info("开始分类抓取: %s (%s), from page=%d", cat_name, cat_path, start_page)

            previous_urls: Set[str] = set()
            page = start_page
            while page <= self.config.max_pages_per_category:
                if self.config.max_articles_total and self.stats.saved >= self.config.max_articles_total:
                    break

                list_url = self._build_category_url(cat_path, page)
                html = self.http.fetch_text(list_url)
                if not html:
                    self.logger.warning("列表页获取失败，停止分类: %s page=%d", cat_path, page)
                    break

                briefs = self.parser.parse_category_page(html, cat_path, cat_name)
                if not briefs:
                    self.logger.info("分类无更多文章，停止: %s page=%d", cat_path, page)
                    break

                current_urls = {b.url for b in briefs}
                if page > start_page and current_urls and current_urls == previous_urls:
                    self.logger.info("检测到重复分页结果，停止分类: %s page=%d", cat_path, page)
                    break
                previous_urls = current_urls

                self.logger.info(
                    "分类 %s page=%d 发现 %d 篇（待去重）",
                    cat_name,
                    page,
                    len(briefs),
                )
                self._process_briefs(briefs)

                page += 1
                self.state.set_next_page(cat_path, page)
                self.state.save()
                self._sleep()

            self._bump("categories_finished")

    def _crawl_by_id_range(self) -> None:
        id_range = self._resolve_id_range()
        if not id_range:
            return

        start, end = id_range
        self.logger.info("开始 ID 扫描: %d -> %d", start, end)

        batch_size = max(20, self.config.id_batch_size)
        current = start

        while current >= end:
            if self.config.max_articles_total and self.stats.saved >= self.config.max_articles_total:
                break

            batch_ids = list(range(current, max(end - 1, current - batch_size), -1))
            briefs: List[ArticleBrief] = []
            for aid in batch_ids:
                url = urljoin(self.config.base_url, f"articles/{aid}.html")
                briefs.append(
                    ArticleBrief(
                        url=url,
                        article_id=aid,
                        source="id_scan",
                    )
                )

            self._bump("id_scan_requests", len(briefs))
            self._process_briefs(briefs)

            current = batch_ids[-1] - 1
            self.state.set_last_scanned_id(current)
            self.state.save()
            self._sleep()

    def crawl(self) -> None:
        self.logger.info("启动 FreeBuf 爬虫（重构版）")
        self.logger.info(
            "配置: workers=%d, max_pages_per_category=%d, max_articles_total=%s, output=%s",
            self.config.workers,
            self.config.max_pages_per_category,
            self.config.max_articles_total,
            self.config.output_dir,
        )

        try:
            with ThreadPoolExecutor(max_workers=self.config.workers) as executor:
                self._executor = executor
                self._crawl_categories()
                self._crawl_by_id_range()
        finally:
            self.http.close()

        self.stats.end_time = datetime.now().isoformat(timespec="seconds")
        self.store.flush_indexes(self.stats)
        self.state.save()

        self.article_count = self.stats.saved
        self.crawled_urls = set(self.state.data.get("crawled_urls", []))

        self.logger.info("爬取结束: saved=%d, failed=%d", self.stats.saved, self.stats.failed)

    def get_statistics(self) -> Dict[str, Any]:
        return self.stats.as_dict()

    def print_summary(self) -> None:
        s = self.get_statistics()
        print("\n" + "=" * 60)
        print("FreeBuf Crawler Summary")
        print("=" * 60)
        print(f"开始时间: {s['start_time']}")
        print(f"结束时间: {s['end_time']}")
        print(f"运行秒数: {s['elapsed_seconds']}")
        print(f"发现任务: {s['discovered']}")
        print(f"已处理: {s['processed']}")
        print(f"成功保存: {s['saved']}")
        print(f"跳过去重: {s['skipped']}")
        print(f"失败数量: {s['failed']}")
        print(f"下载图片: {s['images_downloaded']}")
        print(f"分类完成: {s['categories_finished']}")
        print(f"ID扫描请求: {s['id_scan_requests']}")
        print(f"吞吐(篇/分钟): {s['articles_per_minute']}")
        print("=" * 60)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FreeBuf 文章爬虫（并发+断点+离线索引）")

    parser.add_argument("--base-url", default="https://www.freebuf.com/", help="基础 URL")
    parser.add_argument("--output-dir", default="freebuf_data", help="输出目录")

    parser.add_argument(
        "--categories",
        nargs="*",
        default=None,
        help="分类列表，例如: web ai-security network 或 articles/web",
    )
    parser.add_argument("--print-categories", action="store_true", help="打印内置分类并退出")

    parser.add_argument("--delay", type=float, default=1.0, help="请求基础延迟（秒）")
    parser.add_argument("--jitter", type=float, default=0.5, help="随机抖动（秒）")
    parser.add_argument("--timeout", type=int, default=20, help="请求超时（秒）")
    parser.add_argument("--retries", type=int, default=3, help="请求重试次数")
    parser.add_argument("--workers", type=int, default=6, help="并发线程数")

    parser.add_argument("--max-pages", type=int, default=50, help="每个分类最多抓取页数")
    parser.add_argument("--max-total", type=int, default=None, help="总文章抓取上限")

    parser.add_argument("--no-images", action="store_true", help="不下载图片")
    parser.add_argument("--no-resume", action="store_true", help="关闭断点续爬")
    parser.add_argument("--force", action="store_true", help="强制重抓已存在 URL")
    parser.add_argument("--insecure", action="store_true", help="默认 verify=False")

    parser.add_argument("--scan-by-id", action="store_true", help="开启 ID 扫描模式")
    parser.add_argument("--id-start", type=int, default=None, help="ID 扫描起始值")
    parser.add_argument("--id-end", type=int, default=None, help="ID 扫描结束值")
    parser.add_argument("--id-batch-size", type=int, default=200, help="ID 扫描批大小")

    return parser


def _print_categories() -> None:
    print("可用分类：")
    for key in DEFAULT_CATEGORIES:
        print(f"- {key:25s}  {CATEGORY_LABELS.get(key, key)}")


def _build_config_from_args(args: argparse.Namespace) -> CrawlConfig:
    categories = FreeBufCrawler._normalize_categories(args.categories)
    return CrawlConfig(
        base_url=args.base_url,
        output_dir=Path(args.output_dir),
        categories=categories,
        delay=max(args.delay, 0.0),
        jitter=max(args.jitter, 0.0),
        timeout=max(args.timeout, 5),
        retries=max(args.retries, 0),
        workers=max(args.workers, 1),
        max_pages_per_category=max(args.max_pages, 1),
        max_articles_total=args.max_total,
        download_images=not args.no_images,
        resume=not args.no_resume,
        force=args.force,
        verify_ssl=not args.insecure,
        scan_by_id=args.scan_by_id,
        id_start=args.id_start,
        id_end=args.id_end,
        id_batch_size=max(args.id_batch_size, 20),
    )


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.print_categories:
        _print_categories()
        return 0

    config = _build_config_from_args(args)
    crawler = FreeBufCrawler(config=config)

    try:
        crawler.crawl()
        crawler.print_summary()
        return 0
    except KeyboardInterrupt:
        print("\n用户中断，正在保存状态...")
        crawler.state.save()
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
