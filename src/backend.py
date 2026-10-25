import json, os, re, cloudscraper, requests, unicodedata
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from rapidfuzz import process, fuzz
from bs4 import BeautifulSoup

try :
    from .utils.resolvers import resolve_video_url, check_stream_health
    from .utils.config import Config
    from .utils.utils import Utils
except ImportError:
    from src.utils.resolvers import resolve_video_url, check_stream_health
    from src.utils.config import Config
    from src.utils.utils import Utils


PATH = os.path.dirname(os.path.abspath(__file__))
PATH_DIR = os.path.join(PATH, "data", "json")
PATH_ANIME = os.path.join(PATH_DIR, "AnimeInfo.json")
BASE_URL = Utils.findLink()

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
}

class Cardinal:

    def findLink():
        return {"url": BASE_URL}
        
    def getAllAnime(reset="False"):
        global BASE_URL
        base_url = BASE_URL if BASE_URL else Utils.findLink()
        if not base_url:
            return "Erreur : Impossible de joindre Anime-Sama pour trouver l'URL."
        BASE_URL = base_url

        os.makedirs(PATH_DIR, exist_ok=True) # Verifi l'existance du dossier data/json

        is_empty = True
        if os.path.exists(PATH_ANIME) and os.path.getsize(PATH_ANIME) > 2:
            try:
                with open(PATH_ANIME, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    if isinstance(existing, list) and len(existing) > 0:
                        is_empty = False
            except Exception:
                is_empty = True

        is_reset = str(reset).strip().lower() in ["true", "1", "yes", "t"]

        if not is_empty and not is_reset:
            return "Fichier déjà existant. Ajoutez l'argument reset='True' pour tout actualiser."

        scraper = cloudscraper.create_scraper()  # équivaut à un navigateur
        max_pages = 1
        page_1_html = ""

        try:
            first_response = scraper.get(f"{base_url}/catalogue/fragment.php?page=1", timeout=10)
            if first_response.status_code == 200:
                json_data = first_response.json()
                page_1_html = json_data.get('liste', '')
                total_items = int(json_data.get('total', 0))
                if total_items > 0:
                    max_pages = (total_items + 47) // 48
                else:
                    pagi_soup = BeautifulSoup(json_data.get('pagination', ''), 'lxml')
                    page_input = pagi_soup.find('input', attrs={'max': True})
                    if page_input and page_input.get('max', '').isdigit():
                        max_pages = int(page_input['max'])
        except Exception:
            pass

        if max_pages <= 1 and not page_1_html:
            first_response = scraper.get(f"{base_url}/catalogue", timeout=10)
            if first_response.status_code != 200:
                return first_response.status_code

            soup_init = BeautifulSoup(first_response.content, 'lxml')
            page_input = soup_init.find('input', attrs={'max': True})
            if page_input and page_input.get('max', '').isdigit():
                max_pages = int(page_input['max'])
            else:
                pagi_links = soup_init.select('.pagi-pages .pagi-num')
                nums = [int(a.get_text(strip=True)) for a in pagi_links if a.get_text(strip=True).isdigit()]
                max_pages = max(nums) if nums else 1

        def fetch_page_content(page_num):
            if page_num == 1 and page_1_html:
                return page_1_html
            for _ in range(3):
                try:
                    r = scraper.get(f"{base_url}/catalogue/fragment.php?page={page_num}", timeout=10)
                    if r.status_code == 200:
                        return r.json().get('liste', '')
                    r_cat = scraper.get(f"{base_url}/catalogue/?page={page_num}", timeout=10)
                    if r_cat.status_code == 200:
                        return r_cat.content
                except Exception:
                    pass
            return ""

        with ThreadPoolExecutor(max_workers=10) as executor:
            pages_content = list(executor.map(fetch_page_content, range(1, max_pages + 1)))

        data = []
        seen_links = set()

        for content in pages_content:
            if not content:
                continue
            soup = BeautifulSoup(content, 'lxml')

            cards = soup.select('.as-carte')
            if cards:
                for card in cards:
                    titre = card.get('data-nom', '').strip()
                    if not titre:
                        t_tag = card.find(class_='as-carte-titre') or card.find(['h3', 'h2'])
                        titre = t_tag.get_text(strip=True) if t_tag else ""

                    a_tag = card.find('a', class_='as-carte-lien') or card.find('a')
                    link = a_tag.get('href', '').strip() if a_tag else card.get('data-url', '').strip()
                    if link:
                        parsed = urlparse(link)
                        path = parsed.path.rstrip('/')
                        link = f"{base_url.rstrip('/')}{path}"

                    cover = card.get('data-img', '').strip()
                    if not cover:
                        img_tag = card.find('img')
                        cover = img_tag.get('src', '').strip() if img_tag else ""

                    if titre and link and link not in seen_links:
                        seen_links.add(link)
                        data.append({
                            "title": Cardinal.normalize_title(titre),
                            "link": link,
                            "cover": cover
                        })
            else:
                titles = soup.find_all('h2', class_="card-title")
                for title_tag in titles:
                    card_link = title_tag.find_parent('a')
                    titre = title_tag.get_text(strip=True)
                    link = card_link.get('href', '') if card_link else ""
                    if link and link.startswith('/'):
                        link = f"{base_url.rstrip('/')}{link}"
                    img_tag = card_link.find('img', class_="card-image") if card_link else None
                    img_src = img_tag.get('src', '') if img_tag else ""

                    if titre and link and link not in seen_links:
                        seen_links.add(link)
                        data.append({
                            "title": Cardinal.normalize_title(titre),
                            "link": link,
                            "cover": img_src
                        })

        with open(PATH_ANIME, "w", encoding='utf-8') as t:
            json.dump(data, t, ensure_ascii=False, indent=2)

        return "Recuperation achever"

    def loadBaseAnimeData():
        if os.path.exists(PATH_ANIME) == True:
            try:
                with open(PATH_ANIME, "r", encoding="utf-8") as data:
                    anime_data = json.load(data)
            except Exception:
                anime_data = []

            # Si le fichier est vide, on déclenche l'actualisation
            if not anime_data:
                Cardinal.getAllAnime(reset="True")
                if os.path.exists(PATH_ANIME):
                    with open(PATH_ANIME, "r", encoding="utf-8") as refreshed:
                        return json.load(refreshed)
                return []

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
                    Cardinal.getAllAnime(reset="True")
                    with open(PATH_ANIME, "r", encoding="utf-8") as refreshed:
                        return json.load(refreshed)

            return anime_data
        else:
            Cardinal.getAllAnime(reset="True")
            if os.path.exists(PATH_ANIME):
                with open(PATH_ANIME, "r", encoding="utf-8") as refreshed:
                    return json.load(refreshed)
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
            
    def serchAnime(search, limit):  # Recherche les animes par fuzzy matching
        animes_data = Cardinal.loadBaseAnimeData()
        if not isinstance(animes_data, list):
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
        data = Cardinal.serchAnime(querry, 5)
        if not data:
            return []

        base_url = data[0]["lien"]
        title = data[0]["title"]
        cover = data[0].get("cover", "")

        scraper = cloudscraper.create_scraper()  # équivaut à un navigateur
        reponse = scraper.get(base_url)
        soup = BeautifulSoup(reponse.text, 'html.parser')

        # Récupération du synopsis
        synopsis = ""
        synopsis_tag = (
            soup.find("p", class_="ak-slide-synopsis")
            or soup.find(id="synopsisText")
            or soup.select_one(".oe-synopsis p")
            or soup.find(class_="oe-synopsis")
        )
        if synopsis_tag:
            for extra in synopsis_tag.find_all(["button", "a"]):
                extra.decompose()
            synopsis = re.sub(r'\s+', ' ', synopsis_tag.get_text(separator=' ', strip=True)).strip()

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
                            "synopsis": synopsis,
                            "Saison": nom,
                            "url": saison_url
                        })

        return animes
    
    def getSpecificAnime(nom, saison=None, version=None): # Syntaxe exemple nom, saison, version : spice%20and%20wolf&s=saison1&v=vostfr
        reponse = Cardinal.getInfoAnime(nom)
        if not reponse or not isinstance(reponse, list):
            return None

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
            if s == saison_norm or (saison_norm in ["oav", "oavs"] and "oav" in s):
                return reponse[i]

        for i, s in enumerate(saisons_normalized):
            if saison_norm in s or s in saison_norm:
                return reponse[i]

        if reponse and len(reponse) > 0:
            return reponse[0]

        return None
        
    def getAnimeLink(nom, saison=None, version=None): # Recupère les différents liens disponibles afin de retourner une playlist complète et prête à être téléchargée
        
        if not saison:
            saison = "saison1"
        if not version:
            version = "vostfr"

        reponse = Cardinal.getSpecificAnime(nom, saison, version)
        if not reponse or not isinstance(reponse, dict) or "url" not in reponse:
            return []

        base_url = reponse.get("base_url", "")
        url = reponse["url"]

        saison_num = saison.lower().replace(" ", "")
        version = version.lower().replace(" ", "")

        if saison_num == "film":
            first_rewoks = url.lower().replace("//film", "/film")
            second_rewoks = re.sub(r'/(?:vostfr|vf)/?$', '', first_rewoks, flags=re.IGNORECASE)
            link = f"{second_rewoks}/{version}"
        elif saison_num in ["oav", "oavs"]:
            first_rewoks = url.lower().replace("//oav", "/oav")
            second_rewoks = re.sub(r'/(?:vostfr|vf)/?$', '', first_rewoks, flags=re.IGNORECASE)
            link = f"{second_rewoks}/{version}"
        else:
            new_url = re.sub(r'/(?:vostfr|vf)/?$', '', url, flags=re.IGNORECASE)
            link = f"{new_url}/{version}"

        scraper = cloudscraper.create_scraper()
        second = scraper.get(link)

        soup = BeautifulSoup(second.text, 'html.parser')
        
        script_tag = soup.find("script", src=lambda s: s and "episodes.js" in s)
        if not script_tag:
            return []

        src = script_tag.get("src", "")
        js_link = src.split('"')[0].split("'")[0]

        jsfile = f"{link.rstrip('/')}/{js_link.lstrip('/')}"
        js_text = scraper.get(jsfile, headers={**headers, "Referer": link}).text
        # Supporte eps1, eps2... ainsi que epsAS ou autres variantes de lecteurs
        matches = re.findall(r"var\s+(eps\w+)\s*=\s*\[(.*?)\];", js_text, re.DOTALL)

        all_eps = {
            name: re.findall(r"'(https?://[^']+)'", content)
            for name, content in matches
        }

        if not all_eps:
            return []

        def get_lecteur_idx(k):
            num = re.sub(r'[^0-9]', '', k)
            return int(num) if num else 99

        def lecteur_priority(l_name):
            urls = all_eps.get(l_name, [])
            first_url = urls[0].lower() if urls else ""
            if "ansembed" in first_url:
                return 0
            if any(s in first_url for s in ["smoothpre", "vidhide", "streamwish", "vidmoly"]):
                return 1
            if "sendvid" in first_url:
                return 2
            if any(s in first_url for s in ["embed4me", "lpayer", "player"]):
                return 3
            return 4

        # Trie les lecteurs par ordre de priorité de qualité/vitesse puis par numéro (eps1, eps2...)
        valid_lecteurs = sorted(
            [k for k, eps in all_eps.items() if eps],
            key=lambda l: (lecteur_priority(l), get_lecteur_idx(l))
        )
        nombre_episodes = max(len(v) for v in all_eps.values())

        def resolve_single_episode(ep_idx):
            session = requests.Session()
            fallback_url = None
            best_candidate = None

            for lecteur in valid_lecteurs:
                eps_list = all_eps.get(lecteur, [])
                if ep_idx >= len(eps_list):
                    continue

                url_to_test = eps_list[ep_idx].strip(" \t\n\r\xa0")
                if not url_to_test or "sibnet.ru" in url_to_test.lower():
                    if url_to_test and not fallback_url:
                        fallback_url = url_to_test
                    continue

                if not fallback_url:
                    fallback_url = url_to_test

                try:
                    resolved = resolve_video_url(url_to_test, session=session)
                except Exception:
                    resolved = None

                if resolved and isinstance(resolved, dict):
                    resolved_url = resolved.get("url")
                    if resolved_url and resolved.get("type") in ("m3u8", "mp4"):
                        # Vérification de santé du stream
                        error_score, is_healthy = check_stream_health(resolved, session=session)
                        
                        # 0 = stream vérifié actif et sain
                        if error_score == 0:
                            return {
                                "episode": ep_idx + 1,
                                "url": resolved_url
                            }
                        
                        # Flux potentiellement valide mais lent à répondre (timeout/connexion lente)
                        elif is_healthy and error_score < 999:
                            if not best_candidate:
                                best_candidate = resolved_url

            # Si aucun lecteur n'a pu être validé instantanément, utiliser le meilleur candidat
            if best_candidate:
                return {
                    "episode": ep_idx + 1,
                    "url": best_candidate
                }

            # En dernier recours pour ne jamais rejeter l'épisode, retourner l'embed
            if fallback_url:
                return {
                    "episode": ep_idx + 1,
                    "url": fallback_url
                }
            return None

        # Exécution en parallèle optimisée
        max_workers = min(8, max(1, nombre_episodes))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(resolve_single_episode, range(nombre_episodes)))

        good_link = [r for r in results if r is not None]
        good_link.sort(key=lambda x: x["episode"])
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