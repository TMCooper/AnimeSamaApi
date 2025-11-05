import asyncio
import os
import subprocess
from datetime import datetime
from playwright.async_api import async_playwright

try :
    from src.utils.Mita import Mita
except ImportError:
    from .Mita import Mita

# --- Fonctions utilitaires ---
PATH_EXEC = os.getcwd()
PATH_DOWNLOAD = os.path.join(PATH_EXEC, "logs")
os.makedirs(PATH_DOWNLOAD, exist_ok=True)

# Revoir cette fonction pour quel fonctionne mieux au seins du programme probabilité de logs useless trop elever
def log_error(anime_title, season_number, episode_number, error):
    log_file = os.path.join(PATH_DOWNLOAD, "error_log_m3u8.txt")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] Échec pour {anime_title} {season_number} Épisode : {episode_number}: {error}\n"
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)

async def extract_m3u8_from_page(base_url: str, episode_numbers_to_find: list):
    if not episode_numbers_to_find:
        return []

    playwright_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "ms-playwright")
    if not os.path.exists(os.path.join(playwright_dir, "chromium-")):
        try:
            subprocess.run(["playwright", "install", "chromium"], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Erreur lors de l'installation de Playwright. Veuillez exécuter 'playwright install chromium' manuellement. Erreur: {e}")
            return []

    browser_user_data_path, browser_channel = Mita.find_browser_profile()
    if not browser_user_data_path:
        print("Aucun profil de navigateur compatible trouvé (Edge ou Chrome).")
        return []

    custom_profile = os.path.join(playwright_dir, "playwright_profile")
    os.makedirs(custom_profile, exist_ok=True)
    
    found_links = []

    async with async_playwright() as p:
        context = None
        # Interception M3U8 (déplacée ici pour être accessible dans le bloc try)
        new_m3u8_event = asyncio.Event()
        pending_m3u8_url = None
        captured_urls = set()

        async def intercept_request(request):
            nonlocal pending_m3u8_url
            if "master.m3u8" in request.url and request.url not in captured_urls:
                pending_m3u8_url = request.url
                captured_urls.add(request.url)
                new_m3u8_event.set()

        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=custom_profile,
                headless=True,
                channel=browser_channel,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=msSmartScreenProtection',
                ]
            )
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
            page.on("request", intercept_request)

            # print(f"Navigation vers : {base_url}")
            await page.goto(base_url, wait_until="networkidle", timeout=60000)
            # print("Page chargée et activité réseau stabilisée.")

            all_available_episodes = await Mita.get_available_episodes(page)
            all_available_lecteurs = await Mita.get_available_lecteurs(page)
            
            if not all_available_episodes:
                raise RuntimeError("La liste des épisodes est vide. Le site n'a peut-être pas chargé correctement.")
            if not all_available_lecteurs:
                all_available_lecteurs = ["Lecteur 1"]

            # print(f"{len(all_available_episodes)} épisodes et {len(all_available_lecteurs)} lecteurs détectés.")

            for ep_num_to_find in episode_numbers_to_find:
                target_episode = next((ep for ep in all_available_episodes if ep["episode"] == ep_num_to_find), None)
                if not target_episode:
                    log_error(None, None, ep_num_to_find, "Non trouvé dans la liste scrapée")
                    continue

                ep_text = target_episode["text"]
                # print(f"\n--- Recherche M3U8 pour : {ep_text} ---")

                m3u8_found_for_this_episode = False
                for lecteur_text in all_available_lecteurs:
                    # print(f"Essai avec : {lecteur_text}")
                    try:
                        new_m3u8_event.clear()
                        pending_m3u8_url = None
                        
                        await page.locator("#selectLecteurs").select_option(label=lecteur_text)
                        
                        await page.locator("#selectEpisodes").select_option(label=ep_text)
                        
                        # print(f"Épisode '{ep_text}' sélectionné.")
                        
                        # print("Attente du M3U8...")
                        await asyncio.wait_for(new_m3u8_event.wait(), timeout=15)
                        
                        if pending_m3u8_url:
                            found_links.append({"episode": ep_num_to_find, "url": pending_m3u8_url})
                            # print("SUCCÈS : M3U8 trouvé !")
                            m3u8_found_for_this_episode = True
                            break
                        
                    except asyncio.TimeoutError:
                        print(f"Timeout sur {lecteur_text}")
                    except Exception as e:
                        print(f"Erreur inattendue : {e}")

                if not m3u8_found_for_this_episode:
                    # print(f"ÉCHEC : Aucun M3U8 trouvé pour {ep_text}")
                    log_error(None, None, ep_num_to_find, "Aucun M3U8 sur aucun lecteur")
                    
        except Exception as e:
            print(f"Erreur critique : {e}")
        finally:
            # print("\nExtraction terminée. Fermeture du navigateur.")
            if context:
                await context.close()
    return found_links