import re
import cloudscraper
import requests
from urllib.parse import urlparse

# --- Configuration & Headers ---
scraper = cloudscraper.create_scraper()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
}

# ============================================================
#  Helpers
# ============================================================
def _to_base_n(num, base):
    if num == 0: return '0'
    chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    res = ''
    while num > 0:
        res = chars[num % base] + res
        num //= base
    return res

def _decode_pack(p, a, c, k_str):
    k_list = k_str.split('|')
    for i in range(c - 1, -1, -1):
        if i < len(k_list) and k_list[i]:
            alias = _to_base_n(i, a)
            p = re.sub(r'\b' + re.escape(alias) + r'\b', k_list[i], p)
    return p

# ============================================================
#  Resolvers
# ============================================================

def resolve_sibnet(url):
    """
    Sibnet resolver. If direct extraction fails (403), returns original URL 
    as it's currently handled by the user's frontend/backend.
    """
    try:
        r = scraper.get(url, headers={**HEADERS, "Referer": "https://video.sibnet.ru/"}, timeout=10)
        if r.status_code == 200:
            match = re.search(r'src:\s*["\'](/v/[^"\']+)["\']', r.text)
            if match:
                return {"url": "https://video.sibnet.ru" + match.group(1), "type": "mp4"}
    except:
        pass
    return {"url": url, "type": "embed"} # Fallback to original embed URL

def resolve_vidmoly(url):
    """
    Vidmoly resolver. Tries .net domain which often bypasses bot walls better.
    Supports JS redirection.
    """
    # Force .net instead of .to if matching
    url_net = url.replace("vidmoly.to", "vidmoly.net")
    try:
        r = scraper.get(url_net, headers={**HEADERS, "Referer": url_net}, timeout=10)
        
        # Follow JS redirect if present
        redirect_match = re.search(r"window\.location\.replace\('([^']+)'\)", r.text)
        if redirect_match:
            r = scraper.get(redirect_match.group(1), headers={**HEADERS, "Referer": url_net}, timeout=10)
            
        # Regex for m3u8 (supports both single and double quotes)
        match = re.search(r'file\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', r.text)
        if match:
            return {"url": match.group(1), "type": "m3u8"}
    except:
        pass
    return None

def resolve_smoothpre(url):
    """
    SmoothPre/VidHide/StreamWish resolver. Decodes P.A.C.K. JavaScript to find m3u8.
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    try:
        r = scraper.get(url, headers={**HEADERS, "Referer": base_url + "/"}, timeout=10)
        eval_match = re.search(r"eval\(function\(p,a,c,k,e,d\)\{.*?\}\('(.*?)',(\d+),(\d+),'(.*?)'\.split\('\|'\)\)\)", r.text, re.DOTALL)
        if eval_match:
            decoded = _decode_pack(eval_match.group(1), int(eval_match.group(2)), int(eval_match.group(3)), eval_match.group(4))
            for key in ['hls4', 'hls3', 'hls2']:
                m = re.search(f'"{key}"\\s*:\\s*"(.*?)"', decoded)
                if m:
                    target_url = m.group(1).replace('\\', '')
                    if target_url.startswith("/"): target_url = base_url + target_url
                    return {"url": target_url, "type": "m3u8"}
    except:
        pass
    return None

def resolve_sendvid(url):
    """
    SendVid resolver. Extracts MP4 URL from <source> or og:video.
    """
    try:
        r = scraper.get(url, headers={**HEADERS, "Referer": "https://sendvid.com/"}, timeout=10)
        # Match <source src="..."> or property="og:video" content="..."
        match = re.search(r'<source\s+src="([^"]+\.mp4[^"]*)"', r.text)
        if not match:
             match = re.search(r'property="og:video"\s+content="([^"]+)"', r.text)
        if not match:
             match = re.search(r'property="og:video:url"\s+content="([^"]+)"', r.text)
             
        if match:
            video_url = match.group(1)
            if video_url.startswith("//"): video_url = "https:" + video_url
            return {"url": video_url, "type": "mp4"}
    except:
        pass
    return None

# ============================================================
#  Dispatcher
# ============================================================

RESOLVER_MAP = {
    "video.sibnet.ru": resolve_sibnet,
    "sibnet.ru": resolve_sibnet,
    "vidmoly.to": resolve_vidmoly,
    "vidmoly.net": resolve_vidmoly,
    "smoothpre.com": resolve_smoothpre,
    "vidhide.com": resolve_smoothpre,
    "streamwish.com": resolve_smoothpre,
    "sendvid.com": resolve_sendvid,
}

def resolve_video_url(url):
    """
    Resolves a video embed URL to a direct link (mp4/m3u8) or returns original if failed.
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")
    resolver = RESOLVER_MAP.get(domain)
    if resolver:
        return resolver(url)
    return {"url": url, "type": "raw"}
