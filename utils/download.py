import urllib.request
import zipfile
import os

url = "https://github.com/thunlp/Chinese_Rumor_Dataset/archive/refs/heads/master.zip"
output = r"E:\rumor_detection\data\chinese_rumor.zip"

print(f"下载中: {url}")

urllib.request.urlretrieve(url, output)

print(f"解压中: {output}")

with zipfile.ZipFile(output, 'r') as zip_ref:
    zip_ref.extractall(r"E:\rumor_detection\data")

print("完成!")
