import re
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

def resolve_vidmoly(url):
    """
    Vidmoly resolver. Tries .net domain which often bypasses bot walls better.
    Supports JS redirection.
    """
    # Force .net instead of .to if matching
    url_net = url.replace("vidmoly.to", "vidmoly.net")
    try:
        r = scraper.get(url_net, headers={**HEADERS, "Referer": url_net}, timeout=10)
        if r.status_code not in (200, 206):
            return None
        
        # Follow JS redirect if present
        redirect_match = re.search(r"window\.location\.replace\('([^']+)'\)", r.text)
        if redirect_match:
            r = scraper.get(redirect_match.group(1), headers={**HEADERS, "Referer": url_net}, timeout=10)
            if r.status_code not in (200, 206):
                return None
            
        # Regex for m3u8 (supports both single and double quotes)
        match = re.search(r'file\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', r.text)
        if match:
            return {"url": match.group(1).strip(), "type": "m3u8"}
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
        if r.status_code not in (200, 206):
            return None
        eval_match = re.search(r"eval\(function\(p,a,c,k,e,d\)\{.*?\}\('(.*?)',(\d+),(\d+),'(.*?)'\.split\('\|'\)\)\)", r.text, re.DOTALL)
        if eval_match:
            decoded = _decode_pack(eval_match.group(1), int(eval_match.group(2)), int(eval_match.group(3)), eval_match.group(4))
            for key in ['hls4', 'hls3', 'hls2']:
                m = re.search(f'"{key}"\\s*:\\s*"(.*?)"', decoded)
                if m:
                    target_url = m.group(1).replace('\\', '')
                    if target_url.startswith("/"): target_url = base_url + target_url
                    try:
                        chk = scraper.get(target_url, headers={**HEADERS, "Referer": base_url + "/"}, timeout=3, stream=True)
                        if chk.status_code in (200, 206):
                            return {"url": target_url, "type": "m3u8"}
                    except:
                        pass
    except:
        pass
    return None

def resolve_sendvid(url):
    """
    SendVid resolver. Extracts MP4 URL from <source> or og:video.
    Returns None if content is unavailable (4xx/5xx).
    """
    try:
        r = scraper.get(url, headers={**HEADERS, "Referer": "https://sendvid.com/"}, timeout=10)
        if r.status_code not in (200, 206):
            return None  # Contenu supprimé ou inaccessible
        # Match <source src="..."> or property="og:video" content="..."
        match = re.search(r'<source\s+src="([^"]+\.mp4[^"]*)"', r.text)
        if not match:
             match = re.search(r'property="og:video"\s+content="([^"]+)"', r.text)
        if not match:
             match = re.search(r'property="og:video:url"\s+content="([^"]+)"', r.text)
             
        if match:
            video_url = match.group(1)
            if video_url.startswith("//"): video_url = "https:" + video_url
            try:
                chk = scraper.get(video_url, headers={**HEADERS, "Referer": "https://sendvid.com/"}, timeout=3, stream=True)
                if chk.status_code in (200, 206):
                    return {"url": video_url, "type": "mp4"}
            except:
                pass
    except:
        pass
    return None

def resolve_ansembed(url):
    """
    Ansembed / Movembed resolver. Extracts m3u8 playlist URL from player page.
    """
    try:
        r = scraper.get(url, headers={**HEADERS, "Referer": url}, timeout=10)
        if r.status_code not in (200, 206):
            return None
        match = re.search(r'file\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', r.text)
        if not match:
            match = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', r.text)
        if match:
            m3u8_url = match.group(1).strip()
            try:
                chk = scraper.get(m3u8_url, headers={**HEADERS, "Referer": url}, timeout=3, stream=True)
                if chk.status_code in (200, 206):
                    return {"url": m3u8_url, "type": "m3u8"}
            except:
                pass
    except:
        pass
    return None

def resolve_embed4me(url):
    """
    Embed4me / Lplayer resolver. Tente d'extraire le m3u8 depuis la page du player.
    Retourne l'URL embed en fallback si l'extraction échoue.
    """
    try:
        r = scraper.get(url, headers={**HEADERS, "Referer": url}, timeout=10)
        if r.status_code not in (200, 206):
            return None
        match = re.search(r'file\s*:\s*["\']( https?://[^"\']+\.m3u8[^"\']*)["\']', r.text)
        if not match:
            match = re.search(r'["\']( https?://[^"\']+\.m3u8[^"\']*)["\']', r.text)
        if match:
            return {"url": match.group(1).strip(), "type": "m3u8"}
    except:
        pass
    return {"url": url, "type": "embed"}

# ============================================================
#  Stream Health & Integrity Checkers
# ============================================================


