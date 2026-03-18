# FreeBuf 网络安全文章爬虫（重构版）

面向离线比赛场景，重点做了：
- 现代技术栈：`httpx(http2)` + `requests` + `curl_cffi` + `tenacity` + `selectolax` + `pydantic` + `orjson` + `rich`
- 并发抓取（详情页多线程）
- 断点续爬（`state.json`）
- 增量去重（`manifest.json`）
- 图片本地化（`freebuf_data/images`）
- 离线检索索引（`index.sqlite` / `index.jsonl` / `index.csv` / `summary.json`）
- 可选 ID 扫描模式（用于补历史文章）

## 1. 安装依赖

```bash
pip install -r requirements.txt
```

## 2. 快速开始

### 2.1 直接跑（推荐）

```bash
python3 freebuf_crawler.py
```

默认行为：
- 抓取全部内置分类
- 每分类最多尝试 50 页（站点分页失效时会自动停）
- 开启断点续爬
- 下载图片并本地化

### 2.2 使用模板脚本

```bash
python3 maxcrawler.py
```

`maxcrawler.py` 里已经给了常用参数，改起来更快。

## 3. 常用命令

### 3.1 只抓几个分类

```bash
python3 freebuf_crawler.py --categories web ai-security network --max-pages 20
```

### 3.2 限制总文章数（赛前快速预热）

```bash
python3 freebuf_crawler.py --max-total 300 --workers 8
```

### 3.3 关闭图片下载（加速）

```bash
python3 freebuf_crawler.py --no-images
```

### 3.4 不使用断点（全新跑）

```bash
python3 freebuf_crawler.py --no-resume
```

### 3.5 强制重抓已存在文章

```bash
python3 freebuf_crawler.py --force
```

### 3.6 ID 扫描补历史（耗时模式）

```bash
python3 freebuf_crawler.py --scan-by-id --id-start 473900 --id-end 450000 --workers 10
```

说明：
- `--scan-by-id` 会访问 `https://www.freebuf.com/articles/<id>.html`
- 适合站点前端分页失效时补历史内容
- 建议配合断点续爬长时间运行

## 4. 输出结构

```text
freebuf_data/
├── ai-security/...
├── web/...
├── network/...
├── images/
├── logs/
│   └── freebuf_crawler.log
├── state.json
├── manifest.json
├── index.sqlite
├── index.jsonl
├── index.csv
└── summary.json
```

索引文件用途：
- `manifest.json`：URL -> 本地文件映射（去重核心）
- `index.sqlite`：FTS5 全文检索（默认检索后端，速度最快）
- `index.jsonl`：离线检索最方便
- `index.csv`：Excel / 表格工具快速查看
- `summary.json`：统计摘要

## 5. 离线检索

```bash
python3 search_index.py --keyword xss
python3 search_index.py --keyword 漏洞 --category web --limit 20
python3 search_index.py --keyword "sql 注入" --backend sqlite
```

## 6. 分类列表

```bash
python3 freebuf_crawler.py --print-categories
```

内置分类（slug）：
- `articles/container`
- `articles/ai-security`
- `articles/development`
- `articles/endpoint`
- `articles/database`
- `articles/web`
- `articles/network`
- `articles/es`
- `ics-articles`
- `articles/mobile`
- `articles/system`
- `articles/others-articles`

## 7. 参数总览

```bash
python3 freebuf_crawler.py --help
```

重点参数：
- `--categories`
- `--max-pages`
- `--max-total`
- `--workers`
- `--scan-by-id`
- `--id-start --id-end`
- `--no-resume`
- `--force`

## 8. 说明

- FreeBuf 当前前端是 Nuxt，分页经常走前端逻辑，纯拼 URL 翻页并不稳定。
- 本项目默认采用“分类抓最新 + 增量去重 + 可选 ID 扫描补历史”的组合策略。
- 传输层采用三级回退：`httpx(http2)` -> `requests` -> `curl_cffi`，用于提高复杂网络环境可用性。
- 建议赛前多跑几次增量任务，数据集会持续变厚。
