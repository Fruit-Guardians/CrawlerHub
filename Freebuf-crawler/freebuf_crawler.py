#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FreeBuf网络安全文章爬虫
支持全站分类文章抓取、图片下载、Markdown格式化输出
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import json
import os
from urllib.parse import urljoin, urlparse
import logging
from datetime import datetime
import re
import hashlib
from typing import Optional, Dict, List, Any

class FreeBufCrawler:
    def __init__(self, base_url: str = "https://www.freebuf.com/", delay: int = 2, max_pages: int = 50, categories: Optional[List[str]] = None):
        """初始化爬虫
        
        Args:
            base_url: FreeBuf基础URL
            delay: 请求延迟时间(秒)
            max_pages: 每个分类最大抓取页数
            categories: 要抓取的分类列表
        """
        self.base_url = base_url
        self.delay = max(delay, 1)  # 确保至少1秒延迟
        self.max_pages = max_pages
        self.categories = categories or self._get_default_categories()
        self.category_names = self._get_category_mapping()
        
        # 初始化核心组件
        self._init_session()
        self._init_logging()
        self._init_directories()
        
        # 状态管理
        self.crawled_urls = set()
        self.article_count = 0
        self.start_time = datetime.now()
        
        # 统计信息
        self.stats = {
            'total_articles': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'images_downloaded': 0,
            'start_time': None,
            'end_time': None
        }
        
    @staticmethod
    def _get_default_categories() -> List[str]:
        """获取默认分类列表"""
        return [
            'articles/container',     # 容器安全
            'articles/ai-security',   # AI安全
            'articles/development',   # 开发安全
            'articles/endpoint',      # 终端安全
            'articles/database',      # 数据安全
            'articles/web',           # Web安全
            'articles/network',       # 网络安全
            'articles/es',            # 企业安全
            'ics-articles',           # 工控安全
            'articles/mobile',        # 移动安全
            'articles/system',        # 系统安全
            'articles/others-articles' # 其他安全
        ]
    
    @staticmethod
    def _get_category_mapping() -> Dict[str, str]:
        """获取分类映射表"""
        return {
            'articles/container': '容器安全',
            'articles/ai-security': 'AI安全',
            'articles/development': '开发安全',
            'articles/endpoint': '终端安全',
            'articles/database': '数据安全',
            'articles/web': 'Web安全',
            'articles/network': '网络安全',
            'articles/es': '企业安全',
            'ics-articles': '工控安全',
            'articles/mobile': '移动安全',
            'articles/system': '系统安全',
            'articles/others-articles': '其他安全'
        }
        
    def _init_session(self):
        """初始化请求会话"""
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session.headers.update(self.headers)
        
        # 设置重试策略
        retry_strategy = requests.packages.urllib3.util.retry.Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _init_logging(self):
        """初始化日志配置"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('freebuf_crawler.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _init_directories(self):
        """初始化存储目录"""
        # 创建数据存储目录
        self.data_dir = "freebuf_data"
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        # 创建图片存储目录
        self.images_dir = os.path.join(self.data_dir, "images")
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)
        
        # 创建日志目录
        self.logs_dir = os.path.join(self.data_dir, "logs")
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
        
    def get_page(self, url, retries=3):
        """获取网页内容"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response.text
        except requests.exceptions.RequestException as e:
            self.logger.error(f"获取页面失败: {url}, 错误: {e}")
            if retries > 0:
                self.logger.info(f"重试中... 剩余重试次数: {retries}")
                time.sleep(self.delay * 2)
                return self.get_page(url, retries - 1)
            return None
    
    def parse_article_list(self, html):
        """解析文章列表页面"""
        soup = BeautifulSoup(html, 'html.parser')
        articles = []
        
        # 常见的文章列表选择器
        article_selectors = [
            '.article-item', '.post-item', '.feed-item', '.list-item',
            'article', '.post', '.entry', '[class*="article"]', '[class*="post"]'
        ]
        
        for selector in article_selectors:
            elements = soup.select(selector)
            if elements:
                self.logger.info(f"找到 {len(elements)} 篇文章，使用选择器: {selector}")
                break
        else:
            # 如果没有找到特定选择器，尝试通过链接模式匹配
            links = soup.find_all('a', href=True)
            article_links = []
            for link in links:
                href = link.get('href')
                if href and self.is_article_url(href):
                    article_links.append(link)
            elements = article_links
            self.logger.info(f"通过链接模式找到 {len(elements)} 篇文章")
        
        for element in elements:
            article = self.extract_article_info(element)
            if article:
                articles.append(article)
                
        return articles
    
    def is_article_url(self, url):
        """判断是否为文章URL"""
        article_patterns = [
            r'/articles/',
            r'/news/',
            r'/posts/',
            r'/\d{4}/\d{2}/\d{2}/',
            r'/\d+\.html'
        ]
        
        for pattern in article_patterns:
            if re.search(pattern, url):
                return True
        return False
    
    def extract_article_info(self, element):
        """从文章元素中提取信息"""
        # 提取标题
        title = None
        title_selectors = ['h1', 'h2', 'h3', '.title', '.post-title', '.article-title']
        for selector in title_selectors:
            title_elem = element.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                break
        
        if not title:
            # 尝试从链接文本获取标题
            link = element.find('a')
            if link:
                title = link.get_text(strip=True)
        
        # 提取链接
        url = None
        link = element.find('a')
        if link:
            url = link.get('href')
            if url:
                url = urljoin(self.base_url, url)
        
        # 提取摘要
        summary = None
        summary_selectors = ['.summary', '.excerpt', '.description', '.post-excerpt']
        for selector in summary_selectors:
            summary_elem = element.select_one(selector)
            if summary_elem:
                summary = summary_elem.get_text(strip=True)
                break
        
        # 提取时间
        publish_time = None
        time_selectors = ['.time', '.date', '.post-time', '.publish-time']
        for selector in time_selectors:
            time_elem = element.select_one(selector)
            if time_elem:
                publish_time = time_elem.get_text(strip=True)
                break
        
        # 提取作者
        author = None
        author_selectors = ['.author', '.writer', '.post-author']
        for selector in author_selectors:
            author_elem = element.select_one(selector)
            if author_elem:
                author = author_elem.get_text(strip=True)
                break
        
        if title and url:
            return {
                'title': title,
                'url': url,
                'summary': summary,
                'publish_time': publish_time,
                'author': author,
                'crawl_time': datetime.now().isoformat()
            }
        return None
    
    def parse_article_detail(self, html, url, category_dir=None):
        """解析文章详情页面"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 调试：输出页面标题
        title = soup.find('title')
        if title:
            self.logger.info(f"页面标题: {title.get_text()}")
        
        # 提取文章元信息
        article_meta = self._extract_article_meta(soup)
        
        # 先尝试移除所有无用元素
        self._cleanup_elements(soup)
        
        # 尝试多种内容提取策略
        content_elem = None
        strategies = [
            self._extract_by_selectors,
            self._extract_by_structured_content,
            self._extract_by_paragraph_analysis,
            self.extract_main_content
        ]
        
        for i, strategy in enumerate(strategies):
            self.logger.info(f"尝试内容提取策略 {i+1}: {strategy.__name__}")
            content_elem = strategy(soup)
            if content_elem:
                text = content_elem.get_text(strip=True)
                if text and len(text) > 200:  # 确保内容足够长
                    self.logger.info(f"策略 {i+1} 成功，内容长度: {len(text)}")
                    break
                else:
                    content_elem = None
        
        # 处理图片并生成Markdown内容
        markdown_content = ""
        if content_elem:
            text = content_elem.get_text(strip=True)
            self.logger.info(f"最终内容长度: {len(text)}")
            self.logger.info(f"内容预览: {text[:200]}...")
            markdown_content = self.process_content_with_images(content_elem, category_dir)
        else:
            self.logger.warning("未找到内容元素")
        
        # 提取标签
        tags = self._extract_tags(soup)
        
        # 合并元信息
        result = {
            'url': url,
            'content': markdown_content,
            'tags': tags,
            'crawl_time': datetime.now().isoformat()
        }
        result.update(article_meta)
        
        return result
    
    def _extract_article_meta(self, soup):
        """提取文章元信息"""
        meta = {}
        
        # 提取作者
        author_selectors = [
            '.author', '.writer', '.post-author', '.article-author',
            '.meta-author', '.by-author', '[class*="author"]'
        ]
        for selector in author_selectors:
            author_elem = soup.select_one(selector)
            if author_elem:
                author_text = author_elem.get_text(strip=True)
                if author_text and self._is_valid_text(author_text):
                    meta['author'] = author_text
                    break
        
        # 提取发布时间
        time_selectors = [
            '.time', '.date', '.post-time', '.publish-time',
            '.meta-time', '.post-date', '.article-date',
            '[class*="time"]', '[class*="date"]'
        ]
        for selector in time_selectors:
            time_elem = soup.select_one(selector)
            if time_elem:
                time_text = time_elem.get_text(strip=True)
                if time_text and self._is_valid_text(time_text):
                    meta['publish_time'] = time_text
                    break
        
        # 提取阅读量等统计信息
        view_selectors = [
            '.views', '.read-count', '.post-views',
            '[class*="view"]', '[class*="read"]'
        ]
        for selector in view_selectors:
            view_elem = soup.select_one(selector)
            if view_elem:
                view_text = view_elem.get_text(strip=True)
                if view_text and self._is_valid_text(view_text):
                    meta['views'] = view_text
                    break
        
        return meta
    
    def _extract_by_selectors(self, soup):
        """通过CSS选择器提取内容"""
        content_selectors = [
            '.article-content', '.post-content', '.entry-content',
            '.content', '.post-body', '.article-body',
            '.article-detail', '.post-detail', '.entry-content',
            '.main-content', '.article-main', '.post-main',
            '#article-content', '#post-content', '#content',
            '.article-detail-content', '.post-detail-content',
            '.article-text', '.post-text', '.entry-text',
            '.article-body-content', '.post-body-content'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                text = content_elem.get_text(strip=True)
                if text and len(text) > 200 and self._is_valid_text(text):
                    self.logger.info(f"选择器 {selector} 找到内容长度: {len(text)}")
                    return content_elem
        
        return None
    
    def _extract_by_structured_content(self, soup):
        """通过结构化内容提取"""
        # 寻找包含文章内容的结构化区域
        content_candidates = []
        
        # 检查常见的内容容器
        content_containers = ['article', 'main', '[role="main"]', '.content-area', '.article-area']
        for container in content_containers:
            elements = soup.select(container)
            for elem in elements:
                text = elem.get_text(strip=True)
                if text and len(text) > 300:
                    content_candidates.append((elem, len(text)))
        
        if content_candidates:
            # 选择文本最长的候选
            content_candidates.sort(key=lambda x: x[1], reverse=True)
            return content_candidates[0][0]
        
        return None
    
    def _extract_by_paragraph_analysis(self, soup):
        """通过段落分析提取内容"""
        # 找到所有段落
        paragraphs = soup.find_all('p')
        
        if len(paragraphs) < 3:
            return None
        
        # 分析段落质量
        good_paragraphs = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text and len(text) > 20 and self._is_valid_text(text):
                # 检查是否包含完整句子
                sentences = text.split('。')                
                if len(sentences) > 1 or len(text) > 50:
                    good_paragraphs.append(p)
        
        if len(good_paragraphs) >= 3:
            # 找到这些段落的共同父容器
            parent_map = {}
            for p in good_paragraphs:
                parent = p.parent
                while parent:
                    if parent.name in ['div', 'section', 'article', 'main']:
                        parent_map[parent] = parent_map.get(parent, 0) + 1
                    parent = parent.parent
            
            if parent_map:
                # 选择包含最多优质段落的容器
                best_parent = max(parent_map, key=parent_map.get)
                if parent_map[best_parent] >= 3:
                    return best_parent
        
        return None
    
    def _extract_tags(self, soup):
        """提取文章标签"""
        tags = []
        tag_selectors = [
            '.tags a', '.post-tags a', '.article-tags a',
            '.tag-list a', '.category-tags a',
            '.meta-tags a', '.article-meta-tags a',
            '[class*="tag"] a', '[class*="category"] a'
        ]
        
        for selector in tag_selectors:
            tag_elems = soup.select(selector)
            for tag_elem in tag_elems:
                tag_text = tag_elem.get_text(strip=True)
                if tag_text and self._is_valid_text(tag_text) and tag_text not in tags:
                    tags.append(tag_text)
        
        return tags
    
    def _cleanup_elements(self, soup):
        """清理无用元素"""
        # 移除脚本、样式等
        for elem in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            elem.decompose()
        
        # 移除按钮、输入框等交互元素
        for elem in soup(['button', 'input', 'select', 'textarea']):
            elem.decompose()
        
        # 移除包含特定文本的元素
        button_texts = ['收入我的专辑', '加入我的收藏', '展开更多', '收起', '分享', '点赞']
        for text in button_texts:
            for elem in soup.find_all(text=re.compile(text)):
                parent = elem.parent
                if parent:
                    parent.decompose()
    
    def save_article(self, article_info, article_detail=None, category_dir=None):
        """保存文章数据为Markdown格式"""
        article_data = {**article_info}
        if article_detail:
            article_data.update(article_detail)
        
        # 确定保存目录
        save_dir = category_dir if category_dir else self.data_dir
        
        # 生成安全的文件名
        safe_filename = self.generate_safe_filename(article_info['title'])
        filename = f"{safe_filename}.md"
        filepath = os.path.join(save_dir, filename)
        
        # 如果文件已存在，添加序号
        counter = 1
        original_filepath = filepath
        while os.path.exists(filepath):
            filename = f"{safe_filename}_{counter}.md"
            filepath = os.path.join(save_dir, filename)
            counter += 1
        
        # 生成Markdown内容
        markdown_content = self.generate_markdown(article_data)
        
        # 保存Markdown文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        self.article_count += 1
        self.logger.info(f"保存文章: {article_info['title']} -> {filepath}")
    
    def generate_safe_filename(self, title):
        """生成安全的文件名"""
        # 移除特殊字符，只保留中文、字母、数字、下划线和连字符
        import re
        
        # 将中文和英文保持不变，移除其他特殊字符
        safe_name = re.sub(r'[\\/:*?"<>|]', '', title)
        
        # 替换空格为下划线
        safe_name = re.sub(r'\s+', '_', safe_name)
        
        # 移除连续的下划线
        safe_name = re.sub(r'_+', '_', safe_name)
        
        # 去除首尾的下划线
        safe_name = safe_name.strip('_')
        
        # 如果文件名为空，使用默认名称
        if not safe_name:
            safe_name = f"article_{self.article_count:06d}"
        
        # 限制文件名长度（避免路径过长）
        if len(safe_name) > 100:
            safe_name = safe_name[:100].rstrip('_')
        
        return safe_name
    
    def extract_main_content(self, soup):
        """智能提取主要内容"""
        # 先清理无用元素
        self._cleanup_elements(soup)
        
        # 移除特定的无用类
        useless_classes = ['nav', 'menu', 'sidebar', 'comments', 'share', 'related', 'tags', 'meta', 'info', 'author', 'date', 'header', 'footer']
        for class_name in useless_classes:
            for elem in soup.find_all(class_=re.compile(class_name)):
                elem.decompose()
        
        # 寻找可能包含文章内容的区域
        content_candidates = []
        
        # 检查所有div和section
        for elem in soup.find_all(['div', 'section', 'article', 'main']):
            # 跳过明显不是内容的区域
            class_name = elem.get('class', [])
            if class_name:
                class_str = ' '.join(class_name).lower()
                if any(useless in class_str for useless in ['nav', 'menu', 'sidebar', 'comment', 'share', 'related', 'tag', 'meta', 'info', 'author', 'date', 'header', 'footer']):
                    continue
            
            # 检查文本内容
            text = elem.get_text(strip=True)
            if len(text) > 300:  # 只考虑文本长度超过300字符的元素
                # 检查是否包含按钮文本
                if not any(btn_text in text for btn_text in ['收入我的专辑', '加入我的收藏', '展开更多', '收起', '分享', '点赞']):
                    content_candidates.append((elem, len(text)))
        
        if content_candidates:
            # 选择文本最长的候选
            content_candidates.sort(key=lambda x: x[1], reverse=True)
            return content_candidates[0][0]
        
        # 如果还是没找到，尝试查找包含段落的区域
        for elem in soup.find_all(['div', 'section', 'article']):
            paragraphs = elem.find_all('p')
            if len(paragraphs) >= 3:  # 至少3个段落
                return elem
        
        # 最后的备选方案
        return soup.find('body') or soup
    
    def process_content_with_images(self, content_elem, category_dir=None):
        """处理内容中的图片，生成Markdown格式"""
        # 首先移除不需要的元素
        for elem in content_elem.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'button', 'input', 'select', 'textarea']):
            elem.decompose()
        
        # 移除特定的无用元素（根据FreeBuf网站的实际情况）
        for elem in content_elem.find_all(class_=['article-meta', 'article-info', 'article-tags', 'share-box', 'related-articles']):
            elem.decompose()
        
        markdown_lines = []
        
        def process_element(element, depth=0):
            if element.name is None:
                # 文本节点
                text = str(element).strip()
                if text and self._is_valid_text(text):
                    markdown_lines.append(text)
            elif element.name == 'img':
                # 处理图片
                img_src = element.get('src')
                img_alt = element.get('alt', '')
                img_title = element.get('title', '')
                
                if img_src:
                    # 下载图片并获取本地路径
                    local_img_path = self.download_image(img_src)
                    if local_img_path:
                        # 构建图片引用，使用相对于分类目录的路径
                        if category_dir:
                            # 如果在分类目录中，图片路径需要向上一级
                            img_path = f"../images/{local_img_path}"
                        else:
                            # 如果在根目录，直接使用images路径
                            img_path = f"images/{local_img_path}"
                        alt_text = img_alt or img_title or '图片'
                        markdown_lines.append(f"![{alt_text}]({img_path})")
                    else:
                        # 如果下载失败，保留原始链接
                        alt_text = img_alt or img_title or '图片'
                        markdown_lines.append(f"![{alt_text}]({img_src})")
                else:
                    markdown_lines.append(f"![{img_alt or img_title or '图片'}]")
            elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                # 处理标题
                level = int(element.name[1])
                text = element.get_text(strip=True)
                if text and self._is_valid_text(text):
                    # 确保标题级别合理（避免过深的嵌套）
                    adjusted_level = min(level + 1, 6)  # 文章内容从h2开始
                    markdown_lines.append(f"{'#' * adjusted_level} {text}")
                    markdown_lines.append("")  # 标题后空行
            elif element.name == 'p':
                # 处理段落
                text = element.get_text(strip=True)
                if text and self._is_valid_text(text):
                    # 检查是否是标题文本（单独的粗体文本）
                    if element.find('strong') and len(text) < 100:
                        markdown_lines.append(f"**{text}**")
                    else:
                        markdown_lines.append(f"{text}")
                    markdown_lines.append("")  # 段落后空行
            elif element.name == 'a':
                # 处理链接
                href = element.get('href')
                text = element.get_text(strip=True)
                if href and text and self._is_valid_text(text):
                    markdown_lines.append(f"[{text}]({href})")
                elif text and self._is_valid_text(text):
                    markdown_lines.append(text)
            elif element.name in ['ul', 'ol']:
                # 处理列表
                list_items = element.find_all('li', recursive=False)
                if list_items:
                    for i, li in enumerate(list_items):
                        text = li.get_text(strip=True)
                        if text and self._is_valid_text(text):
                            if element.name == 'ul':
                                markdown_lines.append(f"- {text}")
                            else:
                                markdown_lines.append(f"{i + 1}. {text}")
                    markdown_lines.append("")  # 列表后空行
            elif element.name in ['strong', 'b']:
                # 处理粗体
                text = element.get_text(strip=True)
                if text and self._is_valid_text(text):
                    markdown_lines.append(f"**{text}**")
            elif element.name in ['em', 'i']:
                # 处理斜体
                text = element.get_text(strip=True)
                if text and self._is_valid_text(text):
                    markdown_lines.append(f"*{text}*")
            elif element.name == 'code':
                # 处理行内代码
                text = element.get_text(strip=True)
                if text and self._is_valid_text(text):
                    markdown_lines.append(f"`{text}`")
            elif element.name == 'pre':
                # 处理代码块
                text = element.get_text()
                if text and self._is_valid_text(text):
                    # 尝试检测代码语言
                    code_class = element.get('class', [])
                    language = ''
                    for cls in code_class:
                        if 'language-' in cls:
                            language = cls.replace('language-', '')
                            break
                    
                    if language:
                        markdown_lines.append(f"```{language}\n{text}\n```")
                    else:
                        markdown_lines.append(f"```\n{text}\n```")
                    markdown_lines.append("")  # 代码块后空行
            elif element.name == 'blockquote':
                # 处理引用
                text = element.get_text(strip=True)
                if text and self._is_valid_text(text):
                    # 多行引用处理
                    lines = text.split('\n')
                    for line in lines:
                        if line.strip():
                            markdown_lines.append(f"> {line.strip()}")
                    markdown_lines.append("")  # 引用后空行
            elif element.name == 'div':
                # 处理div容器，递归处理子元素
                # 先检查是否是特殊容器
                div_class = element.get('class', [])
                if 'code-block' in div_class or 'highlight' in div_class:
                    # 代码块容器
                    code_text = element.get_text()
                    if code_text and self._is_valid_text(code_text):
                        markdown_lines.append(f"```\n{code_text}\n```")
                        markdown_lines.append("")
                else:
                    # 普通div容器
                    for child in element.children:
                        process_element(child, depth + 1)
            elif element.name == 'table':
                # 处理表格
                markdown_table = self._process_table(element)
                if markdown_table:
                    markdown_lines.append(markdown_table)
                    markdown_lines.append("")
            else:
                # 其他元素，递归处理子元素
                for child in element.children:
                    process_element(child, depth + 1)
        
        # 处理所有子元素
        for element in content_elem.children:
            process_element(element)
        
        # 清理结果：移除多余的空行，合并连续的空行
        cleaned_lines = []
        prev_empty = False
        for line in markdown_lines:
            if line.strip() == "":
                if not prev_empty:
                    cleaned_lines.append("")
                prev_empty = True
            else:
                cleaned_lines.append(line)
                prev_empty = False
        
        return '\n'.join(cleaned_lines)
    
    def _is_valid_text(self, text):
        """检查文本是否有效（不是按钮文本等）"""
        invalid_patterns = [
            r'^[+收加展更]',  # 以这些字符开头的文本
            r'收入我的专辑',
            r'加入我的收藏', 
            r'展开更多',
            r'收起',
            r'分享',
            r'点赞',
            r'评论',
            r'关注',
            r'阅读全文',
            r'点击查看',
            r'立即购买',
            r'免费试用',
            r'了解更多',
            r'联系我们',
            r'返回顶部',
            r'上一页',
            r'下一页',
            r'首页',
            r'尾页'
        ]
        
        text = text.strip()
        if not text or len(text) < 2:
            return False
            
        for pattern in invalid_patterns:
            if re.search(pattern, text):
                return False
                
        return True
    
    def _process_table(self, table_elem):
        """处理HTML表格为Markdown格式"""
        try:
            rows = table_elem.find_all('tr')
            if not rows:
                return None
            
            markdown_lines = []
            
            # 处理表头
            header_row = rows[0]
            headers = header_row.find_all(['th', 'td'])
            if headers:
                header_cells = []
                for header in headers:
                    header_text = header.get_text(strip=True)
                    header_cells.append(header_text)
                markdown_lines.append(f"| {' | '.join(header_cells)} |")
                markdown_lines.append(f"| {' | '.join(['---'] * len(header_cells))} |")
            
            # 处理数据行
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if cells:
                    row_cells = []
                    for cell in cells:
                        cell_text = cell.get_text(strip=True)
                        row_cells.append(cell_text)
                    markdown_lines.append(f"| {' | '.join(row_cells)} |")
            
            return '\n'.join(markdown_lines)
        except Exception as e:
            self.logger.warning(f"处理表格失败: {e}")
            return None
    
    def download_image(self, img_url):
        """下载图片到本地"""
        try:
            # 构建完整URL
            if not img_url.startswith(('http://', 'https://')):
                img_url = urljoin(self.base_url, img_url)
            
            # 清理URL参数
            img_url = self._clean_image_url(img_url)
            
            # 生成文件名
            url_hash = hashlib.md5(img_url.encode()).hexdigest()
            file_extension = self.get_image_extension(img_url)
            filename = f"{url_hash}{file_extension}"
            filepath = os.path.join(self.images_dir, filename)
            
            # 如果文件已存在，直接返回
            if os.path.exists(filepath):
                self.logger.debug(f"图片已存在: {filename}")
                return filename
            
            # 下载图片
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': self.base_url,
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            response = self.session.get(img_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # 检查文件类型
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                self.logger.warning(f"URL不是图片: {img_url}, Content-Type: {content_type}")
                return None
            
            # 保存图片
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            # 验证文件是否成功保存
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                self.logger.info(f"下载图片成功: {img_url} -> {filename} ({os.path.getsize(filepath)} bytes)")
                self.stats['images_downloaded'] += 1
                return filename
            else:
                self.logger.error(f"图片保存失败: {filename}")
                if os.path.exists(filepath):
                    os.remove(filepath)
                return None
            
        except Exception as e:
            self.logger.error(f"下载图片失败: {img_url}, 错误: {e}")
            return None
    
    def _clean_image_url(self, img_url):
        """清理图片URL，移除不必要的参数"""
        try:
            parsed = urlparse(img_url)
            # 移除一些常见的追踪参数
            params = []
            for param in parsed.query.split('&'):
                if param and not any(skip in param.lower() for skip in ['utm_', 'ref=', 'from=', 'share=', 'random=']):
                    params.append(param)
            
            clean_query = '&'.join(params) if params else ''
            clean_url = parsed._replace(query=clean_query).geturl()
            return clean_url
        except Exception:
            return img_url
    
    def get_image_extension(self, img_url):
        """根据URL获取图片扩展名"""
        parsed_url = urlparse(img_url)
        path = parsed_url.path.lower()
        
        if path.endswith(('.jpg', '.jpeg')):
            return '.jpg'
        elif path.endswith('.png'):
            return '.png'
        elif path.endswith('.gif'):
            return '.gif'
        elif path.endswith('.webp'):
            return '.webp'
        elif path.endswith('.svg'):
            return '.svg'
        elif path.endswith('.bmp'):
            return '.bmp'
        elif path.endswith('.tiff'):
            return '.tiff'
        else:
            return '.jpg'  # 默认扩展名
    
    def generate_markdown(self, article_data):
        """生成Markdown格式内容"""
        markdown = f"# {article_data.get('title', '无标题')}\n\n"
        
        # 添加分隔线
        markdown += "---\n\n"
        
        # 添加元数据
        markdown += f"**URL**: {article_data.get('url', '')}\n\n"
        markdown += f"**作者**: {article_data.get('author', '未知')}\n\n"
        markdown += f"**发布时间**: {article_data.get('publish_time', '未知')}\n\n"
        markdown += f"**爬取时间**: {article_data.get('crawl_time', '')}\n\n"
        
        # 添加摘要
        if article_data.get('summary'):
            markdown += "## 摘要\n\n"
            markdown += f"{article_data['summary']}\n\n"
        
        # 添加标签
        if article_data.get('tags'):
            markdown += "## 标签\n\n"
            tags_str = ' '.join([f"`{tag}`" for tag in article_data['tags']])
            markdown += f"{tags_str}\n\n"
        
        # 添加分隔线
        markdown += "---\n\n"
        
        # 添加正文内容
        if article_data.get('content'):
            markdown += "## 正文\n\n"
            markdown += f"{article_data['content']}\n"
        
        return markdown
    
    def crawl(self):
        """开始爬取"""
        self.logger.info("开始爬取FreeBuf网站...")
        
        # 爬取指定分类
        for category in self.categories:
            if self.article_count >= self.max_pages:
                break
                
            category_url = urljoin(self.base_url, category)
            category_name = self.category_names.get(category, category.split('/')[-1])
            self.logger.info(f"爬取分类: {category_name} - {category_url}")
            
            # 为每个分类创建子目录
            dir_name = category.split('/')[-1]
            category_dir = os.path.join(self.data_dir, dir_name)
            if not os.path.exists(category_dir):
                os.makedirs(category_dir)
            
            self.crawl_category(category_url, category_dir)
            
            # 礼貌性延迟
            time.sleep(self.delay + random.uniform(0, 2))
        
        self.logger.info(f"爬取完成，共爬取 {self.article_count} 篇文章")
    
    def crawl_category(self, category_url, category_dir=None):
        """爬取单个分类"""
        page = 1
        while self.article_count < self.max_pages:
            # 构建分页URL
            if page == 1:
                url = category_url
            else:
                # 常见的分页模式
                page_patterns = [
                    f"{category_url}page/{page}/",
                    f"{category_url}?page={page}",
                    f"{category_url}index_{page}.html"
                ]
                
                url = page_patterns[0]  # 默认使用第一种模式
            
            self.logger.info(f"爬取页面: {url}")
            
            html = self.get_page(url)
            if not html:
                break
            
            articles = self.parse_article_list(html)
            if not articles:
                self.logger.warning("未找到文章，可能到达最后一页")
                break
            
            # 爬取每篇文章的详情
            for article in articles:
                if article['url'] in self.crawled_urls:
                    continue
                    
                self.crawled_urls.add(article['url'])
                
                # 爬取文章详情
                detail_html = self.get_page(article['url'])
                if detail_html:
                    article_detail = self.parse_article_detail(detail_html, article['url'], category_dir)
                    self.save_article(article, article_detail, category_dir)
                    
                    # 速率限制
                    time.sleep(self.delay + random.uniform(0, 1))
                
                if self.article_count >= self.max_pages:
                    break
            
            page += 1
            time.sleep(self.delay)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取爬虫统计信息"""
        elapsed_time = datetime.now() - self.start_time
        return {
            'total_articles': self.stats['total_articles'],
            'successful_downloads': self.stats['successful_downloads'],
            'failed_downloads': self.stats['failed_downloads'],
            'images_downloaded': self.stats['images_downloaded'],
            'elapsed_time': str(elapsed_time),
            'articles_per_minute': round(self.stats['total_articles'] / max(elapsed_time.total_seconds() / 60, 0.1), 2) if elapsed_time.total_seconds() > 0 else 0,
            'success_rate': f"{round(self.stats['successful_downloads'] / max(self.stats['total_articles'], 1) * 100, 1)}%" if self.stats['total_articles'] > 0 else "0%"
        }
    
    def print_summary(self):
        """打印爬取摘要"""
        stats = self.get_statistics()
        print("\n" + "="*50)
        print("📊 FreeBuf爬虫运行摘要")
        print("="*50)
        print(f"📝 总文章数: {stats['total_articles']}")
        print(f"✅ 成功下载: {stats['successful_downloads']}")
        print(f"❌ 失败下载: {stats['failed_downloads']}")
        print(f"🖼️  图片下载: {stats['images_downloaded']}")
        print(f"⏱️  运行时间: {stats['elapsed_time']}")
        print(f"📈 每分钟文章: {stats['articles_per_minute']}")
        print(f"🎯 成功率: {stats['success_rate']}")
        print("="*50)

if __name__ == "__main__":
    try:
        # 创建爬虫实例
        crawler = FreeBufCrawler(delay=2, max_pages=100)
        
        # 开始爬取
        crawler.crawl()
        
        # 打印统计摘要
        crawler.print_summary()
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断爬虫运行")
    except Exception as e:
        print(f"❌ 爬虫运行出错: {e}")