def check_m3u8_health(m3u8_url, referer=None, num_samples=10):
    """
    Vérifie l'intégrité complète d'un stream HLS m3u8 :
    - Présence de #EXTM3U et sous-playlists (master playlist)
    - Présence du tag de fin de vidéo (#EXT-X-ENDLIST)
    - Test de disponibilité en parallèle sur un échantillon de segments répartis sur tout le fichier
    Retourne (error_count, is_complete). error_count == 0 => stream 100% complet et fonctionnel.
    """
    req_headers = {**HEADERS}
    if referer:
        req_headers['Referer'] = referer
    else:
        p = urlparse(m3u8_url)
        req_headers['Referer'] = f"{p.scheme}://{p.netloc}/"

    try:
        r = scraper.get(m3u8_url, headers=req_headers, timeout=4)
        if r.status_code != 200 or not r.text or "html" in r.headers.get("Content-Type", "").lower():
            return (999, False)

        text = r.text
        if not text.startswith("#EXTM3U") and "#EXTM3U" not in text[:50]:
            return (999, False)

        # Si master playlist avec variantes de résolutions
        if "#EXT-X-STREAM-INF" in text:
            sub_matches = re.findall(r'^(?!#)(.+)$', text, re.MULTILINE)
            if not sub_matches:
                return (999, False)
            sub_url = sub_matches[0].strip()
            full_sub_url = urljoin(m3u8_url, sub_url)
            return check_m3u8_health(full_sub_url, referer=req_headers['Referer'], num_samples=num_samples)

        has_endlist = "#EXT-X-ENDLIST" in text
        segments = [
            urljoin(m3u8_url, line.strip())
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

        if not segments:
            return (999, False)

        total_segs = len(segments)
        step = max(1, (total_segs - 1) // (num_samples - 1)) if total_segs > num_samples else 1
        sample_indices = sorted(list({min(total_segs - 1, i * step) for i in range(num_samples)}))

        def test_segment(idx):
            seg_url = segments[idx]
            try:
                res = scraper.get(seg_url, headers={**req_headers, 'Range': 'bytes=0-1024'}, timeout=2.5, stream=True)
                if res.status_code in (200, 206) and "html" not in res.headers.get("Content-Type", "").lower():
                    return True
            except Exception:
                pass
            return False

        with ThreadPoolExecutor(max_workers=min(len(sample_indices), 8)) as pool:
            results = list(pool.map(test_segment, sample_indices))

        errors = results.count(False)
        if not has_endlist:
            errors += 2  # Pénalité si le tag de fin de vidéo manque

        return (errors, errors == 0 and has_endlist)
    except Exception:
        return (999, False)

def check_mp4_health(mp4_url, referer=None):
    """
    Vérifie l'intégrité d'un flux MP4 direct :
    - Support des requêtes partielles (Range)
    - Taille minimale (> 5 Mo)
    - Accessibilité du début et de la fin du fichier
    """
    req_headers = {**HEADERS}
    if referer:
        req_headers['Referer'] = referer
    else:
        p = urlparse(mp4_url)
        req_headers['Referer'] = f"{p.scheme}://{p.netloc}/"

    try:
        res = scraper.get(mp4_url, headers={**req_headers, 'Range': 'bytes=0-1024'}, timeout=3, stream=True)
        if res.status_code not in (200, 206) or "html" in res.headers.get("Content-Type", "").lower():
            return (999, False)

        content_range = res.headers.get("Content-Range", "")
        content_length = res.headers.get("Content-Length", "0")
        total_size = 0

        if "/" in content_range:
            try:
                total_size = int(content_range.split("/")[-1])
            except ValueError:
                pass
        elif content_length:
            try:
                total_size = int(content_length)
            except ValueError:
                pass

        if total_size > 0 and total_size < 5 * 1024 * 1024:
            return (5, False)

        if total_size > 2048:
            end_range = f"bytes={total_size - 2048}-{total_size - 1}"
            res_end = scraper.get(mp4_url, headers={**req_headers, 'Range': end_range}, timeout=3, stream=True)
            if res_end.status_code not in (200, 206):
                return (2, False)

        return (0, True)
    except Exception:
        return (999, False)

def check_stream_health(resolved_stream):
    """
    Évalue la santé et la complétude du stream vidéo résolu.
    Retourne (error_score, is_complete).
    error_score == 0 signifie stream 100% complet et fonctionnel sans erreur.
    Plus le score est bas, meilleur est le flux.
    """
    if not resolved_stream or not isinstance(resolved_stream, dict):
        return (9999, False)

    url = resolved_stream.get("url")
    stream_type = resolved_stream.get("type")

    if not url:
        return (9999, False)

    if stream_type == "m3u8" or ".m3u8" in url:
        return check_m3u8_health(url)
    elif stream_type == "mp4" or ".mp4" in url:
        return check_mp4_health(url)
    elif stream_type in ("embed", "raw"):
        try:
            r = scraper.get(url, timeout=3)
            if r.status_code == 200 and "html" not in r.headers.get("Content-Type", "").lower():
                return (20, False)
            elif r.status_code == 200:
                # Embed HTML de lecteur valide
                return (30, False)
        except Exception:
            pass
        return (9999, False)

    return (9999, False)

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


def resolve_video_url(url):
    """
    Resolves a video embed URL to a direct link (mp4/m3u8) or returns original if failed.
    """
    if not url:
        return None
    if re.search(r'\.m3u8(\?|$)', url, re.IGNORECASE):
        return {"url": url, "type": "m3u8"}
    if re.search(r'\.mp4(\?|$)', url, re.IGNORECASE):
        return {"url": url, "type": "mp4"}

    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")
    resolver = RESOLVER_MAP.get(domain)
    if resolver:
        return resolver(url)
    return {"url": url, "type": "raw"}
