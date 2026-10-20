import re
import requests
import cloudscraper # type: ignore
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor

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

def resolve_vidmoly(url, session=None):
    """
    Vidmoly resolver. Tries .net domain which often bypasses bot walls better.
    Supports JS redirection.
    """
    s = session or scraper
    url_net = url.replace("vidmoly.to", "vidmoly.net")
    try:
        r = s.get(url_net, headers={**HEADERS, "Referer": url_net}, timeout=8)
        if r.status_code not in (200, 206):
            return None
        
        redirect_match = re.search(r"window\.location\.replace\('([^']+)'\)", r.text)
        if redirect_match:
            r = s.get(redirect_match.group(1), headers={**HEADERS, "Referer": url_net}, timeout=8)
            if r.status_code not in (200, 206):
                return None
            
        match = re.search(r'file\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', r.text)
        if match:
            return {"url": match.group(1).strip(), "type": "m3u8"}
    except Exception:
        pass
    return None

def resolve_smoothpre(url, session=None):
    """
    SmoothPre/VidHide/StreamWish resolver. Decodes P.A.C.K. JavaScript to find m3u8.
    """
    s = session or scraper
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    try:
        r = s.get(url, headers={**HEADERS, "Referer": base_url + "/"}, timeout=8)
        if r.status_code not in (200, 206):
            return None
        eval_match = re.search(r"eval\(function\(p,a,c,k,e,d\)\{.*?\}\('(.*?)',(\d+),(\d+),'(.*?)'\.split\('\|'\)\)\)", r.text, re.DOTALL)
        if eval_match:
            decoded = _decode_pack(eval_match.group(1), int(eval_match.group(2)), int(eval_match.group(3)), eval_match.group(4))
            for key in ['hls4', 'hls3', 'hls2']:
                m = re.search(f'"{key}"\\s*:\\s*"(.*?)"', decoded)
                if m:
                    target_url = m.group(1).replace('\\', '')
                    if target_url.startswith("/"):
                        target_url = base_url + target_url
                    return {"url": target_url, "type": "m3u8"}
    except Exception:
        pass
    return None

def resolve_sendvid(url, session=None):
    """
    SendVid resolver. Extracts MP4 URL from <source> or og:video.
    """
    s = session or scraper
    try:
        r = s.get(url, headers={**HEADERS, "Referer": "https://sendvid.com/"}, timeout=8)
        if r.status_code not in (200, 206):
            return None
        match = re.search(r'<source\s+src="([^"]+\.mp4[^"]*)"', r.text)
        if not match:
            match = re.search(r'property="og:video"\s+content="([^"]+)"', r.text)
        if not match:
            match = re.search(r'property="og:video:url"\s+content="([^"]+)"', r.text)
             
        if match:
            video_url = match.group(1)
            if video_url.startswith("//"):
                video_url = "https:" + video_url
            return {"url": video_url, "type": "mp4"}
    except Exception:
        pass
    return None

def resolve_ansembed(url, session=None):
    """
    Ansembed / Movembed resolver. Extracts m3u8 playlist URL directly from player page.
    """
    s = session or scraper
    try:
        r = s.get(url, headers={**HEADERS, "Referer": url}, timeout=8)
        if r.status_code not in (200, 206):
            return None
        match = re.search(r'file\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', r.text)
        if not match:
            match = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', r.text)
        if match:
            return {"url": match.group(1).strip(), "type": "m3u8"}
    except Exception:
        pass
    return None

def resolve_embed4me(url, session=None):
    """
    Embed4me / Lplayer resolver. Tente d'extraire le m3u8 depuis la page du player.
    """
    s = session or scraper
    try:
        r = s.get(url, headers={**HEADERS, "Referer": url}, timeout=8)
        if r.status_code not in (200, 206):
            return None
        match = re.search(r'file\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', r.text)
        if not match:
            match = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', r.text)
        if match:
            return {"url": match.group(1).strip(), "type": "m3u8"}
    except Exception:
        pass
    return {"url": url, "type": "embed"}

