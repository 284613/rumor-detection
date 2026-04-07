# -*- coding: utf-8 -*-
"""数据集下载脚本"""
import urllib.request
import zipfile
import os
from pathlib import Path

DATA_DIR = Path("E:/rumor_detection/data")

datasets = [
    # LIAR数据集
    ("https://www.cs.ucsb.edu/~william/data/liar_dataset.zip", "liar_dataset.zip"),
    # 清华微博谣言数据集
    ("https://github.com/thunlp/Chinese_Rumor_Dataset/archive/refs/heads/master.zip", "Chinese_Rumor_Dataset.zip"),
]

for url, filename in datasets:
    output = DATA_DIR / filename
    print(f"\n下载: {url.split('/')[-1]}")
    print(f"到: {output}")
    
    try:
        # 添加User-Agent
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 下载
        urllib.request.urlretrieve(req, output)
        print(f"下载完成!")
        
        # 解压
        if filename.endswith('.zip'):
            print(f"解压: {filename}")
            with zipfile.ZipFile(output, 'r') as zip_ref:
                zip_ref.extractall(DATA_DIR)
            print(f"解压完成!")
            
    except Exception as e:
        print(f"失败: {e}")

print("\n完成!")
