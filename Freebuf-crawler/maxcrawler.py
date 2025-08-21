from freebuf_crawler import FreeBufCrawler

try:
    # 创建爬虫实例 - 全量爬取配置
    crawler = FreeBufCrawler(
        delay=3,           # 3秒延迟，避免被限制
        max_pages=50000,   # 设置一个很大的数值
        categories=None    # 使用默认的所有分类
    )
    
    # 开始爬取
    crawler.crawl()
    
    # 打印统计摘要
    crawler.print_summary()
    
except KeyboardInterrupt:
    print("\n⚠️  用户中断爬虫运行")
except Exception as e:
    print(f"❌ 爬虫运行出错: {e}")