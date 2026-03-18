#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GTFOBins 网站爬虫

优先使用 GTFOBins 官方 JSON API 抓取所有词条，速度快且结构完整。
当 API 不可用时，会自动回退到 HTML 页面解析模式。
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup, FeatureNotFound, Tag


DEFAULT_BASE_URL = "https://gtfobins.org/"
DEFAULT_API_PATH = "api.json"
DEFAULT_JSON_FILE = "gtfobins_data.json"
DEFAULT_CSV_FILE = "gtfobins_data.csv"
DEFAULT_TIMEOUT = 20.0
DEFAULT_RETRIES = 4
DEFAULT_WORKERS = 4
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def configure_logging(level: str = "INFO") -> logging.Logger:
    """配置日志记录器。"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger("gtfobins_scraper")


def dedupe(items: Iterable[str]) -> List[str]:
    """按原始顺序去重。"""
    seen = set()
    result: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def clean_text(value: Optional[str]) -> str:
    """清理文本首尾空白，保留内部换行。"""
    if not value:
        return ""
    return value.strip()


def collapse_text(value: Optional[str]) -> str:
    """将文本压成单行，适合写入 CSV。"""
    if not value:
        return ""
    return " ".join(value.split())


def slug_to_title(slug: str) -> str:
    """将 slug 转为可读标题。"""
    if not slug:
        return ""
    return slug.replace("-", " ").title()


class GTFOBinsScraper:
    """GTFOBins 爬虫。"""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        workers: int = DEFAULT_WORKERS,
        request_delay: float = 0.0,
        logger: Optional[logging.Logger] = None,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.api_url = urljoin(self.base_url, DEFAULT_API_PATH)
        self.timeout = max(1.0, timeout)
        self.retries = max(1, retries)
        self.workers = max(1, workers)
        self.request_delay = max(0.0, request_delay)
        self.logger = logger or configure_logging()
        self.html_parser = self._select_html_parser()

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "close",
            }
        )

        self.binaries: List[str] = []
        self.scraped_data: List[Dict[str, Any]] = []
        self.source_used = "unknown"
        self.stats: Dict[str, Any] = {
            "request_attempts": 0,
            "requests_transport_success": 0,
            "curl_transport_success": 0,
            "start_time": None,
            "end_time": None,
        }

    def _select_html_parser(self) -> str:
        """优先使用 lxml，不可用时回退到 html.parser。"""
        for parser_name in ("lxml", "html.parser"):
            try:
                BeautifulSoup("<html></html>", parser_name)
                if parser_name != "lxml":
                    self.logger.warning("未检测到 lxml，已回退到 html.parser")
                return parser_name
            except FeatureNotFound:
                continue

        raise RuntimeError("当前环境没有可用的 HTML 解析器")

    def _build_binary_url(self, binary_name: str) -> str:
        return urljoin(self.base_url, f"gtfobins/{quote(binary_name, safe='')}/")

    def _sleep_if_needed(self) -> None:
        if self.request_delay > 0:
            time.sleep(self.request_delay)

    def _fetch_with_requests(self, url: str) -> str:
        last_error: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            self.stats["request_attempts"] += 1
            try:
                self._sleep_if_needed()
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                self.stats["requests_transport_success"] += 1
                return response.text
            except requests.RequestException as exc:
                last_error = exc
                if attempt == self.retries:
                    break

                backoff = min(0.5 * (2 ** (attempt - 1)), 4.0)
                self.logger.warning(
                    "requests 获取失败，准备重试 (%s/%s): %s - %s",
                    attempt,
                    self.retries,
                    url,
                    exc,
                )
                time.sleep(backoff)

        raise RuntimeError(f"requests 获取失败: {url} - {last_error}")

    def _fetch_with_curl(self, url: str) -> str:
        curl_path = shutil.which("curl")
        if not curl_path:
            raise RuntimeError("系统中未找到 curl，且 requests 回退也失败")

        last_error = ""
        for attempt in range(1, self.retries + 1):
            self.stats["request_attempts"] += 1
            try:
                self._sleep_if_needed()
                result = subprocess.run(
                    [
                        curl_path,
                        "--http1.1",
                        "-fsSL",
                        "--max-time",
                        str(int(self.timeout)),
                        "-A",
                        DEFAULT_USER_AGENT,
                        url,
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.stats["curl_transport_success"] += 1
                return result.stdout
            except subprocess.CalledProcessError as exc:
                last_error = exc.stderr.strip() or f"exit code {exc.returncode}"
                if attempt == self.retries:
                    break

                backoff = min(0.5 * (2 ** (attempt - 1)), 4.0)
                self.logger.warning(
                    "curl 获取失败，准备重试 (%s/%s): %s - %s",
                    attempt,
                    self.retries,
                    url,
                    last_error,
                )
                time.sleep(backoff)

        raise RuntimeError(f"curl 获取失败: {url} - {last_error}")

    def fetch_text(self, url: str) -> str:
        """获取文本内容，先试 requests，再回退 curl。"""
        try:
            return self._fetch_with_requests(url)
        except Exception as requests_error:
            self.logger.warning("requests 方式不可用，回退 curl: %s", requests_error)
            return self._fetch_with_curl(url)

    def get_page(self, url: str) -> BeautifulSoup:
        """获取 HTML 页面。"""
        html = self.fetch_text(url)
        return BeautifulSoup(html, self.html_parser)

    def fetch_api_payload(self) -> Dict[str, Any]:
        """获取官方 API 数据。"""
        payload = json.loads(self.fetch_text(self.api_url))
        if not isinstance(payload, dict) or "executables" not in payload:
            raise ValueError("GTFOBins API 数据格式不符合预期")
        return payload

    def _resolve_alias(
        self, binary_name: str, executables: Dict[str, Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], List[str]]:
        """解析 alias 链。"""
        chain: List[str] = []
        current_name = binary_name
        current_meta = executables.get(binary_name, {})
        visited = {binary_name}

        while current_meta.get("alias"):
            alias_target = current_meta["alias"]
            chain.append(alias_target)
            if alias_target in visited or alias_target not in executables:
                break
            visited.add(alias_target)
            current_name = alias_target
            current_meta = executables[current_name]

        return current_meta, chain

    def _extract_fenced_code(self, value: str) -> List[str]:
        """从 Markdown 文本中提取代码块。"""
        snippets: List[str] = []
        chunks = value.split("```")
        for index in range(1, len(chunks), 2):
            snippet = clean_text(chunks[index])
            if snippet:
                lines = snippet.splitlines()
                if len(lines) > 1 and lines[0].strip().isalnum():
                    # fenced code block 可能带语言标识，去掉第一行。
                    snippet = "\n".join(lines[1:]).strip()
                snippets.append(snippet)
        return dedupe(snippets)

    def _build_function_reference(
        self,
        function_slug: str,
        field_name: str,
        field_value: Any,
        function_catalog: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        extra_catalog = function_catalog.get("extra", {}).get(field_name)
        if not extra_catalog:
            return None

        reference: Dict[str, Any] = {"type": field_name}
        if isinstance(field_value, str):
            reference["slug"] = field_value

        if isinstance(extra_catalog, dict) and isinstance(field_value, str):
            meta = extra_catalog.get(field_value, {})
            if isinstance(meta, dict):
                if meta.get("comment"):
                    reference["comment"] = clean_text(meta["comment"])
                if meta.get("code"):
                    reference["code"] = clean_text(meta["code"])
            elif meta:
                reference["comment"] = clean_text(str(meta))
        elif isinstance(extra_catalog, str):
            if isinstance(field_value, list):
                formatted_value = ", ".join(map(str, field_value))
                reference["comment"] = clean_text(f"{extra_catalog} {formatted_value}")
            else:
                reference["comment"] = clean_text(extra_catalog)

        return reference if len(reference) > 1 else None

    def _context_note(
        self, context_slug: str, field_name: str, field_value: Any, contexts_catalog: Dict[str, Any]
    ) -> Optional[str]:
        context_meta = contexts_catalog.get(context_slug, {})
        extra_meta = context_meta.get("extra", {}).get(field_name)
        if not extra_meta:
            return None

        if isinstance(extra_meta, dict):
            lookup_key = str(field_value).lower()
            note = extra_meta.get(lookup_key)
            return clean_text(note) if note else None

        if isinstance(extra_meta, str):
            if isinstance(field_value, list):
                values = ", ".join(map(str, field_value))
                return clean_text(f"{extra_meta} {values}")
            return clean_text(extra_meta)

        return None

    def _normalize_contexts(
        self,
        base_code: str,
        entry: Dict[str, Any],
        contexts_catalog: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        contexts: List[Dict[str, Any]] = []
        raw_contexts = entry.get("contexts", {})

        for context_slug, context_value in raw_contexts.items():
            catalog = contexts_catalog.get(context_slug, {})
            context_code = base_code
            notes: List[str] = []
            extra: Dict[str, Any] = {}

            if isinstance(context_value, dict):
                if context_value.get("code"):
                    context_code = clean_text(context_value["code"])

                for key, value in context_value.items():
                    if key == "code":
                        continue
                    extra[key] = value
                    note = self._context_note(context_slug, key, value, contexts_catalog)
                    if note:
                        notes.append(note)

            elif context_value not in (None, ""):
                extra["value"] = context_value

            context_info: Dict[str, Any] = {
                "name": catalog.get("label", slug_to_title(context_slug)),
                "slug": context_slug,
                "description": clean_text(catalog.get("description")),
                "code": context_code,
            }
            if notes:
                context_info["notes"] = dedupe(notes)
            if extra:
                context_info["extra"] = extra
            contexts.append(context_info)

        return contexts

    def _normalize_api_example(
        self,
        function_slug: str,
        entry: Dict[str, Any],
        function_catalog: Dict[str, Any],
        contexts_catalog: Dict[str, Any],
    ) -> Dict[str, Any]:
        base_code = clean_text(entry.get("code"))
        example: Dict[str, Any] = {
            "code": base_code,
            "contexts": self._normalize_contexts(base_code, entry, contexts_catalog),
        }

        if entry.get("comment"):
            example["comment"] = clean_text(entry["comment"])

        if entry.get("version"):
            example["version"] = clean_text(str(entry["version"]))

        if entry.get("from"):
            example["source"] = clean_text(str(entry["from"]))

        flags: Dict[str, Any] = {}
        notes: List[str] = []
        for key in ("binary", "tty", "blind"):
            if key in entry:
                flags[key] = entry[key]
                reference = self._build_function_reference(function_slug, key, entry[key], function_catalog)
                if reference and reference.get("comment"):
                    notes.append(reference["comment"])

        if flags:
            example["flags"] = flags
        if notes:
            example["notes"] = dedupe(notes)

        references: List[Dict[str, Any]] = []
        for key in ("listener", "receiver", "sender", "connector"):
            if key in entry:
                reference = self._build_function_reference(function_slug, key, entry[key], function_catalog)
                if reference:
                    references.append(reference)
        if references:
            example["references"] = references

        return example

    def _binary_description(
        self,
        binary_name: str,
        binary_meta: Dict[str, Any],
        alias_chain: Sequence[str],
        function_entries: Sequence[Dict[str, Any]],
    ) -> str:
        parts: List[str] = []

        if alias_chain:
            parts.append(f"Alias of {alias_chain[0]}.")
        if binary_meta.get("comment"):
            parts.append(clean_text(binary_meta["comment"]))
        elif function_entries:
            first_description = clean_text(function_entries[0].get("description"))
            if first_description:
                parts.append(first_description)

        description = " ".join(part for part in parts if part).strip()
        if description:
            return description

        if binary_name:
            return f"GTFOBins entry for {binary_name}."
        return ""

    def parse_executable_from_api(
        self,
        binary_name: str,
        binary_meta: Dict[str, Any],
        functions_catalog: Dict[str, Any],
        contexts_catalog: Dict[str, Any],
        executables: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """将 API 中的单个 executable 规范化为输出结构。"""
        resolved_meta, alias_chain = self._resolve_alias(binary_name, executables)
        effective_meta = binary_meta if binary_meta.get("functions") else resolved_meta

        functions: List[Dict[str, Any]] = []
        all_examples: List[str] = []

        for function_slug, entries in effective_meta.get("functions", {}).items():
            function_catalog = functions_catalog.get(function_slug, {})
            normalized_examples = [
                self._normalize_api_example(function_slug, entry, function_catalog, contexts_catalog)
                for entry in entries
            ]

            code_examples = dedupe(
                code
                for example in normalized_examples
                for code in [example.get("code"), *[ctx.get("code") for ctx in example.get("contexts", [])]]
                if code
            )

            reference_codes = dedupe(
                reference.get("code", "")
                for example in normalized_examples
                for reference in example.get("references", [])
                if reference.get("code")
            )
            extra_codes = []
            for extra_value in function_catalog.get("extra", {}).values():
                if isinstance(extra_value, str):
                    extra_codes.extend(self._extract_fenced_code(extra_value))

            functions.append(
                {
                    "name": function_catalog.get("label", slug_to_title(function_slug)),
                    "slug": function_slug,
                    "description": clean_text(function_catalog.get("description")),
                    "contexts": dedupe(
                        ctx.get("name", "")
                        for example in normalized_examples
                        for ctx in example.get("contexts", [])
                    ),
                    "code_examples": dedupe([*code_examples, *extra_codes]),
                    "examples": normalized_examples,
                    "mitre": function_catalog.get("mitre", []),
                    "extra": function_catalog.get("extra", {}),
                }
            )

            all_examples.extend(code_examples)
            all_examples.extend(reference_codes)
            all_examples.extend(extra_codes)

        binary_info: Dict[str, Any] = {
            "name": binary_name,
            "url": self._build_binary_url(binary_name),
            "description": self._binary_description(binary_name, binary_meta, alias_chain, functions),
            "functions": functions,
            "examples": dedupe(all_examples),
        }

        if binary_meta.get("comment"):
            binary_info["comment"] = clean_text(binary_meta["comment"])
        if binary_meta.get("alias"):
            binary_info["alias"] = clean_text(binary_meta["alias"])
        if alias_chain:
            binary_info["alias_chain"] = alias_chain

        return binary_info

    def scrape_all_from_api(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """通过官方 API 抓取全部数据。"""
        executables = payload.get("executables", {})
        functions_catalog = payload.get("functions", {})
        contexts_catalog = payload.get("contexts", {})

        binaries = sorted(executables.keys(), key=str.casefold)
        self.logger.info("通过 API 获取到 %s 个 executable", len(binaries))

        self.binaries = binaries
        data = [
            self.parse_executable_from_api(
                binary_name,
                executables[binary_name],
                functions_catalog,
                contexts_catalog,
                executables,
            )
            for binary_name in binaries
        ]
        self.source_used = "api"
        self.scraped_data = data
        return data

    def parse_binary_list_page(self, soup: BeautifulSoup) -> List[str]:
        """从首页 HTML 中提取 binary 列表。"""
        binaries: List[str] = []
        for link in soup.select("#gtfobin-table a.bin-name, a.bin-name"):
            href = link.get("href", "")
            if not href.startswith("/gtfobins/") or "#" in href:
                continue
            binary_name = href.removeprefix("/gtfobins/").strip("/")
            if binary_name:
                binaries.append(binary_name)
        return dedupe(binaries)

    def _parse_html_fieldset(self, fieldset: Tag) -> Dict[str, Any]:
        legend = clean_text(fieldset.find("legend").get_text(" ", strip=True) if fieldset.find("legend") else "")
        paragraphs = [
            clean_text(paragraph.get_text(" ", strip=True))
            for paragraph in fieldset.find_all("p", recursive=False)
        ]
        codes = [clean_text(pre.get_text("\n", strip=True)) for pre in fieldset.find_all("pre", recursive=False)]

        item: Dict[str, Any] = {}
        if legend:
            item["label"] = legend
        if paragraphs:
            item["comment"] = "\n".join(paragraphs)
        if codes:
            item["code"] = codes[0]
            if len(codes) > 1:
                item["codes"] = codes
        return item

    def _parse_html_contexts(self, contexts_block: Tag) -> List[Dict[str, Any]]:
        contexts: List[Dict[str, Any]] = []
        for label in contexts_block.find_all("label", recursive=False):
            details = label.find_next_sibling()
            while details and (not isinstance(details, Tag) or details.name != "div"):
                details = details.find_next_sibling()
            if not isinstance(details, Tag):
                continue

            description = ""
            description_tag = details.find("p", recursive=False)
            if description_tag:
                description = clean_text(description_tag.get_text(" ", strip=True))

            codes = [clean_text(pre.get_text("\n", strip=True)) for pre in details.find_all("pre")]
            notes = [
                self._parse_html_fieldset(fieldset)
                for fieldset in details.find_all("fieldset", recursive=False)
            ]
            notes = [note for note in notes if note]

            context: Dict[str, Any] = {
                "name": clean_text(label.get_text(" ", strip=True)),
                "slug": clean_text(label.get_text(" ", strip=True)).lower().replace(" ", "-"),
                "description": description,
            }
            if codes:
                context["code"] = codes[0]
                if len(codes) > 1:
                    context["codes"] = codes
            if notes:
                context["notes"] = notes
            contexts.append(context)

        return contexts

    def _parse_html_example(self, item: Tag) -> Dict[str, Any]:
        example: Dict[str, Any] = {"contexts": []}
        references: List[Dict[str, Any]] = []

        for child in item.find_all(recursive=False):
            if child.name == "div" and "contexts" in child.get("class", []):
                example["contexts"] = self._parse_html_contexts(child)
            elif child.name == "fieldset":
                fieldset_data = self._parse_html_fieldset(child)
                label = fieldset_data.get("label", "").lower()
                if label == "comment":
                    example["comment"] = fieldset_data.get("comment", "")
                elif fieldset_data:
                    references.append(fieldset_data)

        if references:
            example["references"] = references

        base_codes = dedupe(
            ctx.get("code", "")
            for ctx in example.get("contexts", [])
            if ctx.get("code")
        )
        if base_codes:
            example["code"] = base_codes[0]

        return example

    def parse_binary_page(
        self, soup: BeautifulSoup, binary_name: str, url: str
    ) -> Dict[str, Any]:
        """解析单个 binary 的 HTML 页面。"""
        top_paragraphs: List[str] = []
        alias: Optional[str] = None

        heading = soup.find("h1")
        cursor = heading.find_next_sibling() if heading else soup.body.find() if soup.body else None
        while isinstance(cursor, Tag):
            if cursor.name == "ul" and "tag-list" in cursor.get("class", []):
                break
            if cursor.name == "p":
                text = clean_text(cursor.get_text(" ", strip=True))
                if text:
                    top_paragraphs.append(text)
                alias_link = cursor.find("a", href=lambda href: href and href.startswith("/gtfobins/"))
                if alias_link and "alias" in text.lower():
                    alias = clean_text(alias_link.get_text(" ", strip=True))
            cursor = cursor.find_next_sibling()

        functions: List[Dict[str, Any]] = []
        all_examples: List[str] = []

        for function_heading in soup.select("h2.function-name"):
            function_examples: List[Dict[str, Any]] = []
            function_description = ""

            node = function_heading.find_next_sibling()
            while isinstance(node, Tag):
                if node.name == "h2" and "function-name" in node.get("class", []):
                    break

                if node.name == "p" and not function_description:
                    function_description = clean_text(node.get_text(" ", strip=True))

                if node.name == "ul" and "examples" in node.get("class", []):
                    for item in node.find_all("li", recursive=False):
                        parsed_example = self._parse_html_example(item)
                        function_examples.append(parsed_example)
                node = node.find_next_sibling()

            code_examples = dedupe(
                code
                for example in function_examples
                for code in [example.get("code"), *[ctx.get("code") for ctx in example.get("contexts", [])]]
                if code
            )
            reference_codes = dedupe(
                reference.get("code", "")
                for example in function_examples
                for reference in example.get("references", [])
                if reference.get("code")
            )

            functions.append(
                {
                    "name": clean_text(function_heading.get_text(" ", strip=True)),
                    "slug": function_heading.get("id", ""),
                    "description": function_description,
                    "contexts": dedupe(
                        ctx.get("name", "")
                        for example in function_examples
                        for ctx in example.get("contexts", [])
                    ),
                    "code_examples": code_examples,
                    "examples": function_examples,
                }
            )
            all_examples.extend(code_examples)
            all_examples.extend(reference_codes)

        description = " ".join(top_paragraphs).strip()
        if alias:
            alias_description = f"Alias of {alias}."
            if description and "alias" not in description.lower():
                description = f"{alias_description} {description}".strip()
            else:
                description = alias_description
        if not description and functions:
            description = functions[0].get("description", "")

        binary_info: Dict[str, Any] = {
            "name": binary_name,
            "url": url,
            "description": description,
            "functions": functions,
            "examples": dedupe(all_examples),
        }
        if alias:
            binary_info["alias"] = alias

        return binary_info

    def get_binary_list(self) -> List[str]:
        """获取全部 binary 名称。"""
        self.logger.info("正在从首页提取 executable 列表")
        soup = self.get_page(self.base_url)
        binaries = self.parse_binary_list_page(soup)
        if not binaries:
            raise RuntimeError("未能从 GTFOBins 首页提取 executable 列表")
        self.logger.info("通过 HTML 获取到 %s 个 executable", len(binaries))
        return binaries

    def scrape_binary_info(self, binary_name: str) -> Optional[Dict[str, Any]]:
        """抓取单个 binary 的 HTML 页面。"""
        url = self._build_binary_url(binary_name)
        try:
            soup = self.get_page(url)
            return self.parse_binary_page(soup, binary_name, url)
        except Exception as exc:
            self.logger.error("爬取 %s 失败: %s", binary_name, exc)
            return None

    def scrape_all_from_html(self) -> List[Dict[str, Any]]:
        """回退到 HTML 页面抓取。"""
        self.binaries = self.get_binary_list()
        results: Dict[str, Dict[str, Any]] = {}

        self.logger.info(
            "开始 HTML 回退抓取，共 %s 个 executable，workers=%s",
            len(self.binaries),
            self.workers,
        )

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_map = {
                executor.submit(self.scrape_binary_info, binary_name): binary_name
                for binary_name in self.binaries
            }

            for index, future in enumerate(as_completed(future_map), 1):
                binary_name = future_map[future]
                data = future.result()
                if data:
                    results[binary_name] = data
                self.logger.info("HTML 进度: %s/%s - %s", index, len(self.binaries), binary_name)

        ordered = [results[name] for name in sorted(results.keys(), key=str.casefold)]
        self.source_used = "html"
        self.scraped_data = ordered
        return ordered

    def scrape_all(self, source: str = "auto") -> List[Dict[str, Any]]:
        """抓取全部数据。"""
        self.stats["start_time"] = time.time()

        try:
            if source in {"auto", "api"}:
                try:
                    payload = self.fetch_api_payload()
                    return self.scrape_all_from_api(payload)
                except Exception as exc:
                    if source == "api":
                        raise
                    self.logger.warning("API 模式失败，回退 HTML: %s", exc)

            data = self.scrape_all_from_html()
            return data
        finally:
            self.stats["end_time"] = time.time()

    def save_to_json(self, filename: str = DEFAULT_JSON_FILE) -> str:
        """保存为 JSON。"""
        path = Path(filename)
        with path.open("w", encoding="utf-8") as file:
            json.dump(self.scraped_data, file, ensure_ascii=False, indent=2)
        self.logger.info("JSON 已保存到 %s", path)
        return str(path)

    def save_to_csv(self, filename: str = DEFAULT_CSV_FILE) -> str:
        """保存为 CSV。"""
        path = Path(filename)
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Binary Name", "URL", "Description", "Functions", "Examples"])

            for item in self.scraped_data:
                functions = "; ".join(func["name"] for func in item.get("functions", []))
                examples = "; ".join(item.get("examples", [])[:3])
                writer.writerow(
                    [
                        item.get("name", ""),
                        item.get("url", ""),
                        collapse_text(item.get("description", "")),
                        functions,
                        examples,
                    ]
                )

        self.logger.info("CSV 已保存到 %s", path)
        return str(path)

    def print_summary(self) -> None:
        """输出统计信息。"""
        total_functions = sum(len(item.get("functions", [])) for item in self.scraped_data)
        total_examples = sum(len(item.get("examples", [])) for item in self.scraped_data)
        duration = 0.0
        if self.stats["start_time"] and self.stats["end_time"]:
            duration = self.stats["end_time"] - self.stats["start_time"]

        print("\n抓取完成")
        print(f"- 数据来源: {self.source_used}")
        print(f"- executable 数量: {len(self.scraped_data)}")
        print(f"- 总功能数量: {total_functions}")
        print(f"- 总示例数量: {total_examples}")
        print(f"- 总请求次数: {self.stats['request_attempts']}")
        print(f"- requests 成功次数: {self.stats['requests_transport_success']}")
        print(f"- curl 回退成功次数: {self.stats['curl_transport_success']}")
        print(f"- 耗时: {duration:.2f}s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GTFOBins 爬虫")
    parser.add_argument(
        "--source",
        choices=("auto", "api", "html"),
        default="auto",
        help="抓取来源，默认 auto（优先 API，失败回退 HTML）",
    )
    parser.add_argument(
        "--json-file",
        default=DEFAULT_JSON_FILE,
        help=f"JSON 输出路径，默认 {DEFAULT_JSON_FILE}",
    )
    parser.add_argument(
        "--csv-file",
        default=DEFAULT_CSV_FILE,
        help=f"CSV 输出路径，默认 {DEFAULT_CSV_FILE}",
    )
    parser.add_argument("--skip-json", action="store_true", help="不生成 JSON 输出")
    parser.add_argument("--skip-csv", action="store_true", help="不生成 CSV 输出")
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"单次请求超时秒数，默认 {DEFAULT_TIMEOUT}",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"请求重试次数，默认 {DEFAULT_RETRIES}",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"HTML 回退模式的并发数，默认 {DEFAULT_WORKERS}",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="每次请求前的延迟秒数，主要用于 HTML 回退模式限速",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="日志级别",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logger = configure_logging(args.log_level)
    scraper = GTFOBinsScraper(
        timeout=args.timeout,
        retries=args.retries,
        workers=args.workers,
        request_delay=args.delay,
        logger=logger,
    )

    try:
        data = scraper.scrape_all(source=args.source)
    except KeyboardInterrupt:
        logger.warning("用户中断爬取")
        return 1
    except Exception as exc:
        logger.error("爬取过程中出现错误: %s", exc)
        return 1

    if not data:
        logger.warning("没有获取到任何数据")
        return 1

    if not args.skip_json:
        scraper.save_to_json(args.json_file)
    if not args.skip_csv:
        scraper.save_to_csv(args.csv_file)

    scraper.print_summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
