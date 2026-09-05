import requests
import json, os, re, cloudscraper, requests, unicodedata
from rapidfuzz import process, fuzz
from bs4 import BeautifulSoup

try :
    from .utils.resolvers import resolve_video_url
    from .utils.config import Config
    from .utils.utils import Utils
except ImportError:
    from src.utils.resolvers import resolve_video_url
    from src.utils.config import Config
    from src.utils.utils import Utils

PATH = os.path.dirname(os.path.abspath(__file__))
PATH_DIR = os.path.join(PATH, "data", "json")
PATH_ANIME = os.path.join(PATH_DIR, "AnimeInfo.json")
BASE_URL = Utils.findLink()

headers = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6,de;q=0.5,zh-CN;q=0.4,zh;q=0.3,ru;q=0.2,es;q=0.1,ko;q=0.1,vi;q=0.1,pl;q=0.1",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Host": "bck-1326-ant.vmwesa.online",
    "Origin": "https://vidmoly.net",
    "Pragma": "no-cache",
    "Referer": "https://vidmoly.net/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 OPR/122.0.0.0",
    "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Opera GX";v="122"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

class Cardinal:

    def findLink():
        return {"url": BASE_URL}
        
    def getAllAnime(reset="False"):
        
        data = []
        page = 1

        os.makedirs(PATH_DIR, exist_ok=True) # Verifi l'existance du dossier data/json
        scraper = cloudscraper.create_scraper()  # équivaut à un navigateur

        if os.path.exists(PATH_ANIME) and reset != "True":
            return "Fichier déjà existant. Ajoutez l'argument reset='True' pour tout actualiser."

        first_response = scraper.get(f"{BASE_URL}/catalogue")
        if first_response.status_code != 200:
            return first_response.status_code

        soup_init = BeautifulSoup(first_response.content, 'lxml')
        pagination_links = soup_init.find_all('a', class_=["p-3", "pagination-link", "rounded-md"])

        page_numbers = []
        for link in pagination_links:
            text = link.get_text(strip=True)
            if text.isdigit():  # On vérifie bien que c'est un nombre pur
                page_numbers.append(int(text))

        max_pages = max(page_numbers) if page_numbers else 1
        # print(f"Nombre total de pages détecté : {max_pages}")
        
        for page in range(1, max_pages + 1):
            reponse = scraper.get(f"{BASE_URL}/catalogue/?page={page}")
            # print(reponse.text)
                
            if reponse.status_code != 200:
                return reponse.status_code
            
            source = reponse.content
            soup = BeautifulSoup(source, 'lxml')

            titles = soup.find_all('h2', class_="card-title")

            for title_tag in titles:    
                card_link = title_tag.find_parent('a')

                titre = title_tag.get_text(strip=True)
                link = card_link.get('href')

                img_tag = card_link.find('img', class_="card-image")
                img_src = img_tag.get('src') if img_tag else ""
                            
                # print(titre)
                # print(link)
                            
                data.append({
                    "title" : Cardinal.normalize_title(titre),
                    "link" : link,
                    "cover" : img_src
                })

        with open(PATH_ANIME, "w", encoding='utf-8') as t:
            json.dump(data, t, ensure_ascii=False, indent=2)

        return "Recuperation achever"

    def loadBaseAnimeData():
        if os.path.exists(PATH_ANIME) == True:
            with open(PATH_ANIME, "r", encoding="utf-8") as data:
                anime_data = json.load(data)
                
                if BASE_URL:
                    # Extraire le domaine de BASE_URL (ex: "anime-sama.si")
                    base_domain = BASE_URL.replace("https://", "").replace("http://", "").rstrip("/")
                    
                    # Initialiser la variable AVANT la boucle
                    needs_refresh = False
                    
                    # Vérifier si au moins un lien dans les données utilise un mauvais domaine
                    for anime in anime_data:
                        if "link" in anime:
                            anime_link = anime["link"]
                            # Vérifier si le lien contient le bon domaine
                            if base_domain not in anime_link:
                                needs_refresh = True
                                break  # Un seul suffit pour déclencher l'actualisation complète
                    
                    if needs_refresh:
                        requests.get(f"http://{Config.IP}:{Config.PORT}/api/getAllAnime?r=True")
                
                return anime_data
        else:
            return f"Fichier non existant veuillez request : http://{Config.IP}:{Config.PORT}/api/getAllAnime"
    
    def normalize_title(title):
        if not title:
            return ""

        # Normalize les accents en standards
        title = unicodedata.normalize("NFKD", title)
        title = "".join([c for c in title if not unicodedata.combining(c)])

        # Converti les guillemets spéciaux en guillemets simples
        title = title.replace("“", "\"").replace("”", "\"")
        title = title.replace("‘", "'").replace("’", "'")

        # Remplacer les caractères interdits JSON ou filesystem
        forbidden = r'[\/\\\:\*\?\"\<\>\|]'
        title = re.sub(forbidden, " ", title)

        # Nettoyer les caractères non alphanumériques excessifs
        title = re.sub(r"[^a-zA-Z0-9\-\_\&\.\'\#\s]", " ", title)

        # Réduire espaces multiples
        title = re.sub(r"\s+", " ", title).strip()

        return title
    
    def clean_string(text):
        """Une fonction pour nettoyer et normaliser une chaîne de caractères."""
        if not text:
            return ""
        # Met tout en minuscule
        text = text.lower()
        # Ne garde que les lettres, les chiffres et les espaces
        text = re.sub(r'[^a-z0-9\s]', '', text)
        # Enlève les espaces en trop
        text = re.sub(r'\s+', ' ', text).strip()
        return text
            
    def serchAnime(search, limit):  # Ajouter de quoi afficher sur la liste finale les titres alternatifs s'il y en a
        try:
            # animes_data = requests.get("http://127.0.0.1:5000/api/loadBaseAnimeData").json()
            scraper = cloudscraper.create_scraper()  # équivaut à un navigateur
            animes_data = scraper.get(f"http://{Config.IP}:{Config.PORT}/api/loadBaseAnimeData").json()
        except cloudscraper.exceptions.RequestException as e:
            print(f"Erreur lors de la récupération des animes: {e}")
            return []

        cleaned_search = Cardinal.clean_string(search)  # Utilise directement Cardinal.clean_string
        if not cleaned_search:
            return []

        # Utilisation de dictionnaires pour garantir l'unicité
        cleaned_to_original_map = {Cardinal.clean_string(anime.get("title", "")): anime.get("title") for anime in animes_data if anime.get("title")}
        cleaned_to_id_map = {Cardinal.clean_string(anime.get("title", "")): anime.get("link") for anime in animes_data if anime.get("title")}

        cleaned_to_cover_map = {Cardinal.clean_string(anime.get("title", "")): anime.get("cover") for anime in animes_data if anime.get("title")}
        
        cleaned_titles = list(cleaned_to_original_map.keys())

        # On prend une marge plus large pour avoir assez de matière pour notre tri intelligent
        matches = process.extract(cleaned_search, cleaned_titles, scorer=fuzz.token_set_ratio, limit=15) 

        temp_results = []
        
        for cleaned_title, score, _ in matches:
            if score < 75:
                continue

            # Logique de score intelligent
            length_ratio = len(cleaned_title) / len(cleaned_search) if len(cleaned_search) > 0 else 0
            specificity_bonus = 0
            if 0.9 <= length_ratio <= 1.1:
                specificity_bonus = 10
            elif length_ratio < 0.5:
                specificity_bonus = -15
                
            final_score = score + specificity_bonus

            original_title = cleaned_to_original_map.get(cleaned_title)
            anime_link = cleaned_to_id_map.get(cleaned_title)

            anime_cover = cleaned_to_cover_map.get(cleaned_title)

            if original_title and anime_link:
                temp_results.append({
                    "title": original_title,
                    "lien": anime_link,
                    "cover": anime_cover,
                    "final_score": final_score
                })

        # Tri sur le score final
        temp_results.sort(key=lambda x: x["final_score"], reverse=True)

        # Logique anti-doublons et application de la limite
        final_results = []
        seen_ids = set()
        for res in temp_results:
            if len(final_results) >= limit:
                break
            if res["lien"] not in seen_ids:
                res['score'] = res.pop('final_score')
                final_results.append(res)
                seen_ids.add(res["lien"])

        return final_results
    
    def getInfoAnime(querry):
        animes = []
        # data = requests.get(f"http://127.0.0.1:5000/api/getSerchAnime?q={querry}").json()
        scraper = cloudscraper.create_scraper()  # équivaut à un navigateur
        data = scraper.get(f"http://{Config.IP}:{Config.PORT}/api/getSerchAnime?q={querry}").json()

        base_url = data[0]["lien"]
        title = data[0]["title"]
        cover = data[0].get("cover", "")

        scraper = cloudscraper.create_scraper()  # équivaut à un navigateur
        reponse = scraper.get(base_url)
        soup = BeautifulSoup(reponse.text, 'html.parser')

        scripts = soup.find_all("script")
        pattern = re.compile(r'panneau(?:Anime|Film|Scan|Visual)\s*\(\s*(["\'])(.*?)\1\s*,\s*(["\'])(.*?)\3\s*\)')

        for script in scripts:
            if script.text:  # Vérifie qu'il contient bien du texte
                text = re.sub(r'/\*.*?\*/', '', script.text, flags=re.DOTALL)
                matches = pattern.findall(text)
                for quote1, nom, quote2, lien in matches:
                    if nom.lower() != "nom" and lien.lower() != "url":
                        saison_url = base_url.rstrip("/") + "/" + lien.lstrip("/")
                        animes.append({
                            "base_url": base_url,
                            "title": title,
                            "cover": cover,
                            "Saison": nom,
                            "url": saison_url
                        })

        return animes
    
    def getSpecificAnime(nom, saison=None, version=None): # Syntaxe exemple nom, saison, version : spice%20and%20wolf&s=saison1&v=vostfr
        scraper = cloudscraper.create_scraper()
        reponse = scraper.get(f"http://{Config.IP}:{Config.PORT}/api/getInfoAnime?q={nom}").json() 

        # Vérifier que saison n'est pas vide
        if not saison:
            saison = "saison1"
        if not version:
            version = "vostfr"

        # Extraire toutes les saisons
        saisons = [item["Saison"] for item in reponse if "Saison" in item]
        
        # Normaliser les noms
        saisons_normalized = [s.strip().lower().replace(" ", "") for s in saisons]
        saison_norm = saison.strip().lower().replace(" ", "")
        
        for i, s in enumerate(saisons_normalized):
            if s == saison_norm:
                return reponse[i]

        # Si la saison demandée n'est pas trouvée par nom exact, retourner la première saison par défaut
        if reponse and len(reponse) > 0:
            return reponse[0]

        return None
        
    def getAnimeLink(nom, saison=None, version=None): # Recupère les différents liens disponibles afin de retourner une playlist complète et prête à être téléchargée
        
        if not saison:
            saison = "saison1"
        if not version:
            version = "vostfr"

        good_link = []
        # Liste étendue des hébergeurs vidéo supportés (Sibnet, Embed4me, Ansembed, Vidmoly, Smoothpre, Sendvid, etc.)
        # "sibnet.ru", "video.sibnet.ru",
        allowed_sites = [
            "embed4me.com", "lpayer.embed4me.com", "player.embed4me.com",
            "ansembed.net", "ansembed.com",
            "vidmoly.to", "vidmoly.net", "vidmoly.me",
            "smoothpre.com", "vidhide.com", "vidhidepro.com",
            "streamwish.com", "streamwish.to",
            "sendvid.com", "oneupload.to", "oneupload.net",
            "filemoon.sx", "filemoon.to", "vidoza.net"
        ]
        
        scraper = cloudscraper.create_scraper()  # équivaut à un navigateur
        try:
            reponse = scraper.get(f"http://{Config.IP}:{Config.PORT}/api/getSpecificAnime?q={nom}&s={saison}").json()
        except Exception:
            reponse = Cardinal.getSpecificAnime(nom, saison, version)

        if not reponse or not isinstance(reponse, dict) or "url" not in reponse:
            return []

        base_url = reponse.get("base_url", "")
        url = reponse["url"]

        saison_num = saison.lower().replace(" ", "")
        version = version.lower().replace(" ", "")

        if saison_num == "film":
            first_rewoks = url.lower().replace("//film", "/film")
            second_rewoks = first_rewoks.split("/vostfr")[0]
            link = f"{second_rewoks}/{version}"
        else:
            new_url = url.split("/vostfr")[0]
            link = f"{new_url}/{version}"

        scraper = cloudscraper.create_scraper()
        second = scraper.get(link)
        # print(second)

        soup = BeautifulSoup(second.text, 'html.parser')
        
        script_tag = soup.find("script", src=lambda s: s and "episodes.js" in s)
        if not script_tag:
            return []

        js_str = str(script_tag)
        js_link = js_str.split('src="')[1].split('"')[0]

        jsfile = f"{link}/{js_link}" # Lien du fichier contenant tous les liens vers les différents épisodes
        js_text = scraper.get(jsfile).text
        matches = re.findall(r"var\s+(eps\d+)\s*=\s*\[(.*?)\];", js_text, re.DOTALL)

        all_eps = {
            name: re.findall(r"'(https?://[^']+)'", content)
            for name, content in matches
        }

        if not all_eps:
            return []

        # On trie les lecteurs disponibles (eps1, eps2, eps3, ...)
        lecteurs = sorted([k for k in all_eps.keys() if k.startswith("eps")], key=lambda x: int(x.replace("eps", "") or 0))
        if not lecteurs:
            return []

        nombre_episodes = max(len(all_eps[k]) for k in lecteurs)

        # Parcours épisode par épisode en testant les lecteurs dans l'ordre (eps1 -> eps2 -> ...)
        for episode in range(nombre_episodes):
            best_link = None
            fallback_link = None

            for lecteur in lecteurs:
                eps_list = all_eps[lecteur]
                if episode >= len(eps_list):
                    continue

                url_to_test = eps_list[episode]
                analyse = any(site in url_to_test.lower() for site in allowed_sites)

                if analyse:
                    try:
                        resolved = resolve_video_url(url_to_test)
                        if resolved and resolved.get("url"):
                            res_type = resolved.get("type", "raw")
                            # Si le résolveur extrait un lien direct vidéo (m3u8 ou mp4), on le sélectionne immédiatement
                            if res_type in ["m3u8", "mp4"]:
                                best_link = resolved["url"]
                                break
                            elif not fallback_link:
                                fallback_link = resolved["url"]
                    except Exception:
                        pass

            final_url = best_link or fallback_link
            if final_url:
                good_link.append({
                    "episode": episode,
                    "url": final_url
                })

        return good_link


    def getScanLink(nom, chap=None):

        if not chap:
            chap = "all"

        resolve_json = {}

        scraper = cloudscraper.create_scraper()  # équivaut à un navigateur
        chap_information = scraper.get(f"http://{Config.IP}:{Config.PORT}/api/getScanHashmap?n={nom}").json()

        origin_title = chap_information["title"]
        title = origin_title.replace(" ", "%20")
        
        if chap == "all":
            for chapitre in range(1, chap_information.get("max_chapter", 0) + 1): # La variable chapitre contient seulement l'id du chapitre que l'on analyse
                chap_key = f"Chapitre {chapitre}"
                resolve_json[chap_key] = []
                # Renvoie le nombre de page qu'il va faloir loop pour recuperer toute les images : chap_information[f"Chapitre {chapitre}"]
                for images in range (1, chap_information[str(chapitre)] + 1):
                    
                    resolve_json[chap_key].append(f"https://anime-sama.to/s2/scans/{title}/{chapitre}/{images}.jpg") # Lien typique sous se format https://anime-sama.to/s2/scans/nomeScan/chapitreNumber/imageNumber.jpg : https://anime-sama.to/s2/scans/Frieren/1/2.jpg
        else:
            chap_key = f"Chapitre {chap}"
            resolve_json[chap_key] = []
            for images in range(1, chap_information[str(chap)] + 1):
                resolve_json[chap_key].append(f"https://anime-sama.to/s2/scans/{title}/{chap}/{images}.jpg") # Lien typique sous se format https://anime-sama.to/s2/scans/nomeScan/chapitreNumber/imageNumber.jpg : https://anime-sama.to/s2/scans/Frieren/1/2.jpg

        return resolve_json

    def getScanHashmap(nom):
        saison = "scans"

        scraper = cloudscraper.create_scraper()  # équivaut à un navigateur
        reponse = scraper.get(f"http://{Config.IP}:{Config.PORT}/api/getSpecificAnime?q={nom}&s={saison}").json()

        # Lien typique que l'on vise pour les informations de base : https://anime-sama.to/s2/scans/get_nb_chap_et_img.php?oeuvre=Frieren
        title = reponse["title"]
        chap_hashmap = scraper.get(f"https://anime-sama.to/s2/scans/get_nb_chap_et_img.php?oeuvre={title}")
        chap_information = Utils.transform_chapters(chap_hashmap.content, title)

        return chap_information