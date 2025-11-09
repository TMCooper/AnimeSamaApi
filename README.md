# Documentation API Anime

## Table des matières

1. [Présentation](#présentation)
2. [Installation](#installation)
3. [Architecture du projet](#architecture-du-projet)
4. [Démarrage rapide](#démarrage-rapide)
5. [Endpoints de l'API](#endpoints-de-lapi)
6. [Exemples d'utilisation](#exemples-dutilisation)
7. [Gestion des erreurs](#gestion-des-erreurs)
8. [Limitations et notes techniques](#limitations-et-notes-techniques)

---

## Présentation

Cette API REST permet de rechercher, récupérer et accéder aux informations d'animes depuis le site anime-sama.org. Elle propose des fonctionnalités de recherche intelligente, de récupération de métadonnées et d'extraction de liens de lecture.

### Fonctionnalités principales

- Catalogue complet d'animes avec titres alternatifs
- Recherche floue avec scoring intelligent
- Récupération d'informations détaillées par anime
- Extraction automatique des liens M3U8 pour le streaming
- Support multi-saisons et multi-versions (VOSTFR/VF)
- L'api peut toute a fait traité les saison / film / oav t'en qu'il existe

---

## Potentiel nouvelle feature
- Scan support ?
- Ou vous pouvez en suggerer vous même [ici](https://github.com/TMCooper/Anime-Sama-Downloader/discussions/categories/ideas)

## Installation

### Prérequis

- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)

### Dépendances

Installez les dépendances nécessaires :

```cmd
pip install -r requirements.txt
```

Pour l'extraction M3U8 (fonctionnalité avancée), installez Chromium pour Playwright :

```cmd
playwright install chromium
```

### Structure des fichiers

Assurez-vous que votre projet respecte cette structure :

```
projet/
├── main.py
├── src/
│   ├── api.py
│   ├── backend.py
│   └── utils/
│       ├── m3u8.py
│       └── Mita.py
└── data/
    └── json/
        └── AnimeInfo.json (généré automatiquement)
```

---

## Architecture du projet

### Composants principaux

| Fichier | Rôle |
|---------|------|
| `main.py` | Point d'entrée de l'application |
| `api.py` | Définition des routes Flask |
| `backend.py` | Logique métier et scraping |
| `m3u8.py` | Extraction des liens M3U8 via Playwright |
| `Mita.py` | Utilitaires pour l'automatisation navigateur |

### Flux de données

```
Requête HTTP → Flask (api.py) → Cardinal (backend.py) → Scraping/Recherche → Réponse JSON
```

---

## Démarrage rapide

### Lancer l'API

```python
python main.py
```

Par défaut, l'API démarre sur `http://127.0.0.1:5000` en mode debug.

### Configuration personnalisée

```python
from main import Api

# Lancer sur un port différent sans debug
Api.launch(port=5001, debug_state=False, reload_status=False)
```

### Première utilisation

Avant d'utiliser les fonctions de recherche, initialisez la base de données :

```cmd
curl "http://127.0.0.1:5000/api/getAllAnime"
```

**Attention** : Cette opération peut prendre plusieurs minutes lors de la première exécution.

---

## Endpoints de l'API

### 1. Route de test

**GET** `/`

Vérifie que l'API fonctionne correctement.

**Paramètres** :
- `q` (obligatoire) : Chaîne de test

**Exemple** :
```
http://127.0.0.1:5000/?q=test
```

**Réponse** :
```json
{
  "Bonjours": "Je suis une api...",
  "Valeur q": "test",
  "Cardinal value": "Cardinal.test()"
}
```

---

### 2. Récupération du catalogue complet

**GET** `/api/getAllAnime`

Scrap et stocke tous les animes disponibles dans un fichier JSON local.

**Paramètres** :
- `r` (optionnel) : `True` pour forcer la mise à jour du catalogue entier

**Exemple** :
```
http://127.0.0.1:5000/api/getAllAnime?r=True
```

**Réponse** :
```json
"Recuperation achever"
```

**Note** : Le fichier généré se trouve dans `data/json/AnimeInfo.json` et contient environ 4000+ animes comprenner que cela puisse prendre du temps au premier lancement ainsi que les reset.

---

### 3. Chargement de la base locale

**GET** `/api/loadBaseAnimeData`

Retourne le contenu du fichier `AnimeInfo.json`.

**Exemple** :
```
http://127.0.0.1:5000/api/loadBaseAnimeData
```

**Réponse** :
```json
[
  {
    "title": "Frieren",
    "AlterTitle": "Sousou no Frieren",
    "link": "https://anime-sama.org/catalogue/frieren/"
  },
  ...
]
```

---

### 4. Recherche d'animes

**GET** `/api/getSerchAnime`

Recherche des animes par nom avec algorithme de correspondance floue.

**Paramètres** :
- `q` (obligatoire) : Terme de recherche
- `l` (optionnel) : Limite de résultats (défaut : 5)

**Exemple** :
```
http://127.0.0.1:5000/api/getSerchAnime?q=Frieren&l=3
```

**Réponse** :
```json
[
  {
    "title": "Frieren",
    "lien": "https://anime-sama.org/catalogue/frieren/",
    "score": 95
  },
  {
    "title": "Sousou No Frieren",
    "lien": "https://anime-sama.org/catalogue/sousou-no-frieren/",
    "score": 88
  }
]
```

**Algorithme de scoring** :
- Score de base : similarité token_set_ratio (RapidFuzz)
- Bonus de spécificité : +10 si longueur similaire (ratio 0.9-1.1)
- Pénalité : -15 si titre trop court (ratio < 0.5)
- Seuil minimum : 75

---

### 5. Informations détaillées d'un anime

**GET** `/api/getInfoAnime`

Récupère toutes les saisons disponibles pour un anime.

**Paramètres** :
- `q` (obligatoire) : Nom de l'anime

**Exemple** :
```
http://127.0.0.1:5000/api/getInfoAnime?q=Demon Slayer
```

**Réponse** :
```json
[
  {
    "base_url": "https://anime-sama.org/catalogue/demon-slayer/",
    "title": "Demon Slayer",
    "Saison": "Saison 1",
    "url": "https://anime-sama.org/catalogue/demon-slayer/saison1/"
  },
  {
    "base_url": "https://anime-sama.org/catalogue/demon-slayer/",
    "title": "Demon Slayer",
    "Saison": "Saison 2",
    "url": "https://anime-sama.org/catalogue/demon-slayer/saison2/"
  }
]
```

---

### 6. Récupération d'une saison spécifique

**GET** `/api/getSpecificAnime`

Retourne les informations d'une saison particulière.

**Paramètres** :
- `q` (obligatoire) : Nom de l'anime
- `s` (optionnel) : Saison (défaut : `saison1`)
- `v` (optionnel) : Version (défaut : `vostfr`)

**Exemple** :
```
http://127.0.0.1:5000/api/getSpecificAnime?q=One%20Piece&s=saison1&v=vostfr
```

**Réponse** :
```json
{
  "base_url": "https://anime-sama.org/catalogue/one-piece/",
  "title": "One Piece",
  "Saison": "Saison 1",
  "url": "https://anime-sama.org/catalogue/one-piece/saison1/vostfr"
}
```

---

### 7. Extraction des liens de streaming

**GET** `/api/getAnimeLink`

Récupère tous les liens de streaming pour une saison complète.

**Paramètres** :
- `n` (obligatoire) : Nom de l'anime
- `s` (optionnel) : Saison (défaut : `saison1`)
- `v` (optionnel) : Version (défaut : `vostfr`)

**Exemple** :
```
http://127.0.0.1:5000/api/getAnimeLink?n=Spy%20x%20Family&s=saison1&v=vostfr
```

**Réponse** :
```json
[
  {
    "episode": 0,
    "url": "https://..."
  },
  {
    "episode": 1,
    "url": "https://..."
  }
]
```

**Note** : Cette fonction tente plusieurs lecteurs et sources pour garantir la disponibilité de tous les épisodes.

---

## Exemples d'utilisation

### Exemple : Rechercher et récupérer un anime

```python
import requests

# 1. Rechercher l'anime
response = requests.get("http://127.0.0.1:5000/api/getSerchAnime?q=Attack%20on%20Titan&l=1")
results = response.json()
print(f"Trouvé : {results[0]['title']}")

# 2. Récupérer les saisons
anime_name = results[0]['title']
response = requests.get(f"http://127.0.0.1:5000/api/getInfoAnime?q={anime_name}")
seasons = response.json()
print(f"Saisons disponibles : {len(seasons)}")

# 3. Obtenir les liens de la saison 1
response = requests.get(f"http://127.0.0.1:5000/api/getAnimeLink?n={anime_name}&s=saison1")
links = response.json()
print(f"Épisodes disponibles : {len(links)}")
```

---

## Gestion des erreurs

### Codes d'erreur HTTP

| Code | Signification | Exemple |
|------|---------------|---------|
| 200 | Succès | Données retournées correctement |
| 400 | Paramètre manquant | `{"error": "Paramètre 'q' manquant"}` |
| 500 | Erreur serveur | Problème de scraping ou de connexion |

### Erreurs courantes

**1. Base de données non initialisée**

```json
"Fichier non existant velliez request : http://127.0.0.1:5000/api/getAllAnime"
```

**Solution** : Exécutez d'abord `/api/getAllAnime` pour créer la base locale.

**2. Aucun résultat de recherche**

```json
[]
```

**Causes possibles** :
- Orthographe incorrecte (l'algorithme tolère certaines erreurs)
- Anime non présent dans le catalogue
- Score de similarité < 75

**3. Timeout lors de l'extraction M3U8**

```
Timeout sur Lecteur 2
```

**Cause** : Le lecteur sélectionné ne répond pas dans les 15 secondes.

**Solution** : L'API teste automatiquement les autres lecteurs disponibles.

---

## Limitations et notes techniques

### Performance

- **Première récupération du catalogue** : 10-20 minutes (4000+ animes)
- **Recherche** : < 1 seconde
- **Extraction de liens** : 2-5 secondes par saison (sans M3U8)
- **Extraction M3U8** : 15-30 secondes par épisode manquant

### Restrictions

1. **Taux de requêtes** : Pas de limite implémentée, mais Cloudflare peut bloquer en cas d'abus, il en va de même pour le site que l'on request un cooldown est présent pour evité ça
2. **Dépendance externe** : Nécessite que anime-sama.org soit accessible

### Stratégie de fallback

L'endpoint `/api/getAnimeLink` implémente une stratégie en cascade :

1. Tente le lecteur par défaut (eps1)
2. En cas d'échec, teste tous les lecteurs disponibles
3. Pour les épisodes manquants, lance l'extraction via Playwright
4. Retourne tous les liens trouvés triés par numéro d'épisode

### Logs et debugging

Les erreurs d'extraction M3U8 sont enregistrées dans :

```
logs/error_log.txt
```

Format :
```
[2025-11-04 14:30:12] Échec pour Anime X Saison 1 Épisode : 5: Timeout
```

### Configuration avancée

**Modifier les headers de requête** (dans `backend.py`) :

```python
headers = {
    "User-Agent": "Votre User-Agent personnalisé",
    # ...
}
```

**Changer le timeout M3U8** (dans `m3u8.py`) :

```python
await asyncio.wait_for(new_m3u8_event.wait(), timeout=30)  # 30 secondes
```

---

## Support et contribution

Pour toute question ou bug, vérifiez :
1. Les logs dans `logs/error_log.txt`
2. La console Flask pour les erreurs de scraping
3. La disponibilité du site source

---
