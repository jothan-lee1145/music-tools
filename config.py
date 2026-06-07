import requests
import os

API_BASE = "https://music-api.gdstudio.xyz/api.php"

STABLE_SOURCES = {
    "网易云音乐 (netease)": "netease",
    "酷我音乐 (kuwo)": "kuwo",
    "JOOX音乐 (joox)": "joox"
}

QUALITY_MAP = {
    "标准音质 (128kbps)": "128",
    "极高音质 (320kbps)": "320",
    "无损音质 (FLAC)": "740",
    " Hi-Res无损 (24bit)": "999"
}

REGIONS = {
    "🇨🇳 中国大陆 (CN)": "CN", "🇺🇸 美国 (US)": "US", "🇵 日本 (JP)": "JP",
    "🇹🇼 中国台湾 (TW)": "TW", "🇭 中国香港 (HK)": "HK", "🇷 韩国 (KR)": "KR"
}

# 共享网络会话
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, audio/*, */*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://music.163.com/'
})

def setup_proxy():
    http_p = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_p = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    proxy_url = https_p or http_p
    if proxy_url:
        session.proxies.update({'http': proxy_url, 'https': proxy_url})
        return f"代理已启用: {proxy_url}"
    return "直连模式"