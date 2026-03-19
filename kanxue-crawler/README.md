# 看雪文章爬虫

基于 `Playwright + Crawlee + SQLite + Markdown` 的看雪文章采集器，目标是做一套适合线下 CTF 备赛和知识归档的长期方案，而不是一次性脚本。

## 设计目标

| 目标 | 方案 |
|---|---|
| 稳定采集 | `Playwright` 复用人工登录会话，必要时走浏览器态 |
| 抗验证 | 普通帖子统一归一化为 `thread-xxxx.htm?style=1` 简化页 |
| 增量抓取 | `SQLite` 管理发现任务、详情任务和文章元数据 |
| 可离线阅读 | 导出 `Markdown + 本地图片资源` |
| 可赛场检索 | `SQLite FTS5` 全文搜索标题、作者、标签、正文 |

## 目录结构

```text
src/
  browser/        # Playwright 上下文和会话复用
  crawlee/        # 列表发现 + 详情抓取主流程
  discovery/      # 看雪 URL 分类与归一化
  export/         # Markdown 导出与资源本地化
  parser/         # 看雪正文抽取与 Markdown 转换
  seeds/          # 站点种子页
  store/          # SQLite / 文件归档
  utils/          # 文本、日志、时间、哈希
  index.js        # CLI 入口
data/
  assets/
  crawlee/
  db/
  json/
  markdown/
  raw/
logs/
tests/
```

## 运行方式

| 步骤 | 命令 | 说明 |
|---|---|---|
| 安装依赖 | `npm install` | 首次执行 |
| 安装浏览器 | `npm run bootstrap` | 安装 Playwright Chromium |
| 预热会话 | `npm run bootstrap-session:chrome` | 推荐优先用系统 Chrome |
| 发现链接 | `npm run discover` | 从种子页入库待抓链接 |
| 抓取详情 | `npm run crawl` | 抓正文、落库、存原始 HTML |
| 重新解析 | `npm run refresh:raw` | 用已保存的 raw HTML 重建标题、分类、正文 |
| 导出 Markdown | `npm run export:markdown` | 下载图片并本地化引用 |
| 查看统计 | `npm run stats` | 查看库里已有任务和文章数 |
| 本地搜索 | `npm run search -- --q frida` | 用 SQLite FTS 搜关键词 |

## 注意事项

| 项目 | 建议 |
|---|---|
| 登录态 | 首次建议人工登录一次，保存 `data/session/kanxue-storage-state.json` |
| 验证页 | 若出现“安全验证”，优先重新执行 `bootstrap-session:chrome` |
| 并发 | 当前默认低并发，适合稳跑，不建议随意拉高 |
| 使用范围 | 适合个人学习和赛前资料整理，不建议公开镜像整站内容 |