def check_stream_health(resolved_stream, session=None):
    """
    Vérifie l'intégrité et la disponibilité du flux vidéo résolu.
    Retourne (error_score, is_healthy):
    - error_score == 0: flux vérifié et actif (m3u8 valide avec #EXTM3U ou MP4 direct accessible).
    - error_score == 1: flux potentiellement valide mais lent à répondre (timeout/connexion lente).
    - error_score >= 999: flux définitivement mort (404, 410, fichier supprimé, page d'erreur HTML).
    """
    if not resolved_stream or not isinstance(resolved_stream, dict):
        return (999, False)

    url = resolved_stream.get("url")
    stream_type = resolved_stream.get("type", "")

    if not url:
        return (999, False)

    s = session or scraper
    parsed = urlparse(url)
    referer = f"{parsed.scheme}://{parsed.netloc}/"
    req_headers = {**HEADERS, "Referer": referer}

    try:
        if stream_type == "m3u8" or ".m3u8" in url:
            # Requête légère sur le fichier m3u8 pour valider les balises HLS
            r = s.get(url, headers=req_headers, timeout=6)
            if r.status_code in (404, 410, 403, 502, 503):
                return (999, False)
            
            content_type = r.headers.get("Content-Type", "").lower()
            text_start = r.text[:300] if r.text else ""
            
            # Détection d'erreurs explicites (fichier supprimé ou page HTML d'erreur)
            if "html" in content_type or "<html" in text_start.lower():
                if any(err in text_start.lower() for err in ["file deleted", "not found", "404", "access denied", "blocked"]):
                    return (999, False)
            
            if "#EXTM3U" in text_start or "#EXT-X-" in text_start:
                return (0, True)
            
            # Si le status est 200/206 mais sans balise évidente (proxy ou playlist dynamique)
            if r.status_code in (200, 206):
                return (1, True)
            return (999, False)

        elif stream_type == "mp4" or ".mp4" in url:
            r = s.get(url, headers={**req_headers, "Range": "bytes=0-1024"}, timeout=6, stream=True)
            if r.status_code in (404, 410, 403, 502, 503):
                return (999, False)
            
            content_type = r.headers.get("Content-Type", "").lower()
            if "html" in content_type:
                return (999, False)
            
            if r.status_code in (200, 206):
                return (0, True)
            return (999, False)

        elif stream_type in ("embed", "raw"):
            return (1, True)

    except (requests.exceptions.RequestException, Exception):
        # Ne PAS rejeter un épisode si la connexion est lente ou si le serveur met du temps à répondre
        return (1, True)

    return (1, True)

# ============================================================
#  Dispatcher
# ============================================================

RESOLVER_MAP = {
    "ansembed.net": resolve_ansembed,
    "ansembed.com": resolve_ansembed,
    "lpayer.embed4me.com": resolve_embed4me,
    "embed4me.com": resolve_embed4me,
    "player.embed4me.com": resolve_embed4me,
    "vidmoly.to": resolve_vidmoly,
    "vidmoly.net": resolve_vidmoly,
    "vidmoly.me": resolve_vidmoly,
    "smoothpre.com": resolve_smoothpre,
    "vidhide.com": resolve_smoothpre,
    "vidhidepro.com": resolve_smoothpre,
    "streamwish.com": resolve_smoothpre,
    "streamwish.to": resolve_smoothpre,
    "sendvid.com": resolve_sendvid,
}

def resolve_video_url(url, session=None):
    """
    Resolves a video embed URL to a direct link (mp4/m3u8) or returns original if failed.
    """
    if not url:
        return None
    url = url.strip()
    if re.search(r'\.m3u8(\?|$)', url, re.IGNORECASE):
        return {"url": url, "type": "m3u8"}
    if re.search(r'\.mp4(\?|$)', url, re.IGNORECASE):
        return {"url": url, "type": "mp4"}

    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")
    resolver = RESOLVER_MAP.get(domain)
    if resolver:
        return resolver(url, session=session)
    return {"url": url, "type": "raw"}
