# -*- coding: utf-8 -*-
"""数据集导入工具 - 将下载的数据集导入到项目"""
import os
import json
import zipfile
import tarfile
from pathlib import Path
import shutil

DATA_DIR = Path("E:/rumor_detection/data")

def import_zip(zip_path, extract_to=None):
    """解压并导入ZIP文件"""
    if extract_to is None:
        extract_to = DATA_DIR
    
    print(f"解压: {zip_path}")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"完成: {zip_path}")
    except Exception as e:
        print(f"失败: {e}")

def import_tar(tar_path, extract_to=None):
    """解压并导入TAR文件"""
    if extract_to is None:
        extract_to = DATA_DIR
    
    print(f"解压: {tar_path}")
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            tar.extractall(extract_to)
        print(f"完成: {tar_path}")
    except Exception as e:
        print(f"失败: {e}")

def import_json(json_path, target_name=None):
    """导入JSON文件"""
    if target_name is None:
        target_name = Path(json_path).name
    
    target = DATA_DIR / target_name
    
    print(f"复制: {json_path} -> {target}")
    try:
        shutil.copy2(json_path, target)
        print(f"完成: {target}")
    except Exception as e:
        print(f"失败: {e}")

def scan_and_import():
    """扫描下载目录并自动导入"""
    download_dir = Path("D:/下载")  # 中文路径
    
    if not download_dir.exists():
        download_dir = Path("D:/Download")
    
    print(f"扫描目录: {download_dir}")
    print("="*50)
    
    if not download_dir.exists():
        print("下载目录不存在!")
        return
    
    # 扫描文件
    for f in download_dir.iterdir():
        if f.is_file():
            print(f"\n发现: {f.name}")
            
            if f.suffix == '.zip':
                import_zip(f)
            elif f.suffix in ['.tar', '.gz', '.bz2']:
                import_tar(f)
            elif f.suffix == '.json':
                import_json(f)
            elif f.suffix == '.tsv':
                target = DATA_DIR / f.name
                shutil.copy2(f, target)
                print(f"复制: {f.name}")
    
    print("\n" + "="*50)
    print("导入完成! 数据目录内容:")
    for f in DATA_DIR.iterdir():
        print(f"  {f.name}")

if __name__ == "__main__":
    scan_and_import()
