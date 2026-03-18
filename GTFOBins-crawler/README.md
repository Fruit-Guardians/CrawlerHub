# GTFOBins 网站爬虫

这个项目用于抓取 [GTFOBins](https://gtfobins.org/) 的全部词条信息，并导出为 JSON 和 CSV。当前版本优先使用 GTFOBins 官方 `api.json`，当 API 不可用时会自动回退到 HTML 页面解析。

## 这次优化了什么

- 默认走官方 API，全量抓取速度从逐页串行请求优化为单请求拉取
- 自动回退 HTML 抓取，避免 API 短暂不可用时脚本直接失效
- 增加请求重试、指数退避，以及 `curl` 传输回退，提升 TLS 不稳定场景下的成功率
- HTML 回退模式支持并发抓取
- 保留原有 `name / url / description / functions / examples` 核心输出字段，同时补充 `alias`、`alias_chain`、上下文、MITRE、额外说明等结构化信息
- 新增 CLI 参数，支持选择数据源、并发数、超时、重试次数和输出路径
- 新增离线测试，覆盖 alias 解析、上下文覆盖和 HTML 回退解析

## 文件说明

- `gtfobins_scraper.py`：主爬虫脚本
- `test_gtfobins_scraper.py`：离线测试
- `requirements.txt`：依赖列表
- `gtfobins_data.json`：JSON 输出文件
- `gtfobins_data.csv`：CSV 输出文件

## 安装依赖

```bash
python3 -m pip install -r requirements.txt
```

`lxml` 会优先用于 HTML 解析；如果当前环境没有安装，脚本会自动回退到 Python 内置的 `html.parser`。

## 使用方法

默认运行：

```bash
python3 gtfobins_scraper.py
```

这会自动：

1. 优先请求 `https://gtfobins.org/api.json`
2. 失败时回退到 HTML 页面抓取
3. 输出 `gtfobins_data.json` 和 `gtfobins_data.csv`
4. 打印执行来源、词条数、功能数、示例数和请求统计

只跑 API，不写文件：

```bash
python3 gtfobins_scraper.py --source api --skip-json --skip-csv
```

强制 HTML 回退模式：

```bash
python3 gtfobins_scraper.py --source html --workers 6
```

自定义输出文件：

```bash
python3 gtfobins_scraper.py --json-file data/gtfobins.json --csv-file data/gtfobins.csv
```

## CLI 参数

- `--source {auto,api,html}`：抓取来源，默认 `auto`
- `--json-file PATH`：JSON 输出路径
- `--csv-file PATH`：CSV 输出路径
- `--skip-json`：跳过 JSON 输出
- `--skip-csv`：跳过 CSV 输出
- `--timeout FLOAT`：单次请求超时秒数
- `--retries INT`：请求重试次数
- `--workers INT`：HTML 回退模式并发数
- `--delay FLOAT`：每次请求前的延迟秒数
- `--log-level {DEBUG,INFO,WARNING,ERROR}`：日志级别

## 输出格式

### JSON

每个 binary 至少包含以下字段：

```json
{
  "name": "bash",
  "url": "https://gtfobins.org/gtfobins/bash/",
  "description": "This executable can spawn an interactive system shell.",
  "functions": [
    {
      "name": "Shell",
      "slug": "shell",
      "description": "This executable can spawn an interactive system shell.",
      "contexts": ["Unprivileged", "Sudo", "SUID"],
      "code_examples": ["bash", "bash -p"],
      "examples": [
        {
          "code": "bash",
          "contexts": [
            {
              "name": "Unprivileged",
              "slug": "unprivileged",
              "description": "This function can be performed by any unprivileged user.",
              "code": "bash"
            }
          ]
        }
      ]
    }
  ],
  "examples": ["bash", "bash -p"],
  "alias": "mawk"
}
```

说明：

- `alias` / `alias_chain` 只会在别名词条中出现
- `functions[].mitre` 和 `functions[].extra` 来自官方 API
- `functions[].examples[].references` 会保存 `listener`、`receiver`、`sender`、`connector` 等附加代码块

### CSV

CSV 继续保持轻量格式，包含以下列：

- `Binary Name`
- `URL`
- `Description`
- `Functions`
- `Examples`

## 性能说明

- `--source auto` 或 `--source api` 时，通常只需要 1 次网络请求即可完成全量抓取
- `--source html` 时会逐页解析，速度显著慢于 API，但在 API 不可用时更稳妥
- 当前站点偶发 TLS EOF，脚本会先重试 `requests`，仍失败时自动回退 `curl --http1.1`

## 运行测试

```bash
python3 -m unittest test_gtfobins_scraper.py
```

## 免责声明

本工具仅用于学习与研究，请遵守目标站点使用条款以及当地法律法规。
