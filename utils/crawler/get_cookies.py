#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微博Cookie获取脚本
支持Playwright和Selenium两种方式自动获取登录后的Cookie

使用方法:
    python get_cookies.py                    # 交互式选择
    python get_cookies.py --playwright       # 使用Playwright
    python get_cookies.py --selenium         # 使用Selenium
    
依赖安装:
    Playwright方式: pip install playwright && playwright install chromium
    Selenium方式:   pip install selenium webdriver-manager
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path

# ==================== 核心功能函数 ====================

def save_cookies_to_file(cookies, filename="weibo_cookies.json"):
    """
    保存Cookie到JSON文件
    
    Args:
        cookies: Cookie列表 (字典列表)
        filename: 保存的文件名
        
    Returns:
        str: 保存的文件路径
    """
    try:
        # 确保cookies是列表格式
        if not isinstance(cookies, list):
            raise ValueError(f"Cookie应该是列表格式, 实际收到: {type(cookies)}")
        
        # 获取脚本所在目录作为默认保存路径
        script_dir = Path(__file__).parent
        file_path = script_dir / filename
        
        # 写入JSON文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        
        print(f"[✓] Cookie已保存到: {file_path}")
        return str(file_path)
        
    except Exception as e:
        print(f"[✗] 保存Cookie失败: {e}")
        raise


def load_cookies_from_file(filename="weibo_cookies.json"):
    """
    从JSON文件读取Cookie
    
    Args:
        filename: Cookie文件名
        
    Returns:
        list: Cookie列表
    """
    try:
        script_dir = Path(__file__).parent
        file_path = script_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Cookie文件不存在: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        
        print(f"[✓] 已从 {file_path} 加载 {len(cookies)} 条Cookie")
        return cookies
        
    except Exception as e:
        print(f"[✗] 读取Cookie失败: {e}")
        raise


def print_usage():
    """打印使用说明"""
    usage = """
==========================================
     微博Cookie获取工具 - 使用说明
==========================================

【功能说明】
  自动启动浏览器,打开微博登录页面,
  用户登录后自动保存Cookie到本地文件。

【运行方式】
  1. 交互式选择:
     python get_cookies.py
     
  2. 指定方式:
     python get_cookies.py --playwright
     python get_cookies.py --selenium

【依赖安装】
  Playwright方式:
    pip install playwright
    playwright install chromium
  
  Selenium方式:
    pip install selenium webdriver-manager

【输出文件】
  weibo_cookies.json (默认)

【使用Cookie】
  from get_cookies import load_cookies_from_file
  cookies = load_cookies_from_file()

==========================================
"""
    print(usage)


# ==================== Playwright 方式 ====================

