# FreeBuf 网络安全文章爬虫

>基于 claude code 开发

## 📁 支持的分类

| 分类 | URL路径 | 中文说明 |
|------|---------|----------|
| 容器安全 | `articles/container` | Docker、K8s等容器安全 |
| AI安全 | `articles/ai-security` | 人工智能安全 |
| 开发安全 | `articles/development` | DevSecOps、安全开发 |
| 终端安全 | `articles/endpoint` | 主机、终端安全 |
| 数据安全 | `articles/database` | 数据库、数据保护 |
| Web安全 | `articles/web` | Web应用安全 |
| 网络安全 | `articles/network` | 网络攻防、协议安全 |
| 企业安全 | `articles/es` | 企业级安全解决方案 |
| 工控安全 | `ics-articles` | 工业控制系统安全 |
| 移动安全 | `articles/mobile` | 移动应用安全 |
| 系统安全 | `articles/system` | 操作系统安全 |
| 其他安全 | `articles/others-articles` | 其他安全主题 |

## 🚀 快速开始
我这里写了一个全量版本，你们可以根据需要自己改一下

```python
python3 maxcrawler.py
```

### 安装依赖

```bash
pip install requests beautifulsoup4
```

### 基本使用

```python
from freebuf_crawler import FreeBufCrawler

# 创建爬虫实例
crawler = FreeBufCrawler(
    delay=2,           # 请求间隔2秒
    max_pages=50,      # 每个分类最多50页
)

# 开始爬取
crawler.crawl()
```

### 自定义分类

```python
# 只爬取特定分类
categories = ['articles/web', 'articles/ai-security']
crawler = FreeBufCrawler(categories=categories)
crawler.crawl()
```

## 📂 输出结构

```
freebuf_data/
├── images/              # 所有图片文件
├── 容器安全/            # 分类目录
│   ├── 文章标题1.md
│   └── 文章标题2.md
├── Web安全/
│   ├── 文章标题3.md
│   └── 文章标题4.md
└── logs/                # 日志文件
```

## 🛠️ 配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `base_url` | str | `"https://www.freebuf.com/"` | FreeBuf基础URL |
| `delay` | int | `2` | 请求间隔时间(秒) |
| `max_pages` | int | `50` | 每个分类最大页数 |
| `categories` | list | `None` | 自定义分类列表 |
