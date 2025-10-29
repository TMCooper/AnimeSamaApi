import requests, json, os, re
from rapidfuzz import process, fuzz
from bs4 import BeautifulSoup

PATH = os.path.dirname(os.path.abspath(__file__))
PATH_DIR = os.path.join(PATH, r"data\json")
PATH_ANIME = os.path.join(PATH_DIR, "AnimeInfo.json")

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
            with open(PATH_ANIME, "r") as data:
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