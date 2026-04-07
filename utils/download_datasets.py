import urllib.request
import zipfile
import os

datasets = [
    ("https://github.com/USTC-ICLab/Chinese-Multiplatform-Rumor-Dataset/archive/refs/heads/main.zip", "cmr_dataset.zip"),
    ("https://github.com/wdm2020/COVID19-Rumor-Dataset/archive/refs/heads/master.zip", "covid_rumor.zip"),
]

for url, filename in datasets:
    output = f"E:\\rumor_detection\\data\\{filename}"
    print(f"下载: {url}")
    print(f"到: {output}")
    try:
        urllib.request.urlretrieve(url, output)
        print(f"完成: {filename}")
    except Exception as e:
        print(f"失败: {e}")
    print()
