#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GTFOBins 网站爬虫
爬取所有词条信息并保存为JSON格式
"""

import requests
import json
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
from typing import List, Dict, Any

class GTFOBinsScraper:
    def __init__(self):
        self.base_url = "https://gtfobins.github.io/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.binaries = []
        self.scraped_data = []
        
    def get_page(self, url: str) -> BeautifulSoup:
        """获取页面内容"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"获取页面失败 {url}: {e}")
            return None
            
    def get_binary_list(self) -> List[str]:
        """从主页获取所有二进制文件列表"""
        print("正在获取二进制文件列表...")
        soup = self.get_page(self.base_url)
        if not soup:
            return []
            
        binaries = []
        # 查找所有二进制文件链接
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('/gtfobins/') and href.endswith('/'):
                binary_name = href.split('/')[-2]
                if binary_name and binary_name not in binaries:
                    binaries.append(binary_name)
                    
        # 如果没有找到链接，尝试从页面内容中提取
        if not binaries:
            # 查找包含二进制文件名的元素
            for element in soup.find_all(['div', 'span', 'li']):
                if element.get('class') and 'binary' in ' '.join(element.get('class')):
                    text = element.get_text().strip()
                    if text and text.isalnum():
                        binaries.append(text)
                        
        print(f"找到 {len(binaries)} 个二进制文件")
        return binaries
        
    def scrape_binary_info(self, binary_name: str) -> Dict[str, Any]:
        """爬取单个二进制文件的详细信息"""
        url = f"{self.base_url}gtfobins/{binary_name}/"
        print(f"正在爬取: {binary_name}")
        
        soup = self.get_page(url)
        if not soup:
            return None
            
        binary_info = {
            'name': binary_name,
            'url': url,
            'functions': [],
            'description': '',
            'examples': []
        }
        
        # 获取描述
        desc_elem = soup.find('p')
        if desc_elem:
            binary_info['description'] = desc_elem.get_text().strip()
            
        # 获取功能列表
        function_sections = soup.find_all(['div', 'section'], class_=re.compile(r'function|capability'))
        if not function_sections:
            # 尝试其他方式查找功能
            function_sections = soup.find_all('h2')
            
        for section in function_sections:
            function_name = section.get_text().strip()
            if function_name and function_name.lower() not in ['description', 'examples']:
                function_info = {
                    'name': function_name,
                    'code_examples': [],
                    'description': ''
                }
                
                # 查找代码示例
                next_elem = section.find_next_sibling()
                while next_elem and next_elem.name != 'h2':
                    if next_elem.name == 'pre' or (next_elem.name == 'div' and 'highlight' in next_elem.get('class', [])):
                        code = next_elem.get_text().strip()
                        if code:
                            function_info['code_examples'].append(code)
                    elif next_elem.name == 'p':
                        if not function_info['description']:
                            function_info['description'] = next_elem.get_text().strip()
                    next_elem = next_elem.find_next_sibling()
                    
                binary_info['functions'].append(function_info)
                
        # 获取所有代码示例
        code_blocks = soup.find_all(['pre', 'code'])
        for block in code_blocks:
            code = block.get_text().strip()
            if code and code not in binary_info['examples']:
                binary_info['examples'].append(code)
                
        return binary_info
        
    def scrape_all(self) -> List[Dict[str, Any]]:
        """爬取所有二进制文件信息"""
        # 首先获取二进制文件列表
        self.binaries = self.get_binary_list()
        
        # 如果没有从主页获取到，使用已知的一些常见二进制文件
        if not self.binaries:
            print("从主页获取列表失败，使用预定义列表...")
            self.binaries = [
                '7z', 'aa-exec', 'ab', 'agetty', 'alpine', 'ansible-playbook', 
                'ansible-test', 'aoss', 'apache2ctl', 'apt-get', 'apt', 'ar', 
                'aria2c', 'arj', 'arp', 'as', 'ascii-xfr', 'ash', 'aspell', 
                'at', 'atobm', 'awk', 'base32', 'base64', 'basenc', 'bash', 
                'bc', 'bridge', 'busybox', 'bzip2', 'cabal', 'cancel', 'cat', 
                'chmod', 'chown', 'chroot', 'cobc', 'column', 'comm', 'cp', 
                'cpio', 'cpulimit', 'csh', 'csplit', 'csvtool', 'cupsfilter', 
                'curl', 'cut', 'dash', 'date', 'dd', 'dialog', 'diff', 'dig', 
                'distcc', 'dmsetup', 'docker', 'dosbox', 'ed', 'efax', 'elvish', 
                'emacs', 'env', 'eqn', 'espeak', 'expand', 'expect', 'file', 
                'find', 'fish', 'flock', 'fmt', 'fold', 'gawk', 'gcc', 'gdb', 
                'gimp', 'git', 'grep', 'gzip', 'head', 'hexdump', 'highlight', 
                'iconv', 'install', 'ionice', 'ip', 'jjs', 'join', 'jq', 'jrunscript', 
                'julia', 'ksh', 'ld.so', 'less', 'logsave', 'look', 'lua', 'make', 
                'man', 'mawk', 'more', 'mount', 'mtr', 'mv', 'nano', 'nawk', 
                'nc', 'nice', 'nl', 'nmap', 'node', 'nohup', 'od', 'openssl', 
                'paste', 'perl', 'pg', 'php', 'pic', 'pico', 'python', 'readelf', 
                'rev', 'rlwrap', 'rsync', 'ruby', 'run-parts', 'rvim', 'sed', 
                'setarch', 'sh', 'shuf', 'socat', 'sort', 'split', 'sqlite3', 
                'ssh', 'start-stop-daemon', 'stdbuf', 'strace', 'strings', 
                'systemctl', 'tac', 'tail', 'tar', 'taskset', 'tclsh', 'tee', 
                'telnet', 'tftp', 'time', 'timeout', 'tmux', 'top', 'touch', 
                'tr', 'ul', 'unexpand', 'uniq', 'unshare', 'unzip', 'update-alternatives', 
                'uudecode', 'uuencode', 'vi', 'vim', 'watch', 'wc', 'wget', 
                'whois', 'xargs', 'xxd', 'xz', 'yum', 'zip', 'zsh', 'zypper'
            ]
            
        print(f"开始爬取 {len(self.binaries)} 个二进制文件的信息...")
        
        for i, binary in enumerate(self.binaries, 1):
            print(f"进度: {i}/{len(self.binaries)} - {binary}")
            
            binary_info = self.scrape_binary_info(binary)
            if binary_info:
                self.scraped_data.append(binary_info)
                
            # 添加延迟避免过于频繁的请求
            time.sleep(1)
            
        return self.scraped_data
        
    def save_to_json(self, filename: str = 'gtfobins_data.json'):
        """保存数据到JSON文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.scraped_data, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到 {filename}")
        
    def save_to_csv(self, filename: str = 'gtfobins_data.csv'):
        """保存数据到CSV文件"""
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Binary Name', 'URL', 'Description', 'Functions', 'Examples'])
            
            for item in self.scraped_data:
                functions = '; '.join([func['name'] for func in item.get('functions', [])])
                examples = '; '.join(item.get('examples', [])[:3])  # 只取前3个示例
                writer.writerow([
                    item['name'],
                    item['url'],
                    item['description'],
                    functions,
                    examples
                ])
                
        print(f"数据已保存到 {filename}")

def main():
    scraper = GTFOBinsScraper()
    
    try:
        # 爬取所有数据
        data = scraper.scrape_all()
        
        if data:
            print(f"\n爬取完成！共获取 {len(data)} 个二进制文件的信息")
            
            # 保存为JSON格式
            scraper.save_to_json()
            
            # 保存为CSV格式
            scraper.save_to_csv()
            
            # 显示统计信息
            total_functions = sum(len(item.get('functions', [])) for item in data)
            total_examples = sum(len(item.get('examples', [])) for item in data)
            
            print(f"\n统计信息:")
            print(f"- 二进制文件数量: {len(data)}")
            print(f"- 总功能数量: {total_functions}")
            print(f"- 总示例数量: {total_examples}")
            
        else:
            print("没有获取到任何数据")
            
    except KeyboardInterrupt:
        print("\n用户中断爬取")
    except Exception as e:
        print(f"爬取过程中出现错误: {e}")
        
if __name__ == "__main__":
    main()