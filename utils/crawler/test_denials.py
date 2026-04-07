# -*- coding: utf-8 -*-
"""测试辟谣账号API"""
import requests
import json
import time

# 读取Cookie
with open('E:\\rumor_detection\\utils\\crawler\\weibo_cookies.json', 'r') as f:
    cookies = json.load(f)

# 转换为Cookie字符串
cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in cookies])

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Cookie': cookie_str,
    'Referer': 'https://weibo.com/',
    'X-Requested-With': 'XMLHttpRequest'
}

# 微博辟谣账号UID
account_uid = "5869998085"

# 使用用户微博接口
url = "https://weibo.com/ajax/statuses/mymblog"
params = {
    "uid": account_uid,
    "feature": 0,
    "is_all": 1,
    "is_search": 0,
    "visible": 0,
    "page": 1,
    "page_size": 20,
    "basetime": int(time.time())
}

resp = requests.get(url, headers=headers, params=params)
print('Status:', resp.status_code)
print('URL:', resp.url)
data = resp.json()
print('Response:', json.dumps(data, ensure_ascii=False, indent=2)[:500])