def get_cookies_with_playwright():
    """
    使用Playwright获取微博Cookie
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[错误] Playwright未安装,请运行: pip install playwright")
        print("       并安装浏览器: playwright install chromium")
        sys.exit(1)
    
    print("\n[INFO] 正在启动Playwright浏览器...")
    
    with sync_playwright() as p:
        # 启动Chromium浏览器 (无头=False,可以看到浏览器界面)
        browser = p.chromium.launch(
            headless=False,  # 显示浏览器窗口
            args=['--disable-blink-features=AutomationControlled']  # 隐藏自动化特征
        )
        
        # 创建新页面
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 720}
        )
        
        page = context.new_page()
        
        # 打开微博登录页
        print("[INFO] 正在打开微博登录页面...")
        page.goto('https://login.sina.com.cn/signup/signin.php', timeout=30000)
        
        # 等待用户登录
        print("\n" + "="*50)
        print("【请在浏览器中登录微博】")
        print("登录成功后,脚本将自动保存Cookie")
        print("="*50 + "\n")
        
        # 等待用户点击登录成功后的元素或检测URL变化
        try:
            # 等待URL变成登录后的状态 或 等待特定元素出现
            page.wait_for_url(lambda url: 'weibo.com' in url or 'my.sina.com.cn' in url or 'weibo.cn' in url, timeout=300000)
            print("[INFO] 检测到登录成功,正在保存Cookie...")
        except Exception:
            # 超时等待,提示用户手动确认
            print("[提示] 等待超时,请在登录后按回车继续...")
            input()
        
        # 获取所有Cookie
        cookies = context.cookies()
        
        # 保存Cookie
        save_cookies_to_file(cookies, "weibo_cookies.json")
        
        # 关闭浏览器
        browser.close()
        
        print("\n[✓] Playwright方式Cookie获取完成!")


# ==================== Selenium 方式 ====================

def get_cookies_with_selenium():
    """
    使用Selenium获取微博Cookie
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        print("[错误] Selenium未安装,请运行: pip install selenium webdriver-manager")
        sys.exit(1)
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError:
        print("[错误] webdriver-manager未安装,请运行: pip install webdriver-manager")
        sys.exit(1)
    
    print("\n[INFO] 正在启动Selenium浏览器...")
    
    # 配置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    try:
        # 自动下载并设置ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"[错误] 启动Chrome失败: {e}")
        print("       请确保已安装Chrome浏览器")
        sys.exit(1)
    
    try:
        # 打开微博登录页
        print("[INFO] 正在打开微博登录页面...")
        driver.get('https://login.sina.com.cn/signup/signin.php')
        
        # 等待用户登录
        print("\n" + "="*50)
        print("【请在浏览器中登录微博】")
        print("登录成功后,脚本将自动保存Cookie")
        print("="*50 + "\n")
        
        # 等待用户登录成功 (检测URL变化)
        WebDriverWait(driver, 300).until(
            lambda d: 'weibo.com' in d.current_url or 'my.sina.com.cn' in d.current_url
        )
        
        print("[INFO] 检测到登录成功,正在保存Cookie...")
        
        # 获取所有Cookie
        cookies = driver.get_cookies()
        
        # 保存Cookie
        save_cookies_to_file(cookies, "weibo_cookies.json")
        
    except Exception as e:
        print(f"[错误] 获取Cookie失败: {e}")
        raise
    finally:
        # 关闭浏览器
        driver.quit()
    
    print("\n[✓] Selenium方式Cookie获取完成!")


# ==================== 主程序入口 ====================

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='微博Cookie获取工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python get_cookies.py                    # 交互式选择
  python get_cookies.py --playwright       # 使用Playwright
  python get_cookies.py --selenium         # 使用Selenium
  python get_cookies.py -l                 # 加载已有Cookie
  python get_cookies.py -h                 # 显示帮助
        """
    )
    
    parser.add_argument('--playwright', '-p', action='store_true', 
                        help='使用Playwright方式获取Cookie')
    parser.add_argument('--selenium', '-s', action='store_true', 
                        help='使用Selenium方式获取Cookie')
    parser.add_argument('--load', '-l', action='store_true', 
                        help='加载已保存的Cookie并显示')
    parser.add_argument('--filename', '-f', default='weibo_cookies.json',
                        help='Cookie文件名 (默认: weibo_cookies.json)')
    parser.add_argument('--usage', '-u', action='store_true',
                        help='显示详细使用说明')
    
    args = parser.parse_args()
    
    # 显示使用说明
    if args.usage:
        print_usage()
        return
    
    # 加载已有Cookie
    if args.load:
        try:
            cookies = load_cookies_from_file(args.filename)
            print("\nCookie内容预览:")
            for i, cookie in enumerate(cookies[:5], 1):  # 只显示前5条
                print(f"  {i}. {cookie.get('name', 'N/A')}: {cookie.get('value', 'N/A')[:20]}...")
            if len(cookies) > 5:
                print(f"  ... 共 {len(cookies)} 条")
        except Exception as e:
            print(f"[错误] {e}")
        return
    
    # 选择获取方式
    if args.playwright:
        get_cookies_with_playwright()
    elif args.selenium:
        get_cookies_with_selenium()
    else:
        # 交互式选择
        print("\n请选择获取方式:")
        print("  1. Playwright (推荐,更稳定)")
        print("  2. Selenium")
        print("  3. 退出")
        
        choice = input("\n请输入选项 (1/2/3): ").strip()
        
        if choice == '1':
            get_cookies_with_playwright()
        elif choice == '2':
            get_cookies_with_selenium()
        elif choice == '3':
            print("已退出")
            sys.exit(0)
        else:
            print("[错误] 无效选项")
            sys.exit(1)


if __name__ == '__main__':
    main()
