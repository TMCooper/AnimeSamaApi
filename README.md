# 📚 Documentation complète - API Anime

## Table des matières

1. [Introduction](#1-introduction)
2. [Architecture](#2-architecture)
3. [Installation et configuration](#3-installation-et-configuration)
4. [Référence API](#4-référence-api)
5. [Guide d'utilisation](#5-guide-dutilisation)
6. [Modules et classes](#6-modules-et-classes)
7. [Algorithmes et logique](#7-algorithmes-et-logique)
8. [Gestion des erreurs](#8-gestion-des-erreurs)
9. [Performance et optimisation](#9-performance-et-optimisation)
10. [Sécurité](#10-sécurité)
11. [FAQ](#11-faq)

---

## 1. Introduction

### 1.1 Présentation

L'API Anime est une solution complète pour rechercher, récupérer et streamer des contenus anime depuis Anime-Sama. Elle offre une interface REST simple et puissante avec des fonctionnalités avancées de recherche et de récupération de liens.

### 1.2 Cas d'usage

- **Applications de streaming** : Intégration de contenus anime
- **Moteurs de recherche** : Recherche intelligente d'animes
- **Agrégateurs** : Centralisation de contenus
- **Outils de téléchargement** : Automatisation de récupération

### 1.3 Prérequis techniques

- Python 3.8+
- Connexion internet stable
- 500 MB d'espace disque
- RAM : 512 MB minimum

---

## 2. Architecture

### 2.1 Vue d'ensemble

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP/REST
┌──────▼──────────────────────────────┐
│         Flask Application           │
│  ┌──────────────────────────────┐   │
│  │        API Layer (api.py)    │   │
│  └────────────┬─────────────────┘   │
│               │                     │
│  ┌────────────▼─────────────────┐   │
│  │   Business Logic (backend.py)│   │
│  │      - Cardinal Class        │   │
│  └────┬───────────────────┬─────┘   │
│       │                   │         │
│  ┌────▼─────┐      ┌─────▼─────┐    │
│  │ Web      │      │  Playwright│   │
│  │ Scraping │      │  Extractor │   │
│  └──────────┘      └────────────┘   │
└─────────────────────────────────────┘
       │                   │
┌──────▼────────┐   ┌─────▼──────┐
│  Anime-Sama   │   │   M3U8     │
│   Website     │   │   Servers  │
└───────────────┘   └────────────┘
```

### 2.2 Composants principaux

| Composant | Fichier | Rôle |
|-----------|---------|------|
| **Entry Point** | `main.py` | Démarrage de l'application |
| **API Layer** | `api.py` | Gestion des routes et requêtes HTTP |
| **Business Logic** | `backend.py` | Traitement des données, scraping |
| **M3U8 Extractor** | `m3u8.py` | Extraction de liens vidéo |
| **Browser Utils** | `Mita.py` | Utilitaires navigateur |

### 2.3 Flux de données

```
1. Requête HTTP → 2. Validation → 3. Traitement → 4. Scraping/Cache → 5. Réponse JSON
```

---

## 3. Installation et configuration

### 3.1 Installation standard

```bash
# Cloner le projet
git clone <repository-url>
cd anime-api

# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Installer les dépendances
pip install Flask requests beautifulsoup4 lxml rapidfuzz playwright

# Installer Playwright
playwright install chromium
```

### 3.2 Configuration avancée

#### 3.2.1 Variables d'environnement

Créez un fichier `.env` :

```env
FLASK_ENV=production
FLASK_DEBUG=False
API_HOST=0.0.0.0
API_PORT=5000
CACHE_TIMEOUT=3600
```

#### 3.2.2 Configuration Flask

Modifiez `main.py` :

```python
from src.api import *
import os

def main():
    host = os.getenv('API_HOST', '127.0.0.1')
    port = int(os.getenv('API_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False') == 'True'
    
    Yui.app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    main()
```

### 3.3 Déploiement en production

#### 3.3.1 Avec Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 main:Yui.app
```

#### 3.3.2 Avec Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

COPY . .
EXPOSE 5000

CMD ["python", "main.py"]
```

---

## 4. Référence API

### 4.1 Base URL

```
http://127.0.0.1:5000
```

### 4.2 Endpoints détaillés

#### 4.2.1 GET /

**Description** : Endpoint de test

**Paramètres**

| Nom | Type | Requis | Description |
|-----|------|--------|-------------|
| `q` | string | Oui | Texte de test |

**Exemple de requête**

```bash
curl "http://127.0.0.1:5000/?q=test"
```

**Réponse 200 OK**

```json
{
  "Bonjours": "Je suis une api...",
  "Valeur q": "test",
  "Cardinal value": "Cardinal.test()"
}
```

**Codes d'erreur**

- `400` : Paramètre 'q' manquant

---

#### 4.2.2 GET /api/getAllAnime

**Description** : Récupère et met en cache tous les animes du catalogue

**Paramètres**

| Nom | Type | Requis | Description | Valeur par défaut |
|-----|------|--------|-------------|-------------------|
| `r` | string | Non | Force le rafraîchissement | `False` |

**Comportement**

- Si `r=True` : Scrape complet du catalogue (peut prendre plusieurs minutes)
- Si `r=False` ou absent : Utilise le cache si disponible

**Exemple de requête**

```bash
# Utiliser le cache
curl "http://127.0.0.1:5000/api/getAllAnime"

# Forcer le rafraîchissement
curl "http://127.0.0.1:5000/api/getAllAnime?r=True"
```

**Réponse 200 OK**

```json
"Recuperation achever"
```

ou

```json
"Fichier déjà existant ajouté l'argument = r=True pour tous actualiser"
```

**Durée estimée**

- Cache : < 1 seconde
- Scraping complet : 2-5 minutes (dépend du nombre de pages)

**Notes importantes**

⚠️ Le scraping complet charge toutes les pages du catalogue. Utilisez `r=True` uniquement si nécessaire.

---

#### 4.2.3 GET /api/loadBaseAnimeData

**Description** : Charge les données d'animes depuis le cache

**Paramètres** : Aucun

**Exemple de requête**

```bash
curl "http://127.0.0.1:5000/api/loadBaseAnimeData"
```

**Réponse 200 OK**

```json
[
  {
    "title": "Frieren",
    "AlterTitle": "Sousou no Frieren",
    "link": "https://anime-sama.fr/catalogue/frieren/"
  },
  {
    "title": "One Piece",
    "AlterTitle": "ワンピース",
    "link": "https://anime-sama.fr/catalogue/one-piece/"
  }
]
```

**Codes d'erreur**

- `200` avec message : "Fichier non existant..." si aucun cache n'existe

---

#### 4.2.4 GET /api/getSerchAnime

**Description** : Recherche d'animes avec algorithme de correspondance floue

**Paramètres**

| Nom | Type | Requis | Description | Valeur par défaut |
|-----|------|--------|-------------|-------------------|
| `q` | string | Oui | Terme de recherche | - |
| `l` | integer | Non | Nombre de résultats | 5 |

**Algorithme de recherche**

L'API utilise RapidFuzz avec scoring personnalisé :

1. **Score de base** : `fuzz.token_set_ratio` (0-100)
2. **Bonus/Malus** :
   - +10 points si longueur titre ≈ longueur recherche (90-110%)
   - -15 points si titre trop court (<50% recherche)
3. **Seuil minimum** : 75 points

**Exemple de requête**

```bash
# Recherche basique
curl "http://127.0.0.1:5000/api/getSerchAnime?q=Frieren"

# Recherche avec limite
curl "http://127.0.0.1:5000/api/getSerchAnime?q=demon%20slayer&l=10"
```

**Réponse 200 OK**

```json
[
  {
    "title": "Frieren",
    "lien": "https://anime-sama.fr/catalogue/frieren/",
    "score": 95
  },
  {
    "title": "Frieren: Beyond Journey's End",
    "lien": "https://anime-sama.fr/catalogue/frieren-beyond/",
    "score": 88
  }
]
```

**Caractéristiques**

- ✅ Insensible à la casse
- ✅ Ignore la ponctuation
- ✅ Tolère les fautes de frappe minime
- ✅ Recherche par titre original
- ✅ Dédoublonnage automatique

**Codes d'erreur**

- `400` : Paramètre 'q' manquant
- `200` avec `[]` : Aucun résultat trouvé

---

#### 4.2.5 GET /api/getInfoAnime

**Description** : Récupère les informations détaillées d'un anime (saisons disponibles)

**Paramètres**

| Nom | Type | Requis | Description |
|-----|------|--------|-------------|
| `q` | string | Oui | Nom de l'anime |

**Exemple de requête**

```bash
curl "http://127.0.0.1:5000/api/getInfoAnime?q=Frieren"
```

**Réponse 200 OK**

```json
[
  {
    "base_url": "https://anime-sama.fr/catalogue/frieren/",
    "title": "Frieren",
    "Saison": "saison1",
    "url": "https://anime-sama.fr/catalogue/frieren/saison1"
  },
  {
    "base_url": "https://anime-sama.fr/catalogue/frieren/",
    "title": "Frieren",
    "Saison": "saison2",
    "url": "https://anime-sama.fr/catalogue/frieren/saison2"
  }
]
```

**Détails techniques**

- Utilise le premier résultat de `getSerchAnime`
- Parse le JavaScript de la page pour extraire les saisons
- Regex utilisée : `panneauAnime\("([^"]+)",\s*"([^"]+)"\)`

**Codes d'erreur**

- `400` : Paramètre 'q' manquant

---

#### 4.2.6 GET /api/getAnimeLink

**Description** : Récupère tous les liens de streaming pour une saison donnée

**Paramètres**

| Nom | Type | Requis | Description | Valeur par défaut |
|-----|------|--------|-------------|-------------------|
| `n` | string | Oui | Nom de l'anime | - |
| `s` | string | Non | Numéro de saison | `saison1` |
| `v` | string | Non | Version linguistique | `vostfr` |

**Valeurs acceptées**

- **Saison** : `saison1`, `saison2`, ..., `film`, `oav`
- **Version** : `vostfr`, `vf`

**Exemple de requête**

```bash
# Configuration par défaut (saison1 vostfr)
curl "http://127.0.0.1:5000/api/getAnimeLink?n=Frieren"

# Configuration personnalisée
curl "http://127.0.0.1:5000/api/getAnimeLink?n=Demon%20Slayer&s=saison2&v=vf"
```

**Réponse 200 OK**

```json
[
  {
    "episode": 0,
    "url": "https://video.sibnet.ru/shell.php?videoid=5234567"
  },
  {
    "episode": 1,
    "url": "https://video.sibnet.ru/shell.php?videoid=5234568"
  },
  {
    "episode": 2,
    "url": "https://video.sibnet.ru/shell.php?videoid=5234569"
  }
]
```

**Processus de récupération**

```
1. Récupération du fichier episodes.js
2. Parsing des variables (eps1, eps2, ...)
3. Test de chaque lien :
   - Vérification HTTP (status 200)
   - Validation du domaine (whitelist)
4. Si échec : fallback sur autres lecteurs
5. Si toujours échec : extraction M3U8 via Playwright
6. Tri par numéro d'épisode
```

**Domaines autorisés**

- `video.sibnet.ru`

**Durée de traitement**

- Cas optimal : 5-10 secondes
- Avec fallback : 30-60 secondes
- Avec Playwright : 2-5 minutes

**Codes d'erreur**

- `400` : Paramètre 'n' manquant

---

## 5. Guide d'utilisation

### 5.1 Workflow typique

#### Étape 1 : Initialisation du cache

```bash
# Première utilisation uniquement
curl "http://127.0.0.1:5000/api/getAllAnime"
```

#### Étape 2 : Recherche d'un anime

```python
import requests

def search_anime(query):
    response = requests.get(
        "http://127.0.0.1:5000/api/getSerchAnime",
        params={"q": query, "l": 5}
    )
    return response.json()

results = search_anime("Demon Slayer")
print(f"Trouvé {len(results)} résultats")

for anime in results:
    print(f"- {anime['title']} (score: {anime['score']})")
```

#### Étape 3 : Récupération des informations

```python
def get_anime_info(anime_name):
    response = requests.get(
        "http://127.0.0.1:5000/api/getInfoAnime",
        params={"q": anime_name}
    )
    return response.json()

info = get_anime_info(results[0]['title'])
print(f"Saisons disponibles : {len(info)}")
```

#### Étape 4 : Obtention des liens de streaming

```python
def get_streaming_links(anime_name, season="saison1", version="vostfr"):
    response = requests.get(
        "http://127.0.0.1:5000/api/getAnimeLink",
        params={"n": anime_name, "s": season, "v": version}
    )
    return response.json()

links = get_streaming_links(results[0]['title'], "saison1", "vostfr")
print(f"Nombre d'épisodes : {len(links)}")

for episode in links:
    print(f"Épisode {episode['episode'] + 1} : {episode['url']}")
```

### 5.2 Exemple complet : Application CLI

```python
import requests
from typing import List, Dict

class AnimeAPI:
    BASE_URL = "http://127.0.0.1:5000"
    
    def __init__(self):
        self.session = requests.Session()
    
    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Recherche d'animes"""
        response = self.session.get(
            f"{self.BASE_URL}/api/getSerchAnime",
            params={"q": query, "l": limit}
        )
        response.raise_for_status()
        return response.json()
    
    def get_info(self, anime_name: str) -> List[Dict]:
        """Informations sur un anime"""
        response = self.session.get(
            f"{self.BASE_URL}/api/getInfoAnime",
            params={"q": anime_name}
        )
        response.raise_for_status()
        return response.json()
    
    def get_links(self, anime_name: str, season: str = "saison1", 
                  version: str = "vostfr") -> List[Dict]:
        """Liens de streaming"""
        response = self.session.get(
            f"{self.BASE_URL}/api/getAnimeLink",
            params={"n": anime_name, "s": season, "v": version}
        )
        response.raise_for_status()
        return response.json()

# Utilisation
if __name__ == "__main__":
    api = AnimeAPI()
    
    # Recherche
    query = input("Rechercher un anime : ")
    results = api.search(query)
    
    if not results:
        print("Aucun résultat trouvé")
        exit()
    
    # Affichage des résultats
    print("\nRésultats :")
    for i, anime in enumerate(results, 1):
        print(f"{i}. {anime['title']} (score: {anime['score']})")
    
    # Sélection
    choice = int(input("\nChoisir un anime (numéro) : ")) - 1
    selected = results[choice]
    
    # Informations
    info = api.get_info(selected['title'])
    print(f"\nSaisons disponibles pour {selected['title']} :")
    for season_info in info:
        print(f"- {season_info['Saison']}")
    
    # Récupération des liens
    season = input("\nSaison (ex: saison1) : ") or "saison1"
    version = input("Version (vostfr/vf) : ") or "vostfr"
    
    print("\nRécupération des liens...")
    links = api.get_links(selected['title'], season, version)
    
    print(f"\n{len(links)} épisodes disponibles :")
    for ep in links:
        print(f"Épisode {ep['episode'] + 1} : {ep['url']}")
```

### 5.3 Exemple JavaScript (Frontend)

```javascript
class AnimeAPI {
    constructor(baseUrl = 'http://127.0.0.1:5000') {
        this.baseUrl = baseUrl;
    }
    
    async search(query, limit = 5) {
        const response = await fetch(
            `${this.baseUrl}/api/getSerchAnime?q=${encodeURIComponent(query)}&l=${limit}`
        );
        if (!response.ok) throw new Error('Search failed');
        return await response.json();
    }
    
    async getInfo(animeName) {
        const response = await fetch(
            `${this.baseUrl}/api/getInfoAnime?q=${encodeURIComponent(animeName)}`
        );
        if (!response.ok) throw new Error('Failed to get info');
        return await response.json();
    }
    
    async getLinks(animeName, season = 'saison1', version = 'vostfr') {
        const response = await fetch(
            `${this.baseUrl}/api/getAnimeLink?n=${encodeURIComponent(animeName)}&s=${season}&v=${version}`
        );
        if (!response.ok) throw new Error('Failed to get links');
        return await response.json();
    }
}

// Utilisation
const api = new AnimeAPI();

// Recherche avec affichage
async function searchAndDisplay() {
    try {
        const results = await api.search('Frieren');
        
        const listElement = document.getElementById('anime-list');
        listElement.innerHTML = '';
        
        results.forEach(anime => {
            const item = document.createElement('div');
            item.className = 'anime-item';
            item.innerHTML = `
                <h3>${anime.title}</h3>
                <p>Score : ${anime.score}</p>
                <button onclick="loadAnime('${anime.title}')">
                    Voir les épisodes
                </button>
            `;
            listElement.appendChild(item);
        });
    } catch (error) {
        console.error('Erreur :', error);
    }
}

async function loadAnime(title) {
    try {
        const links = await api.getLinks(title);
        
        const episodeList = document.getElementById('episode-list');
        episodeList.innerHTML = '';
        
        links.forEach(ep => {
            const item = document.createElement('div');
            item.innerHTML = `
                <a href="${ep.url}" target="_blank">
                    Épisode ${ep.episode + 1}
                </a>
            `;
            episodeList.appendChild(item);
        });
    } catch (error) {
        console.error('Erreur :', error);
    }
}
```

---

## 6. Modules et classes

### 6.1 Classe Cardinal (backend.py)

Classe principale contenant toute la logique métier.

#### 6.1.1 getAllAnime(reset="False")

```python
def getAllAnime(reset="False"):
    """
    Scrape tous les animes du catalogue Anime-Sama
    
    Args:
        reset (str): "True" pour forcer le rafraîchissement
    
    Returns:
        str: Message de statut
    
    Process:
        1. Vérifie l'existence du cache
        2. Si nécessaire, scrape chaque page du catalogue
        3. Pour chaque anime :
           - Extrait le titre principal
           - Récupère le titre alternatif
           - Sauvegarde l'URL
        4. Écrit dans AnimeInfo.json
    """
```

**Structure de sortie (AnimeInfo.json)**

```json
[
  {
    "title": "Titre principal",
    "AlterTitle": "Titre alternatif",
    "link": "https://anime-sama.fr/catalogue/..."
  }
]
```

#### 6.1.2 loadBaseAnimeData()

```python
def loadBaseAnimeData():
    """
    Charge les données depuis le cache
    
    Returns:
        list: Liste des animes ou message d'erreur
    """
```

#### 6.1.3 clean_string(text)

```python
@staticmethod
def clean_string(text):
    """
    Normalise une chaîne pour la recherche
    
    Args:
        text (str): Texte à nettoyer
    
    Returns:
        str: Texte normalisé
    
    Transformations:
        - Conversion en minuscules
        - Suppression de la ponctuation
        - Normalisation des espaces
        - Suppression des caractères spéciaux
    
    Exemples:
        "Demon Slayer: Kimetsu no Yaiba!" -> "demon slayer kimetsu no yaiba"
        "One-Piece" -> "one piece"
    """
```

#### 6.1.4 serchAnime(search, limit)

```python
def serchAnime(search, limit):
    """
    Recherche d'animes avec scoring intelligent
    
    Args:
        search (str): Terme de recherche
        limit (int): Nombre max de résultats
    
    Returns:
        list: Résultats triés par score
    
    Algorithme:
        1. Nettoyage du terme de recherche
        2. Création de maps titre -> info
        3. RapidFuzz token_set_ratio (top 15)
        4. Calcul du bonus/malus de spécificité
        5. Tri par score final
        6. Dédoublonnage
        7. Application de la limite
    
    Scoring:
        - Base : fuzz.token_set_ratio (0-100)
        - Bonus : +10 si longueur ≈ recherche
        - Malus : -15 si titre trop court
        - Seuil : 75 minimum
    """
```

#### 6.1.5 getInfoAnime(querry)

```python
def getInfoAnime(querry):
    """
    Extrait les informations de saisons
    
    Args:
        querry (str): Nom de l'anime
    
    Returns:
        list: Liste des saisons avec URLs
    
    Process:
        1. Recherche de l'anime
        2. Récupération de la page principale
        3. Parsing des scripts JS
        4. Extraction regex des appels panneauAnime()
        5. Construction des URLs de saison
    """
```

#### 6.1.6 getAnimeLink(nom, saison, version)

```python
def getAnimeLink(nom, saison, version):
    """
    Récupère tous les liens de streaming
    
    Args:
        nom (str): Nom de l'anime
        saison (str): Numéro de saison
        version (str): Version linguistique
    
    Returns:
        list: Liste des épisodes avec URLs
    
    Process (complexe):
        1. Construction de l'URL de saison
        2. Récupération du fichier episodes.js
        3. Parsing des variables eps1, eps2, ...
        4. Test de chaque lien (lecteur 1)
        5. Si erreurs : fallback sur autres lecteurs
        6. Si toujours erreurs : extraction M3U8
        7. Tri final par numéro d'épisode
    
    Fallback Strategy:
        Lecteur 1 → Lecteur 2 → ... → Lecteur N → Playwright M3U8
    
    Whitelist domains:
        - video.sibnet.ru
    """
```

### 6.2 Classe Mita (Mita.py)

Utilitaires pour l'interaction avec le navigateur.

#### 6.2.1 find_browser_profile()

```python
@staticmethod
def find_browser_profile():
    """
    Localise le profil Edge ou Chrome
    
    Returns:
        tuple: (chemin_profil, nom_navigateur)
    
    Ordre de priorité:
        1. Microsoft Edge
        2. Google Chrome
        3. None si aucun trouvé
    """
```

#### 6.2.2 get_available_episodes(page)

```python
@staticmethod
async def get_available_episodes(page):
    """
    Liste les épisodes disponibles
    
    Args:
        page: Instance Playwright Page
    
    Returns:
        list: [{"episode": int, "text": str}, ...]
    
    Sélecteur: #selectEpisodes > option
    """
```

#### 6.2.3 get_available_lecteurs(page)

```python
@staticmethod
async def get_available_lecteurs(page):
    """
    Liste les lecteurs disponibles
    
    Args:
        page: Instance Playwright Page
    
    Returns:
        list: ["Lecteur 1", "Lecteur 2", ...]
    
    Sélecteur: #selectLecteurs > option
    """
```

### 6.3 Module M3U8 (m3u8.py)

Extraction de liens vidéo via automatisation navigateur.

#### 6.3.1 log_error(anime_title, season_number, episode_number, error)

```python
def log_error(anime_title, season_number, episode_number, error):
    """
    Enregistre les erreurs dans error_log.txt
    
    Args:
        anime_title (str): Titre de l'anime
        season_number (str): Numéro de saison
        episode_number (int): Numéro d'épisode
        error (str): Message d'erreur
    
    Format: [TIMESTAMP] Échec pour ... : erreur
    """
```

#### 6.3.2 extract_m3u8_from_page(base_url, episode_numbers_to_find)

```python
async def extract_m3u8_from_page(base_url: str, 
                                 episode_numbers_to_find: list):
    """
    Extrait les liens M3U8 via Playwright
    
    Args:
        base_url (str): URL de la saison
        episode_numbers_to_find (list): Épisodes à récupérer
    
    Returns:
        list: [{"episode": int, "url": str}, ...]
    
    Process (pour chaque épisode):
        1. Lancement du navigateur headless
        2. Navigation vers la page
        3. Détection des lecteurs et épisodes
        4. Pour chaque lecteur :
           a. Sélection du lecteur
           b. Navigation clavier vers l'épisode
           c. Interception requête M3U8
           d. Si trouvé : ajout et passage au suivant
        5. Log des échecs
        6. Fermeture du navigateur
    
    Stratégies de sélection:
        1. Navigation clavier (ArrowDown/Up + Enter)
        2. Fallback JavaScript si échec
    
    Timeout:
        - Navigation : 60 secondes
        - Interception M3U8 : 30 secondes par épisode
    
    Anti-détection:
        - Profil persistant
        - Désactivation AutomationControlled
        - Override navigator.webdriver
    """
```

**Interception de requêtes**

```python
async def intercept_request(request):
    """Intercepte les requêtes contenant master.m3u8"""
    if "master.m3u8" in request.url and request.url not in captured_urls:
        pending_m3u8_url = request.url
        captured_urls.add(request.url)
        new_m3u8_event.set()

page.on("request", intercept_request)
```

---

## 7. Algorithmes et logique

### 7.1 Algorithme de recherche floue

#### Principes

L'API utilise **RapidFuzz** avec `token_set_ratio` pour une recherche tolérante aux fautes.

```python
# Exemple de scoring
search_term = "demon slayer"
titles = ["Demon Slayer", "Demon Slayer Season 2", "The Demon King"]

# Scores de base (token_set_ratio)
"Demon Slayer" → 100
"Demon Slayer Season 2" → 85
"The Demon King" → 67
```

#### Bonus de spécificité

```python
def calculate_specificity_bonus(cleaned_title, cleaned_search):
    length_ratio = len(cleaned_title) / len(cleaned_search)
    
    if 0.9 <= length_ratio <= 1.1:
        return 10  # Longueur similaire
    elif length_ratio < 0.5:
        return -15  # Titre trop court (probablement pas pertinent)
    else:
        return 0
```

**Exemples**

```
Recherche : "frieren" (7 caractères)

Titre : "Frieren" (7 chars)
- Ratio : 1.0
- Bonus : +10
- Score final : 100 + 10 = 110 ✅

Titre : "Frieren Beyond Journeys End" (27 chars)
- Ratio : 3.86
- Bonus : 0
- Score final : 85 + 0 = 85 ✅

Titre : "Frie" (4 chars)
- Ratio : 0.57
- Bonus : 0
- Score final : 80 + 0 = 80 ⚠️

Titre : "Fr" (2 chars)
- Ratio : 0.28
- Bonus : -15
- Score final : 75 - 15 = 60 ❌ (rejeté, < 75)
```

### 7.2 Algorithme de récupération de liens

#### Architecture en cascade

```
┌─────────────────────────────────────┐
│  1. Récupération episodes.js        │
│     - Parse des variables eps1..N   │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│  2. Test Lecteur 1 (tous épisodes)  │
│     - Requête HTTP                  │
│     - Vérif status 200              │
│     - Vérif domaine autorisé        │
└─────────────┬───────────────────────┘
              │
         Succès ?─┐
              │   └─> Retourner résultats
              ▼ Non
┌──────────────────────────────────────┐
│  3. Fallback Lecteurs 2..N           │
│     - Pour chaque erreur             │
│     - Test lecteur suivant           │
└─────────────┬────────────────────────┘
              │
         Succès ?─┐
              │   └─> Retourner résultats
              ▼ Non
┌──────────────────────────────────────┐
│  4. Extraction M3U8 (Playwright)     │
│     - Pour épisodes manquants        │
│     - Automatisation navigateur      │
└─────────────┬────────────────────────┘
              │
              ▼
         Tri et retour
```

#### Pseudo-code détaillé

```python
def getAnimeLink(nom, saison, version):
    # 1. Initialisation
    error_list = []
    good_links = []
    lecteur_actuel = "eps1"
    
    # 2. Récupération du fichier JS
    js_content = fetch_episodes_js(nom, saison, version)
    all_episodes = parse_js_variables(js_content)
    
    nombre_episodes = len(all_episodes["eps1"])
    nombre_lecteurs = count_lecteurs(all_episodes)
    
    # 3. Test lecteur 1
    for episode_index in range(nombre_episodes):
        url = all_episodes[lecteur_actuel][episode_index]
        
        if is_valid_link(url):
            good_links.append({
                "episode": episode_index,
                "url": url
            })
        else:
            error_list.append({
                "lecteur": lecteur_actuel,
                "episode": episode_index,
                "url": url
            })
    
    # 4. Si toutes les URLs OK, retour immédiat
    if len(good_links) == nombre_episodes:
        return sorted(good_links, key=lambda x: x['episode'])
    
    # 5. Fallback sur autres lecteurs
    for lecteur_num in range(2, nombre_lecteurs + 1):
        lecteur_courant = f"eps{lecteur_num}"
        
        for error in error_list.copy():
            ep_index = error['episode']
            url = all_episodes[lecteur_courant][ep_index]
            
            if is_valid_link(url):
                good_links.append({
                    "episode": ep_index,
                    "url": url
                })
                error_list.remove(error)
        
        # Sortie anticipée si tout OK
        if len(good_links) == nombre_episodes:
            return sorted(good_links, key=lambda x: x['episode'])
    
    # 6. Extraction M3U8 pour épisodes manquants
    episodes_trouves = [link['episode'] for link in good_links]
    episodes_manquants = [i for i in range(nombre_episodes) 
                          if i not in episodes_trouves]
    
    if episodes_manquants:
        # Conversion index → numéro épisode (+1)
        episode_numbers = [index + 1 for index in episodes_manquants]
        
        # Extraction Playwright
        m3u8_links = await extract_m3u8_from_page(
            construct_season_url(nom, saison, version),
            episode_numbers
        )
        
        # Ajustement index (-1) et fusion
        for link in m3u8_links:
            link['episode'] -= 1
            good_links.append(link)
    
    # 7. Tri final
    return sorted(good_links, key=lambda x: x['episode'])
```

### 7.3 Validation de liens

```python
def is_valid_link(url, headers, allowed_sites):
    """
    Valide un lien de streaming
    
    Critères:
        1. Status HTTP 200
        2. Domaine dans la whitelist
        3. Pas de timeout (10s)
    """
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # Vérification status
        if response.status_code != 200:
            return False
        
        # Vérification domaine
        is_allowed = any(site in url for site in allowed_sites)
        if not is_allowed:
            return False
        
        return True
        
    except requests.ConnectionError:
        return False
    except requests.Timeout:
        return False
```

---

## 8. Gestion des erreurs

### 8.1 Types d'erreurs

| Type | Code | Cause | Solution |
|------|------|-------|----------|
| **Paramètre manquant** | 400 | Paramètre requis absent | Ajouter le paramètre |
| **Cache vide** | 200 | AnimeInfo.json inexistant | Appeler `/api/getAllAnime` |
| **Aucun résultat** | 200 | Terme de recherche invalide | Modifier la recherche |
| **Timeout** | 500 | Serveur lent/indisponible | Réessayer plus tard |
| **Connection error** | 500 | Perte de connexion | Vérifier la connexion |

### 8.2 Logging

#### Fichier : error_log.txt

```
[2024-10-31 14:30:45] Échec pour Frieren saison1 Épisode : 5: Aucun M3U8 sur aucun lecteur
[2024-10-31 14:35:12] Échec pour One Piece saison1 Épisode : 1050: Timeout
```

#### Fonction de logging

```python
def log_error(anime_title, season_number, episode_number, error):
    log_file = os.path.join(PATH_DOWNLOAD, "error_log.txt")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] Échec pour {anime_title} {season_number} Épisode : {episode_number}: {error}\n"
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)
```

### 8.3 Gestion des exceptions

#### Dans l'API (api.py)

```python
@app.route('/api/getSerchAnime', methods=["GET"])
def serchAnime():
    try:
        querry = request.args.get("q", "").strip()
        limit = request.args.get("l", "").strip()

        if not querry:
            return jsonify({"error": "Paramètre 'q' manquant"}), 400
        
        try:
            limit = int(limit) if limit else 5
        except ValueError:
            limit = 5
        
        return jsonify(Cardinal.serchAnime(querry, limit))
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

#### Dans le backend (backend.py)

```python
def getAnimeLink(nom, saison, version):
    try:
        # Logique principale
        ...
    except requests.ConnectionError:
        error.append({
            "lecteur": lecteur,
            "episode": episode,
            "url": url
        })
        continue
    except Exception as e:
        log_error(nom, saison, episode, str(e))
        raise
```

### 8.4 Stratégies de retry

#### Retry avec backoff exponentiel

```python
import time

def retry_request(url, max_attempts=3):
    """Requête avec retry exponentiel"""
    for attempt in range(max_attempts):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response
        except requests.RequestException:
            if attempt < max_attempts - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait_time)
            else:
                raise
    
    return None
```

---

## 9. Performance et optimisation

### 9.1 Temps de réponse

| Endpoint | Cache HIT | Cache MISS | Notes |
|----------|-----------|------------|-------|
| `/api/loadBaseAnimeData` | < 100ms | N/A | Lecture fichier |
| `/api/getSerchAnime` | ~200ms | N/A | RapidFuzz |
| `/api/getInfoAnime` | ~1-2s | N/A | 1 scraping |
| `/api/getAnimeLink` | 5-10s | 30-60s | Multiple requêtes |
| `/api/getAllAnime` | < 1s | 2-5min | Scraping complet |

### 9.2 Optimisations implémentées

#### 9.2.1 Cache local

```python
# Évite le scraping répétitif
if os.path.exists(PATH_ANIME) and reset != "True":
    return "Fichier déjà existant..."
```

**Avantages :**
- Réduction de 99% du temps de réponse
- Diminution de la charge sur Anime-Sama
- Disponibilité hors-ligne

#### 9.2.2 Requêtes asynchrones (M3U8)

```python
# Extraction M3U8 en async
m3u8_links = asyncio.run(extract_m3u8_from_page(url, episodes))
```

**Gain :** Parallélisation possible des extractions futures

#### 9.2.3 Session pooling

```python
# Réutilisation des connexions HTTP
session = requests.Session()
session.get(url)  # Connection keepalive
```

### 9.3 Optimisations possibles

#### 9.3.1 Redis pour le cache

```python
import redis

class CacheManager:
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=0)
    
    def get_anime_list(self):
        cached = self.redis.get('anime_list')
        if cached:
            return json.loads(cached)
        
        # Sinon, scraping
        data = scrape_anime_list()
        self.redis.setex('anime_list', 3600, json.dumps(data))
        return data
```

**Avantages :**
- Cache distribué
- TTL automatique
- Performance accrue

#### 9.3.2 Rate limiting

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=Yui.app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/getAnimeLink')
@limiter.limit("10 per minute")
def getAnimeLink():
    ...
```

#### 9.3.3 Compression des réponses

```python
from flask_compress import Compress

compress = Compress()
compress.init_app(Yui.app)
```

**Gain :** Réduction de 60-80% de la taille des réponses JSON

#### 9.3.4 Parallélisation du scraping

```python
from concurrent.futures import ThreadPoolExecutor

def scrape_page(page_num):
    response = requests.get(f"https://anime-sama.fr/catalogue/?page={page_num}")
    return parse_page(response.content)

with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(scrape_page, range(1, 50)))
```

**Gain :** Réduction de 70% du temps de scraping complet

---

## 10. Sécurité

### 10.1 Vulnérabilités potentielles

#### 10.1.1 Injection de paramètres

**Problème :**
```python
querry = request.args.get("q", "")
# Utilisé directement dans requests.get()
```

**Solution :**
```python
import re

def sanitize_input(text):
    """Nettoie les entrées utilisateur"""
    # Autorise uniquement alphanumérique et espaces
    return re.sub(r'[^a-zA-Z0-9\s\-]', '', text)

querry = sanitize_input(request.args.get("q", ""))
```

#### 10.1.2 CORS

**Problème :** Par défaut, l'API n'accepte pas les requêtes cross-origin

**Solution :**
```python
from flask_cors import CORS

# Autoriser tous les domaines (développement)
CORS(Yui.app)

# Ou restreindre (production)
CORS(Yui.app, resources={
    r"/api/*": {
        "origins": ["https://votredomaine.com"]
    }
})
```

#### 10.1.3 Rate limiting (DoS)

**Problème :** Possibilité d'abus avec requêtes massives

**Solution :**
```python
from flask_limiter import Limiter

limiter = Limiter(
    app=Yui.app,
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379"
)

@app.route('/api/getAnimeLink')
@limiter.limit("10/minute")
def getAnimeLink():
    ...
```

### 10.2 Bonnes pratiques

#### 10.2.1 Headers sécurisés

```python
from flask_talisman import Talisman

Talisman(Yui.app, 
    content_security_policy=None,  # À configurer selon besoin
    force_https=True
)
```

#### 10.2.2 Validation stricte

```python
ALLOWED_SEASONS = ['saison1', 'saison2', 'saison3', 'saison4', 'film']
ALLOWED_VERSIONS = ['vostfr', 'vf']

def getAnimeLink():
    saison = request.args.get("s", "saison1")
    version = request.args.get("v", "vostfr")
    
    if saison not in ALLOWED_SEASONS:
        return jsonify({"error": "Saison invalide"}), 400
    
    if version not in ALLOWED_VERSIONS:
        return jsonify({"error": "Version invalide"}), 400
    
    ...
```

#### 10.2.3 Authentification (optionnel)

```python
from functools import wraps

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key != os.getenv('API_KEY'):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/getAnimeLink')
@require_api_key
def getAnimeLink():
    ...
```

### 10.3 Protection des données

#### 10.3.1 Pas de stockage de données sensibles

L'API ne stocke que :
- Titres d'animes (publics)
- URLs publiques
- Logs d'erreurs techniques

#### 10.3.2 HTTPS obligatoire en production

```python
# Dans nginx
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
    }
}
```

---

## 11. FAQ

### 11.1 Questions générales

**Q : L'API est-elle gratuite ?**
R : Oui, l'API est open-source et gratuite à utiliser.

**Q : Puis-je utiliser l'API commercialement ?**
R : Vérifiez les conditions d'utilisation d'Anime-Sama et respectez les droits d'auteur.

**Q : Quelle est la limite de requêtes ?**
R : Par défaut, aucune limite. Implémentez un rate limiting si nécessaire.

### 11.2 Problèmes techniques

**Q : "Fichier non existant" lors de la recherche**
```bash
# Solution
curl "http://127.0.0.1:5000/api/getAllAnime"
# Attendez la fin du scraping
```

**Q : Playwright ne trouve pas Chromium**
```bash
# Solution
playwright install chromium --force
```

**Q : Les liens M3U8 ne fonctionnent pas**
R : Les liens M3U8 sont temporaires et peuvent expirer. Récupérez-les juste avant utilisation.

**Q : L'extraction M3U8 est lente**
R : C'est normal, Playwright simule un navigateur complet. Comptez 2-5 minutes pour une saison complète.

**Q : Erreur "Connection refused"**
R : Vérifiez que le serveur Flask est démarré sur le bon port.

### 11.3 Utilisation avancée

**Q : Comment télécharger les épisodes ?**
```python
import requests

def download_episode(url, output_path):
    response = requests.get(url, stream=True)
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

# Utilisation
links = api.get_links("Frieren")
download_episode(links[0]['url'], "episode_1.mp4")
```

**Q : Comment créer une playlist M3U ?**
```python
def create_m3u_playlist(links, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for link in links:
            f.write(f"#EXTINF:-1,Episode {link['episode'] + 1}\n")
            f.write(f"{link['url']}\n")

links = api.get_links("Frieren")
create_m3u_playlist(links, "frieren_s1.m3u")
```

**Q : Comment gérer plusieurs versions simultanées ?**
```python
async def get_all_versions(anime_name, season):
    versions = ['vostfr', 'vf']
    results = {}
    
    for version in versions:
        try:
            links = api.get_links(anime_name, season, version)
            results[version] = links
        except:
            results[version] = []
    
    return results
```

### 11.4 Dépannage

**Q : Le scraping ne trouve aucun anime**
R : Vérifiez que Anime-Sama est accessible et que la structure HTML n'a pas changé.

**Q : RapidFuzz ne trouve aucun résultat**
R : Le terme de recherche est probablement trop éloigné des titres. Essayez des termes plus courts ou différents.

**Q : Status 403 sur les liens vidéo**
R : Les headers sont peut-être obsolètes. Mettez à jour les headers dans `backend.py`.

**Q : Playwright bloque sur headless=True**
R : Certains sites détectent le mode headless. Essayez `headless=False` en développement.

---

## Annexes

### A. Structure complète du projet

```
anime-api/
├── main.py                     # Entry point
├── requirements.txt            # Dépendances
├── .env                       # Variables d'environnement (optionnel)
├── .gitignore
├── README.md
├── DOCUMENTATION.md            # Ce fichier
├── LICENSE
│
├── src/
│   ├── __init__.py
│   ├── api.py                 # Routes Flask
│   ├── backend.py             # Logique métier (Cardinal)
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── Mita.py           # Utilitaires navigateur
│   │   └── m3u8.py           # Extraction M3U8
│   │
│   ├── data/
│   │   └── json/
│   │       └── AnimeInfo.json # Cache (généré)
│   │
│   └── Dist/
│       └── error_log.txt     # Logs (généré)
│
└── tests/                     # Tests unitaires (à créer)
    ├── __init__.py
    ├── test_api.py
    ├── test_backend.py
    └── test_m3u8.py
```

### B. Exemples de fichiers de configuration

#### B.1 requirements.txt

```txt
Flask==3.0.0
requests==2.31.0
beautifulsoup4==4.12.2
lxml==5.1.0
rapidfuzz==3.6.1
playwright==1.41.0
python-dotenv==1.0.0
flask-cors==4.0.0
flask-limiter==3.5.0
gunicorn==21.2.0
```

#### B.2 .env

```env
FLASK_ENV=development
FLASK_DEBUG=True
API_HOST=127.0.0.1
API_PORT=5000
CACHE_TTL=3600
MAX_WORKERS=4
```

#### B.3 .gitignore

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/

# Data
src/data/json/AnimeInfo.json
src/Dist/error_log.txt

# IDE
.vscode/
.idea/
*.swp

# Env
.env
.env.local

# OS
.DS_Store
Thumbs.db
```

### C. Exemples de tests

#### C.1 test_api.py

```python
import unittest
from src.api import Yui

class TestAPI(unittest.TestCase):
    
    def setUp(self):
        self.app = Yui.app.test_client()
        self.app.testing = True
    
    def test_home_without_param(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 400)
    
    def test_home_with_param(self):
        response = self.app.get('/?q=test')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('Bonjours', data)
    
    def test_search_anime(self):
        response = self.app.get('/api/getSerchAnime?q=Frieren&l=5')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)

if __name__ == '__main__':
    unittest.main()
```

### D. Commandes utiles

```bash
# Démarrage du serveur
python main.py

# Avec Gunicorn (production)
gunicorn -w 4 -b 0.0.0.0:5000 "src.api:Yui.app"

# Tests
python -m unittest discover tests

# Vérification du code
flake8 src/
pylint src/

# Installation de Playwright
playwright install chromium

# Mise à jour des dépendances
pip install --upgrade -r requirements.txt
```

### E. Ressources externes

- [Documentation Flask](https://flask.palletsprojects.com/)
- [Playwright Python](https://playwright.dev/python/)
- [RapidFuzz](https://github.com/maxbachmann/RapidFuzz)
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Requests](https://requests.readthedocs.io/)

---

**Version de la documentation :** 1.0.1 
**Dernière mise à jour :** 11 Novembre 2024  
**Auteur :** TMCooper 
**Licence :** MIT

(La documentation a été faite avec l'IA)