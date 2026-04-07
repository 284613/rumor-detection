# -*- coding: utf-8 -*-
"""测试微博API"""
import requests
import json

# 读取Cookie
with open('E:\\rumor_detection\\utils\\crawler\\weibo_cookies.json', 'r') as f:
    cookies = json.load(f)

# 转换为Cookie字符串
cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in cookies])

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Cookie': cookie_str,
    'Referer': 'https://weibo.com/'
}

resp = requests.get('https://weibo.com/ajax/side/hotSearch', headers=headers)
print('Status:', resp.status_code)
data = resp.json()
if data.get('ok') == 1:
    print('成功! 获取到', len(data.get('data', {}).get('realtime', [])), '条热门话题')
    for i, item in enumerate(data['data']['realtime'][:5]):
        print(f"{i+1}. {item.get('word')} - 热度:{item.get('num')}")
else:
    print('失败:', data)
