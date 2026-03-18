#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线检索 FreeBuf 抓取结果。

示例：
    python3 search_index.py --keyword xss
    python3 search_index.py --keyword 漏洞 --category web --limit 20
    python3 search_index.py --keyword "sql 注入" --backend sqlite
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

import orjson


def load_index_jsonl(index_path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not index_path.exists():
        return rows

    with index_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(orjson.loads(line))
            except orjson.JSONDecodeError:
                continue
    return rows


def normalize(s: str) -> str:
    return (s or "").strip().lower()


def parse_tags(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        chunks = re.split(r"[|,\s]+", value.strip())
        return [x for x in chunks if x]
    return [str(value).strip()]


def build_fts_query(keyword: str) -> str:
    chunks = re.findall(r"[\w\u4e00-\u9fff]+", keyword, flags=re.UNICODE)
    if not chunks:
        return keyword
    return " AND ".join(chunks)


def score_row_jsonl(row: Dict[str, Any], keyword: str) -> int:
    title = normalize(row.get("title", ""))
    summary = normalize(row.get("summary", ""))
    tags = " ".join(parse_tags(row.get("tags")))
    tags = normalize(tags)
    excerpt = normalize(row.get("excerpt", ""))

    score = 0
    if keyword in title:
        score += 8
    if keyword in tags:
        score += 5
    if keyword in summary:
        score += 3
    if keyword in excerpt:
        score += 2
    return score


def search_jsonl(
    rows: List[Dict[str, Any]],
    keyword: str,
    category: str,
    author: str,
    limit: int,
) -> List[Tuple[float, Dict[str, Any]]]:
    cat_filter = normalize(category)
    author_filter = normalize(author)

    matched: List[Tuple[float, Dict[str, Any]]] = []
    for row in rows:
        if cat_filter and normalize(row.get("category_slug", "")) != cat_filter:
            continue
        if author_filter and author_filter not in normalize(row.get("author", "")):
            continue

        s = score_row_jsonl(row, keyword)
        if s <= 0:
            continue

        row = dict(row)
        row["tags"] = parse_tags(row.get("tags"))
        matched.append((float(s), row))

    matched.sort(key=lambda x: (x[0], x[1].get("article_id") or 0), reverse=True)
    return matched[: max(1, limit)]


def search_sqlite(
    db_path: Path,
    keyword: str,
    category: str,
    author: str,
    limit: int,
) -> List[Tuple[float, Dict[str, Any]]]:
    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        sql = """
            SELECT
                a.article_id, a.title, a.summary, a.excerpt, a.category_slug, a.category_name,
                a.author, a.publish_time, a.tags, a.path, a.url, a.crawled_at,
                bm25(articles_fts) AS bm25_score
            FROM articles_fts
            JOIN articles a ON a.url = articles_fts.url
            WHERE articles_fts MATCH ?
        """
        params: List[Any] = [build_fts_query(keyword)]

        cat_filter = normalize(category)
        if cat_filter:
            sql += " AND lower(a.category_slug) = ?"
            params.append(cat_filter)

        author_filter = normalize(author)
        if author_filter:
            sql += " AND lower(a.author) LIKE ?"
            params.append(f"%{author_filter}%")

        sql += " ORDER BY bm25_score ASC, COALESCE(a.article_id, 0) DESC LIMIT ?"
        params.append(max(1, limit))

        rows = conn.execute(sql, params).fetchall()
        if not rows:
            like_sql = """
                SELECT
                    a.article_id, a.title, a.summary, a.excerpt, a.category_slug, a.category_name,
                    a.author, a.publish_time, a.tags, a.path, a.url, a.crawled_at,
                    999.0 AS bm25_score
                FROM articles a
                WHERE (
                    a.title LIKE ? OR a.summary LIKE ? OR a.excerpt LIKE ? OR a.tags LIKE ?
                )
            """
            like_kw = f"%{keyword}%"
            like_params: List[Any] = [like_kw, like_kw, like_kw, like_kw]

            if cat_filter:
                like_sql += " AND lower(a.category_slug) = ?"
                like_params.append(cat_filter)

            if author_filter:
                like_sql += " AND lower(a.author) LIKE ?"
                like_params.append(f"%{author_filter}%")

            like_sql += " ORDER BY COALESCE(a.article_id, 0) DESC LIMIT ?"
            like_params.append(max(1, limit))
            rows = conn.execute(like_sql, like_params).fetchall()

        out: List[Tuple[float, Dict[str, Any]]] = []
        for row in rows:
            data = dict(row)
            data["tags"] = parse_tags(data.get("tags"))
            score = float(data.pop("bm25_score", 0.0))
            out.append((score, data))
        return out
    finally:
        conn.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="检索 freebuf_data/index.sqlite / index.jsonl")
    parser.add_argument("--keyword", required=True, help="关键词")
    parser.add_argument("--backend", choices=["auto", "sqlite", "jsonl"], default="auto", help="检索后端")
    parser.add_argument("--db", default="freebuf_data/index.sqlite", help="index.sqlite 路径")
    parser.add_argument("--index", default="freebuf_data/index.jsonl", help="index.jsonl 路径")
    parser.add_argument("--category", default="", help="分类 slug 过滤，例如 web")
    parser.add_argument("--author", default="", help="作者过滤")
    parser.add_argument("--limit", type=int, default=15, help="最多返回条数")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    keyword = normalize(args.keyword)
    if not keyword:
        print("关键词不能为空")
        return 1

    backend = args.backend
    if backend == "auto":
        backend = "sqlite" if Path(args.db).exists() else "jsonl"

    matched: List[Tuple[float, Dict[str, Any]]] = []
    if backend == "sqlite":
        try:
            matched = search_sqlite(
                db_path=Path(args.db),
                keyword=keyword,
                category=args.category,
                author=args.author,
                limit=args.limit,
            )
        except sqlite3.Error as exc:
            if args.backend != "auto":
                print(f"SQLite 查询失败: {exc}")
                return 1
            backend = "jsonl"

    if backend == "jsonl":
        rows = load_index_jsonl(Path(args.index))
        if not rows:
            print(f"未找到索引或索引为空: {args.index}")
            return 1
        matched = search_jsonl(
            rows=rows,
            keyword=keyword,
            category=args.category,
            author=args.author,
            limit=args.limit,
        )

    if not matched:
        print("没有匹配结果")
        return 0

    print(f"后端: {backend}")
    print(f"命中 {len(matched)} 条结果:\n")

    for i, (score, row) in enumerate(matched, start=1):
        tags = " ".join(f"#{t}" for t in (row.get("tags") or [])[:6])
        score_text = f"{score:.3f}" if backend == "sqlite" else f"{int(score)}"

        print(f"{i}. [{score_text}] {row.get('title', '')}")
        print(
            f"   分类: {row.get('category_slug', '')}  "
            f"作者: {row.get('author', '')}  发布时间: {row.get('publish_time', '')}"
        )
        print(f"   文件: {row.get('path', '')}")
        if tags:
            print(f"   标签: {tags}")
        print(f"   URL: {row.get('url', '')}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
