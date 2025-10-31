import yt_dlp, os, requests
from bs4 import BeautifulSoup
PATH = os.path.dirname(os.path.abspath(__file__))
PATH_DOWNLOAD = os.path.join(PATH, "Dist")
os.makedirs(PATH_DOWNLOAD, exist_ok=True)
# AJOUTER option pour les saison affin quel sois trier au même titre qu'il faut gerer le nom de l'animer que l'on télécharge

headers_sendvid = {
    "accept": "text/css,*/*;q=0.1",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6,de;q=0.5,zh-CN;q=0.4,zh;q=0.3,ru;q=0.2,es;q=0.1,ko;q=0.1,vi;q=0.1,pl;q=0.1",
    "cache-control": "no-cache",
    "connection": "keep-alive",
    "host": "sendvid.com",
    "pragma": "no-cache",
    "referer": "https://sendvid.com/embed/xxqt63nz",
    "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Opera GX";v="122"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "style",
    "sec-fetch-mode": "no-cors",
    "sec-fetch-site": "same-origin",
    "sec-fetch-storage-access": "active",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 OPR/122.0.0.0"
}

def extract_and_download_sendvid(embed_url, output_path):
    """Extrait et télécharge la vidéo depuis Sendvid"""
    
    # 1. Extraire l'URL directe
    r = requests.get(embed_url, headers=headers_sendvid)
    soup = BeautifulSoup(r.text, "html.parser")
    video_tag = soup.find("source")
    
    if not video_tag or not video_tag.get("src"):
        raise Exception("Impossible de trouver le lien direct Sendvid.")
    
    direct_url = video_tag["src"]
    print(f"URL directe trouvée: {direct_url}")
    
    # 2. Extraire le nom de fichier
    video_id = embed_url.split("/")[-1]
    filename = f"{video_id}.mp4"
    filepath = os.path.join(output_path, filename)
    
    # 3. Télécharger avec requests
    print(f"Téléchargement en cours...")
    response = requests.get(direct_url, headers=headers_sendvid, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0
    
    with open(filepath, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"\rProgress: {percent:.1f}%", end='', flush=True)
    
    print(f"\n✓ Téléchargement terminé: {filepath}")
    return filepath
    
url = "https://sendvid.com/embed/xxqt63nz"
try:
    extract_and_download_sendvid(url, PATH_DOWNLOAD)
except Exception as e:
    print(f"Erreur: {e}")
