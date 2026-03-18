#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键启动模板：按你的需求改参数即可。

用法：
    python3 maxcrawler.py
"""

from freebuf_crawler import FreeBufCrawler


def main() -> None:
    crawler = FreeBufCrawler(
        delay=1.2,
        max_pages=50,              # 每个分类尝试抓取的页数上限
        categories=None,           # None=默认全部分类
        workers=8,
        max_articles_total=None,   # None=不限制
        resume=True,
        download_images=True,
        force=False,
        # 如果你想扫历史，可打开下面两行（会比较耗时）
        # scan_by_id=True,
        # id_end=450000,
    )

    crawler.crawl()
    crawler.print_summary()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[WARN] 用户中断")
    except Exception as exc:
        print(f"[ERROR] 运行失败: {exc}")
