import json, os, re, cloudscraper, requests, unicodedata
from urllib.parse import urlparse, quote
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
        existing_alts_by_link = {}
        if os.path.exists(PATH_ANIME) and os.path.getsize(PATH_ANIME) > 2:
            try:
                with open(PATH_ANIME, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    if isinstance(existing, list) and len(existing) > 0:
                        is_empty = False
                        for item in existing:
                            if isinstance(item, dict) and item.get("link") and item.get("alt_titles"):
                                existing_alts_by_link[item["link"]] = item["alt_titles"]
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
                        entry = {
                            "title": Cardinal.normalize_title(titre),
                            "link": link,
                            "cover": cover
                        }
                        if link in existing_alts_by_link:
                            entry["alt_titles"] = existing_alts_by_link[link]
                        data.append(entry)
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
                        entry = {
                            "title": Cardinal.normalize_title(titre),
                            "link": link,
                            "cover": img_src
                        }
                        if link in existing_alts_by_link:
                            entry["alt_titles"] = existing_alts_by_link[link]
                        data.append(entry)

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
            
    STOP_WORDS = {'le', 'la', 'les', 'un', 'une', 'de', 'du', 'des', 'the', 'a', 'an', 'of', 'in', 'to', 'no', 'et', 'and'}

    @staticmethod
    def _evaluate_match(cq, ct):
        if cq == ct:
            return 100.0

        q_words = cq.split()
        t_words = ct.split()
        if not q_words or not t_words:
            return 0.0

        # Cas 1: cq est une sous-chaîne exacte de ct (ex: 'naruto' in 'naruto shippuden')
        if cq in ct:
            extra_words = max(0, len(t_words) - len(q_words))
            ratio_len = len(cq) / len(ct)
            return max(60.0, 75.0 + 15.0 * ratio_len - (extra_words * 2.5))

        # Cas 2: ct est une sous-chaîne exacte de cq (ex: 'frieren' in 'sousou no frieren')
        if ct in cq and len(ct) >= 3:
            non_matching_q = [w for w in q_words if not any(fuzz.ratio(w, tw) >= 70 for tw in t_words)]
            non_matching_substantive = [w for w in non_matching_q if w not in Cardinal.STOP_WORDS]
            # Si plus de 2 mots substantiels ajoutés ne correspondent à rien, rejeter
            if len(non_matching_substantive) >= 3:
                return 0.0
            ratio_len = len(ct) / len(cq)
            return 80.0 + 20.0 * ratio_len

        # Cas 3: Ni l'un ni l'autre n'est sous-chaîne
        # Chaque mot important de la requête doit correspondre à au moins un mot du titre
        for qw in q_words:
            if qw in Cardinal.STOP_WORDS:
                continue
            best_w = max((fuzz.ratio(qw, tw) for tw in t_words), default=0)
            if best_w < 70:
                return 0.0

        # Vérifier aussi la couverture inverse pour rejeter les titres trop longs et hors-sujet
        matched_t = 0
        substantive_t = 0
        for tw in t_words:
            if tw in Cardinal.STOP_WORDS:
                continue
            substantive_t += 1
            best_w = max((fuzz.ratio(tw, qw) for qw in q_words), default=0)
            if best_w >= 70:
                matched_t += 1

        if substantive_t > 0 and (matched_t / substantive_t) < 0.4:
            return 0.0

        ts_ratio = fuzz.token_sort_ratio(cq, ct)
        w_ratio = fuzz.WRatio(cq, ct)
        tset_ratio = fuzz.token_set_ratio(cq, ct)
        return (ts_ratio * 0.4) + (w_ratio * 0.4) + (tset_ratio * 0.2)
            
    @staticmethod
    def update_anime_alt_titles(canonical_link_or_title, alt_titles):
        """Met à jour les titres alternatifs d'un anime dans AnimeInfo.json."""
        if not alt_titles or not canonical_link_or_title:
            return
        try:
            if not os.path.exists(PATH_ANIME):
                return
            with open(PATH_ANIME, "r", encoding="utf-8") as f:
                animes_data = json.load(f)
            if not isinstance(animes_data, list):
                return

            updated = False
            for anime in animes_data:
                if anime.get("link") == canonical_link_or_title or anime.get("title") == canonical_link_or_title:
                    existing_alts = set(anime.get("alt_titles", []))
                    new_alts = set(alt_titles)
                    if not new_alts.issubset(existing_alts):
                        anime["alt_titles"] = sorted(list(existing_alts.union(new_alts)))
                        updated = True
                    break

            if updated:
                with open(PATH_ANIME, "w", encoding="utf-8") as f:
                    json.dump(animes_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def serchAnime(search, limit=5):  # Recherche les animes par matching intelligent et précis (titres principaux + alternatifs)
        animes_data = Cardinal.loadBaseAnimeData()
        if not isinstance(animes_data, list):
            return []

        cleaned_search = Cardinal.clean_string(search)
        if not cleaned_search:
            return []

        scored_results = []
        seen = set()

        cleaned_to_anime = {}
        cleaned_keys = []

        for anime in animes_data:
            t = anime.get("title")
            if not t:
                continue
            cleaned_main = Cardinal.clean_string(t)
            if cleaned_main:
                cleaned_to_anime[cleaned_main] = (anime, 1.0)
                cleaned_keys.append(cleaned_main)

            # Prise en compte des titres alternatifs déjà connus localement
            for alt in anime.get("alt_titles", []):
                cleaned_alt = Cardinal.clean_string(alt)
                if cleaned_alt and cleaned_alt not in cleaned_to_anime:
                    cleaned_to_anime[cleaned_alt] = (anime, 0.98)
                    cleaned_keys.append(cleaned_alt)

        # 1. Extraction préliminaire locale
        candidates = process.extract(cleaned_search, cleaned_keys, scorer=fuzz.WRatio, limit=50)

        for candidate_key, _, _ in candidates:
            anime_entry, weight = cleaned_to_anime.get(candidate_key, (None, 1.0))
            if not anime_entry:
                continue

            link = anime_entry.get("link")
            if link in seen:
                continue

            raw_score = Cardinal._evaluate_match(cleaned_search, candidate_key)
            if raw_score < 75.0:
                continue

            final_score = raw_score * weight
            seen.add(link)
            scored_results.append({
                "title": anime_entry.get("title"),
                "alt_titles": anime_entry.get("alt_titles", []),
                "lien": link,
                "cover": anime_entry.get("cover"),
                "score": round(final_score, 1)
            })

        # 2. Si aucun résultat local de quasi-certitude (>= 98), interroger la recherche native Anime-Sama
        # Anime-Sama effectue une recherche SQL sur l'intégralité de ses titres principaux et alternatifs
        best_score = scored_results[0]["score"] if scored_results else 0.0
        if best_score < 98.0:
            try:
                scraper = cloudscraper.create_scraper()
                base_url = BASE_URL if BASE_URL else Utils.findLink()
                r = scraper.get(f"{base_url}/catalogue/fragment.php?page=1&search={quote(cleaned_search)}", timeout=5)
                if r.status_code == 200:
                    json_resp = r.json()
                    soup = BeautifulSoup(json_resp.get('liste', ''), 'html.parser')
                    cards = soup.select('.as-carte')
                    for card in cards:
                        nom = card.get('data-nom', '').strip()
                        link = card.get('data-url', '').strip()
                        cover = card.get('data-img', '').strip()
                        if link:
                            parsed = urlparse(link)
                            path = parsed.path.rstrip('/')
                            link = f"{base_url.rstrip('/')}{path}"

                        if nom and link:
                            norm_title = Cardinal.normalize_title(nom)
                            cleaned_nom = Cardinal.clean_string(norm_title)
                            
                            # Calcul du score pour les résultats retournés par la recherche SQL Anime-Sama
                            if cleaned_nom == cleaned_search:
                                remote_score = 98.0
                            elif cleaned_search in cleaned_nom or cleaned_nom in cleaned_search:
                                remote_score = 96.0
                            else:
                                remote_score = 95.0

                            # Légère pénalité si c'est un spin-off alors que la requête cherchait la série principale
                            if any(w in cleaned_nom for w in ['junior', 'highschool', 'high school', 'chibi', 'spinoff', 'spin off', 'special', 'recap']):
                                if not any(w in cleaned_search for w in ['junior', 'highschool', 'high school', 'chibi', 'spinoff', 'spin off']):
                                    remote_score -= 3.0

                            local_match = next((a for a in animes_data if a.get("link") == link or a.get("title") == norm_title), None)
                            existing_entry = next((item for item in scored_results if item.get("lien") == link), None)
                            
                            if existing_entry:
                                if remote_score > existing_entry["score"]:
                                    existing_entry["score"] = remote_score
                            else:
                                seen.add(link)
                                if local_match:
                                    scored_results.append({
                                        "title": local_match.get("title", norm_title),
                                        "alt_titles": local_match.get("alt_titles", []),
                                        "lien": local_match.get("link", link),
                                        "cover": local_match.get("cover", cover),
                                        "score": remote_score
                                    })
                                else:
                                    scored_results.append({
                                        "title": norm_title,
                                        "alt_titles": [],
                                        "lien": link,
                                        "cover": cover,
                                        "score": remote_score
                                    })
            except Exception:
                pass

        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return scored_results[:limit]
    
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
        if reponse.status_code != 200:
            return []
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

        # Récupération des titres alternatifs officiels
        alt_titles = []
        alt_tag = soup.find(id="titreAlter") or soup.find(class_="oe-alters")
        if alt_tag:
            raw_alts = alt_tag.get_text(separator=',', strip=True)
            alt_titles = [Cardinal.normalize_title(a.strip()) for a in raw_alts.split(',') if a.strip()]
            seen_alts = set()
            alt_titles = [a for a in alt_titles if a and not (a in seen_alts or seen_alts.add(a))]

        # Mise à jour du cache AnimeInfo.json avec ces titres alternatifs
        if alt_titles:
            Cardinal.update_anime_alt_titles(base_url, alt_titles)

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
                            "alt_titles": alt_titles,
                            "cover": cover,
                            "synopsis": synopsis,
                            "Saison": nom,
                            "url": saison_url
                        })

        return animes
    
    @staticmethod
    def normalize_season_text(text):
        if not text:
            return ""
        text = unicodedata.normalize("NFKD", str(text))
        text = "".join(c for c in text if not unicodedata.combining(c))
        text = text.lower().strip()
        # Corriger les fautes de frappe courantes et termes anglais
        text = re.sub(r'\bsaions?\b', 'saison', text)
        text = re.sub(r'\bsaisns?\b', 'saison', text)
        text = re.sub(r'\bseasons?\b', 'saison', text)
        text = re.sub(r'\bsaisons\b', 'saison', text)
        text = re.sub(r'\bsaion(\d+)\b', r'saison \1', text)
        text = re.sub(r'\bsaisn(\d+)\b', r'saison \1', text)
        text = re.sub(r'\bseason(\d+)\b', r'saison \1', text)
        text = re.sub(r'\bsaison(\d+)\b', r'saison \1', text)
        text = re.sub(r'\bs0*(\d+)\b', r'saison \1', text)
        text = re.sub(r'\bmovies?\b', 'film', text)
        text = re.sub(r'\bov[as]+\b', 'oav', text)
        text = re.sub(r'\boavs\b', 'oav', text)
        # Si c'est juste un chiffre : "1" -> "saison 1"
        if re.match(r'^\d+$', text):
            text = f"saison {int(text)}"
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def match_season(reponse, saison_query):
        if not reponse or not isinstance(reponse, list):
            return None

        if not saison_query:
            saison_query = "saison 1"

        q_norm = Cardinal.normalize_season_text(saison_query)
        q_compact = re.sub(r'[^a-z0-9]', '', q_norm)

        # Extraire le numéro de saison visé dans la requête
        q_num_match = re.search(r'\b(?:saison|saga|partie|part)?\s*(\d+)\b', q_norm)
        q_num = int(q_num_match.group(1)) if q_num_match else None

        candidates = []
        for idx, item in enumerate(reponse):
            s_raw = item.get("Saison", "")
            s_norm = Cardinal.normalize_season_text(s_raw)
            s_compact = re.sub(r'[^a-z0-9]', '', s_norm)

            s_num_match = re.search(r'\b(?:saison|saga|partie|part)\s*(\d+)\b', s_norm)
            if not s_num_match:
                s_num_match = re.search(r'\b(\d+)\b', s_norm)
            s_num = int(s_num_match.group(1)) if s_num_match else None

            candidates.append({
                "idx": idx,
                "item": item,
                "raw": s_raw,
                "norm": s_norm,
                "compact": s_compact,
                "num": s_num
            })

        # 1. Correspondance exacte sur la chaîne compacte
        for c in candidates:
            if c["compact"] == q_compact:
                return c["item"]

        # 2. Correspondance sur le numéro précis (ex: 'saison 1', 'saion1', 's1', '1' match 'Saison 1' ou 'Saga 1')
        if q_num is not None:
            for c in candidates:
                if c["num"] == q_num:
                    return c["item"]

        # 3. Mots-clés spéciaux (film, oav, scan, kai)
        for kw in ['film', 'oav', 'scan', 'kai']:
            if kw in q_norm:
                matching = [c for c in candidates if kw in c["norm"]]
                if matching:
                    if q_num is not None:
                        num_match = [c for c in matching if c["num"] == q_num]
                        if num_match:
                            return num_match[0]["item"]
                    return matching[0]["item"]

        # 4. Correspondance de sous-chaîne sans collision de numéro
        for c in candidates:
            if (q_compact in c["compact"] or c["compact"] in q_compact) and (q_num is None or c["num"] == q_num):
                return c["item"]

        # 5. Fuzzy matching via RapidFuzz
        best_candidate = None
        best_score = 0.0
        for c in candidates:
            if q_num is not None and c["num"] is not None and c["num"] != q_num:
                continue
            score = fuzz.token_sort_ratio(q_norm, c["norm"])
            if score > best_score and score >= 70.0:
                best_score = score
                best_candidate = c["item"]
        if best_candidate:
            return best_candidate

        # 6. Fallback pour la requête par défaut ('saison 1' / 'saison' / 'saion1' si l'anime n'a pas de saison 1 numérotée)
        if q_norm in ["saison 1", "saison"] or q_compact in ["saison1", "saison"]:
            non_scans = [c["item"] for c in candidates if "scan" not in c["norm"]]
            if non_scans:
                return non_scans[0]
            return reponse[0]

        return None

    def getSpecificAnime(nom, saison=None, version=None): # Syntaxe exemple nom, saison, version : spice%20and%20wolf&s=saison1&v=vostfr
        reponse = Cardinal.getInfoAnime(nom)
        if not reponse or not isinstance(reponse, list):
            return None

        matched = Cardinal.match_season(reponse, saison)
        if not matched:
            return None

        if version:
            matched_copy = dict(matched)
            v_norm = "vf" if version.strip().lower() in ["vf", "dub", "french", "fr"] else "vostfr"
            base_saison_url = re.sub(r'/(?:vostfr|vf)/?$', '', matched_copy.get("url", ""), flags=re.IGNORECASE)
            base_saison_url = re.sub(r'(?<!:)//+', '/', base_saison_url)
            matched_copy["url"] = f"{base_saison_url}/{v_norm}"
            return matched_copy

        return matched
        
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

        v_norm = "vf" if version.strip().lower() in ["vf", "dub", "french", "fr"] else "vostfr"
        new_url = re.sub(r'/(?:vostfr|vf)/?$', '', url, flags=re.IGNORECASE)
        new_url = re.sub(r'(?<!:)//+', '/', new_url)
        link = f"{new_url}/{v_norm}"

        scraper = cloudscraper.create_scraper()
        second = scraper.get(link)
        if second.status_code != 200:
            if url != link:
                second = scraper.get(url)
                if second.status_code == 200:
                    link = url
                else:
                    return []
            else:
                return []

        soup = BeautifulSoup(second.text, 'html.parser')
        
        script_tag = soup.find("script", src=lambda s: s and "episodes.js" in s)
        if not script_tag:
            return []

        src = script_tag.get("src", "")
        js_link = src.split('"')[0].split("'")[0]

        if js_link.startswith("http://") or js_link.startswith("https://"):
            jsfile = js_link
        elif js_link.startswith("/"):
            parsed_link = urlparse(link)
            jsfile = f"{parsed_link.scheme}://{parsed_link.netloc}{js_link}"
        else:
            jsfile = f"{link.rstrip('/')}/{js_link.lstrip('/')}"

        js_text = scraper.get(jsfile, headers={**headers, "Referer": link}).text
        # Supporte eps1, eps2... ainsi que epsAS ou autres variantes de lecteurs
        matches = re.findall(r"var\s+(eps\w+)\s*=\s*\[(.*?)\];", js_text, re.DOTALL)

        all_eps = {
            name: re.findall(r'''['"](https?://[^'"]+)['"]''', content)
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

        chap_information = Cardinal.getScanHashmap(nom)
        if not chap_information or not isinstance(chap_information, dict) or "title" not in chap_information:
            return {}

        origin_title = chap_information["title"]
        title = quote(origin_title)
        max_chap = chap_information.get("max_chapter", 0)
        if max_chap <= 0:
            return {}
        
        resolve_json = {}
        if chap == "all":
            for chapitre in range(1, max_chap + 1):
                chap_key = f"Chapitre {chapitre}"
                resolve_json[chap_key] = []
                nb_images = chap_information.get(str(chapitre), 0)
                for images in range(1, nb_images + 1):
                    resolve_json[chap_key].append(f"https://anime-sama.to/s2/scans/{title}/{chapitre}/{images}.jpg")
        else:
            str_chap = str(chap)
            if str_chap not in chap_information:
                return {}
            chap_key = f"Chapitre {chap}"
            resolve_json[chap_key] = []
            nb_images = chap_information.get(str_chap, 0)
            for images in range(1, nb_images + 1):
                resolve_json[chap_key].append(f"https://anime-sama.to/s2/scans/{title}/{chap}/{images}.jpg")

        return resolve_json

    def getScanHashmap(nom):
        saison = "scans"

        reponse = Cardinal.getSpecificAnime(nom, saison=saison)
        if not reponse or not isinstance(reponse, dict) or "title" not in reponse:
            return {}

        title = reponse["title"]
        try:
            scraper = cloudscraper.create_scraper()
            encoded_title = quote(title)
            chap_hashmap = scraper.get(f"https://anime-sama.to/s2/scans/get_nb_chap_et_img.php?oeuvre={encoded_title}", timeout=10)
            if chap_hashmap.status_code != 200:
                return {}
            chap_information = Utils.transform_chapters(chap_hashmap.content, title)
            if not chap_information or not isinstance(chap_information, dict) or chap_information.get("max_chapter", 0) == 0:
                return {}
            return chap_information
        except Exception:
            return {}