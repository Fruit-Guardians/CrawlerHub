# GTFOBins 网站爬虫

这个项目用于爬取 [GTFOBins](https://gtfobins.github.io/) 网站的所有词条信息。GTFOBins 是一个收集Unix二进制文件提权技术的知识库。

## 功能特性

- 自动爬取GTFOBins网站的所有二进制文件词条
- 提取每个二进制文件的详细信息，包括：
  - 二进制文件名称
  - 功能描述
  - 提权方法和技术
  - 代码示例
  - 使用场景
- 支持多种输出格式：JSON 和 CSV
- 包含进度显示和错误处理

## 文件说明

- `gtfobins_scraper.py` - 主要的爬虫脚本
- `requirements.txt` - Python依赖包列表
- `gtfobins_data.json` - 爬取结果的JSON格式文件（运行后生成）
- `gtfobins_data.csv` - 爬取结果的CSV格式文件（运行后生成）

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

运行爬虫脚本：

```bash
python gtfobins_scraper.py
```

脚本会自动：
1. 获取GTFOBins网站上所有二进制文件的列表
2. 逐个爬取每个二进制文件的详细信息
3. 将结果保存为JSON和CSV两种格式

## 输出格式

### JSON格式
每个二进制文件的信息包含以下字段：
```json
{
  "name": "二进制文件名",
  "url": "词条页面URL",
  "description": "功能描述",
  "functions": [
    {
      "name": "功能名称",
      "description": "功能描述",
      "code_examples": ["代码示例1", "代码示例2"]
    }
  ],
  "examples": ["所有代码示例"]
}
```

### CSV格式
包含以下列：
- Binary Name: 二进制文件名
- URL: 词条页面URL
- Description: 功能描述
- Functions: 功能列表（分号分隔）
- Examples: 代码示例（分号分隔，最多3个）

## 注意事项

- 爬取过程可能需要较长时间（约390个词条）
- 脚本包含1秒的请求间隔以避免对服务器造成过大压力
- 如果网络连接不稳定，可能会有部分词条爬取失败
- 建议在网络环境良好的情况下运行

## 统计信息

脚本运行完成后会显示：
- 成功爬取的二进制文件数量
- 总功能数量
- 总示例数量

## 免责声明

本工具仅用于学习和研究目的。请遵守相关法律法规和网站的使用条款。