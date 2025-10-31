import requests, json, os, re, asyncio
from rapidfuzz import process, fuzz
from bs4 import BeautifulSoup
from src.utils.m3u8 import extract_m3u8_from_page

PATH = os.path.dirname(os.path.abspath(__file__))
PATH_DIR = os.path.join(PATH, r"data\json")
PATH_ANIME = os.path.join(PATH_DIR, "AnimeInfo.json")

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
    
    def getAllAnime(reset="False"):
        
        data = []
        page = 1

        os.makedirs(PATH_DIR, exist_ok=True) # Verifi l'existance du dossier data/json

        while True:
            if not os.path.exists(PATH_ANIME) or reset == "True":
                reponse = requests.get(f"https://anime-sama.fr/catalogue/?page={page}")

                if reponse.status_code == 200:
                    source = reponse.content
                    soup = BeautifulSoup(source, 'lxml')

                    if soup.find_all('p', class_ = "text-white font-bold text-2xl h-96 p-5"):
                        # print(page)
                        with open(PATH_ANIME, "w", encoding='utf-8') as t:
                            json.dump(data, t, ensure_ascii=False, indent=2)
                        
                        return "Recuperation achever"
                    else:
                        for soupPrimordial in soup.find_all('a', class_ = "flex divide-x"):
                            for tag in soupPrimordial.select('img, p, hr'):
                                tag.extract() # Enlève les balise non interessante d'abord de notre soupPrimordial
                            
                            h1 = soupPrimordial.find('h1')
                            Titre = h1.get_text(strip=True) if h1 else "Titre introuvable"
                            link = soupPrimordial.get('href')

                            secondRequest = requests.get(link)
                            secondSoup = BeautifulSoup(secondRequest.text, 'lxml')
                            titre_alter = secondSoup.find('h2', id="titreAlter")
                            if titre_alter:
                                AlterTitle = titre_alter.get_text(strip=True)
                            
                            data.append({
                                "title" : Titre,
                                "AlterTitle" : AlterTitle,
                                "link" : link
                            })

                    # print(f"Page : {page}")
                    page += 1
                else:
                    return reponse.status_code
            else:
                return "Fichier déjà existant ajouté l'argument = r=True pour tous actualiser"

    def loadBaseAnimeData():
        if os.path.exists(PATH_ANIME) == True:
            with open(PATH_ANIME, "r", encoding="utf-8") as data:
                return json.load(data)
        else:
            return "Fichier non existant velliez request : http://127.0.0.1:5000/api/getAllAnime"
        
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
            
    def serchAnime(search, limit):  #Ajouter de quoi afficher sur la liste final les titre alternatif si il y en a
        try:
            animes_data = requests.get("http://127.0.0.1:5000/api/loadBaseAnimeData").json()
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la récupération des animes: {e}")
            return []

        cleaned_search = Cardinal.clean_string(search)  # Utilise directement Cardinal.clean_string
        if not cleaned_search:
            return []

        # Utilisation de dictionnaires pour garantir l'unicité
        cleaned_to_original_map = {Cardinal.clean_string(anime.get("title", "")): anime.get("title") for anime in animes_data if anime.get("title")}
        cleaned_to_id_map = {Cardinal.clean_string(anime.get("title", "")): anime.get("link") for anime in animes_data if anime.get("title")}
        
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

            if original_title and anime_link:
                temp_results.append({
                    "title": original_title,
                    "lien": anime_link,
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
    
    def getInfoAnime(querry): # Voir pour proposer un lien de scan par défaut ou non 
        animes = []
        data = requests.get(f"http://127.0.0.1:5000/api/getSerchAnime?q={querry}").json()

        base_url = data[0]["lien"]
        title = data[0]["title"]

        reponse = requests.get(base_url)
        soup = BeautifulSoup(reponse.text, 'html.parser')

        scripts = soup.find_all("script")
        pattern = re.compile(r'panneauAnime\("([^"]+)",\s*"([^"]+)"\)')

        for script in scripts:
            if script.string:  # Vérifie qu'il contient bien du texte
                text = re.sub(r'/\*.*?\*/', '', script.string, flags=re.DOTALL)
                matches = pattern.findall(text)
                for nom, lien in matches:
                    if nom.lower() != "nom" and lien.lower() != "url":
                        saison_url = base_url + "/" + lien
                        animes.append({
                            "base_url": base_url,
                            "title": title,
                            "Saison": nom,
                            "url": saison_url
                        })

                # scan_url = []
                # scan_url.append({
                #     "scan_url" :base_url + "/scan/vf"
                #     })

        return animes#, scan_url
    
    def getAnimeLink(nom, saison, version): # Recupère les different lien disponible affin de retourner une playlist complete et prete a être télécharger
        error = []
        good_link = []
        allowed_sites = ["video.sibnet.ru"]
        lecteur_num = 1
        lecteur = f"eps{lecteur_num}"
        
        reponse = requests.get(f"http://127.0.0.1:5000/api/getInfoAnime?q={nom}").json()

        base_url = reponse[0]["base_url"]
        saison_num = saison.lower()
        version = version.lower()

        if saison_num == "film":
            link = f"{base_url}{saison_num}/{version}"
        
        else:
            link = f"{base_url}{saison_num}/{version}"        
        
        second = requests.get(link)
        soup = BeautifulSoup(second.text, 'html.parser')
        
        script_tag = soup.find("script", src=lambda s: s and "episodes.js" in s)
        js_str = str(script_tag)
        js_link = js_str.split('src="')[1].split('" type="')[0] # Exemple de sortie : episodes.js?filever=5306

        jsfile = f"{link}/{js_link}" # Lien du fichier contenant tous les lien vers les differents episode

        js_text = requests.get(jsfile).text
        matches = re.findall(r"var\s+(eps\d+)\s*=\s*\[(.*?)\];", js_text, re.DOTALL)

        all_eps = {
            name: re.findall(r"'(https?://[^']+)'", content)
            for name, content in matches
        }

        nombre_lecteurs = sum(1 for lecteur_num in all_eps if lecteur_num.startswith('eps')) # Renvoie le nombre de lecteur max disponible
        # print(nombre_lecteurs)
        nombre_episodes = len(all_eps.get("eps1", [])) # Renvoie le nombre de fois a boucler pour avoir tous les épisode
        
        for episode in range(nombre_episodes):
            try :
                reponse = requests.get(all_eps[lecteur][episode],headers=headers, timeout=10)

                analyse = any(site in all_eps[lecteur][episode] for site in allowed_sites)

                if reponse.status_code != 200 or reponse.status_code == 200 and analyse == False:
                    error.append({
                        "lecteur" : lecteur,
                        "episode" : episode,
                        "url" : all_eps[lecteur][episode]
                    })
                    continue

                elif reponse.status_code == 200 and analyse:
                    good_link.append({
                        "episode" : episode,
                        "url" : all_eps[lecteur][episode]
                    })
                    if len(good_link) == nombre_episodes:
                        return good_link

            except requests.ConnectionError:
                # print("Erreur le serveur a fermer la connection...")
                error.append({
                    "lecteur" : lecteur,
                    "episode" : episode,
                    "url" : all_eps[lecteur][episode]
                })
                continue
        
        if error:
            new_error = []

            for lecteur_num in range(1, nombre_lecteurs + 1):
                lecteur_er = f"eps{lecteur_num}"

                for e in error.copy():

                    try:
                        error_ep = e['episode']
                        # print(all_eps[lecteur_er][error_ep])

                        reponse = requests.get(all_eps[lecteur_er][error_ep], headers=headers, timeout=10)
                        # print(reponse.status_code)
                        analyse = any(site in all_eps[lecteur_er][error_ep] for site in allowed_sites)

                        if reponse.status_code != 200 or reponse.status_code != 200 and analyse == False:
                            new_error.append({
                                "lecteur": lecteur_er,
                                "episode": error_ep,
                                "url": all_eps[lecteur_er][error_ep]
                            })
                            continue
                        
                        if reponse.status_code == 200 and analyse:
                            good_link.append({
                                "episode": error_ep,
                                "url": all_eps[lecteur_er][error_ep]
                            })

                            # print(len(good_link))
                            if len(good_link) == nombre_episodes:
                                return good_link

                    except requests.ConnectionError:
                        # print("Erreur : le serveur a fermé la connexion...")
                        new_error.append({
                            "lecteur": lecteur_er,
                            "episode": error_ep,
                            "url": all_eps[lecteur_er][error_ep]
                        })
                        continue

            if len(good_link) < nombre_episodes:
                episodes_trouves = [item["episode"] for item in good_link]
                episodes_attendus = list(range(nombre_episodes))
                episodes_manquants = [ep for ep in episodes_attendus if ep not in episodes_trouves]

                # print(f"Il manque {len(episodes_manquants)} épisode qui est : {episodes_manquants}")
                episode_numbers_to_search = [index + 1 for index in episodes_manquants] 
                # print(f"Lancement de la recherche pour le(s) numéro(s) d'épisode(s) : {episode_numbers_to_search}")

                if base_url:
                    m3u8_for_missing = asyncio.run(extract_m3u8_from_page(link, episode_numbers_to_search))
                        
                    # On ajoute les nouveaux liens trouvés à notre liste principale
                    if m3u8_for_missing:
                        # print(f"{len(m3u8_for_missing)} liens M3U8 supplémentaires ont été trouvés.")
                        for item in m3u8_for_missing:
                            item["episode"] = item["episode"] - 1
                            good_link.append(item)

                    # Trier la liste finale pour qu'elle soit dans l'ordre
                else:
                    print(f"Impossible de construire l'URL de base pour la saison {saison}")
                                        
                good_link.sort(key=lambda x: x.get('episode', 0))
                return good_link

        
        # print(error)
        # print(error[5]) # Pour iterer les erreur a terme

        # print(js_text)
        
        # return link

        # saison_num = reponse.text
        # print(saison_nu)