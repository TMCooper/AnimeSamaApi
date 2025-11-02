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
PATH_DOWNLOAD = os.path.join(PATH_EXEC, "Dist")
os.makedirs(PATH_DOWNLOAD, exist_ok=True)

def log_error(anime_title, season_number, episode_number, error):
    log_file = os.path.join(PATH_DOWNLOAD, "error_log.txt")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] Échec pour {anime_title} {season_number} Épisode : {episode_number}: {error}\n"
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)

# --- Fonction principale corrigée ---
async def extract_m3u8_from_page(base_url: str, episode_numbers_to_find: list):
    if not episode_numbers_to_find:
        return []

    playwright_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "ms-playwright")
    if not os.path.exists(os.path.join(playwright_dir, "chromium-")):
        subprocess.run(["playwright", "install", "chromium"], check=True)

    print("Démarrage de l'extracteur M3U8...")
    browser_user_data_path, browser_channel = Mita.find_browser_profile()
    if not browser_user_data_path:
        return []

    custom_profile = os.path.join(playwright_dir, "playwright_profile")
    os.makedirs(custom_profile, exist_ok=True)
    
    found_links = []

    async with async_playwright() as p:
        context = None
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=custom_profile,
                headless=True,
                channel=browser_channel,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=msSmartScreenProtection',
                ]
            )
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

            # Interception M3U8
            new_m3u8_event = asyncio.Event()
            pending_m3u8_url = None
            captured_urls = set()

            async def intercept_request(request):
                nonlocal pending_m3u8_url
                if "master.m3u8" in request.url and request.url not in captured_urls:
                    pending_m3u8_url = request.url
                    captured_urls.add(request.url)
                    new_m3u8_event.set()

            page.on("request", intercept_request)

            # Navigation initiale
            # print(f"Navigation vers : {base_url}")
            await page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)  # Attendre que tout soit chargé
            
            all_available_episodes = await Mita.get_available_episodes(page)
            all_available_lecteurs = await Mita.get_available_lecteurs(page)
            
            if not all_available_episodes:
                raise RuntimeError("Liste des épisodes introuvable.")
            if not all_available_lecteurs:
                all_available_lecteurs = ["Lecteur 1"]

            # print(f"{len(all_available_episodes)} épisodes et {len(all_available_lecteurs)} lecteurs détectés.")

            for ep_num_to_find in episode_numbers_to_find:
                target_episode = next((ep for ep in all_available_episodes if ep["episode"] == ep_num_to_find), None)
                if not target_episode:
                    log_error(None, None, ep_num_to_find, "Non trouvé dans le menu déroulant")
                    continue

                ep_text = target_episode["text"]
                # print(f"\n--- Recherche M3U8 pour : {ep_text} ---")

                m3u8_found_for_this_episode = False
                
                for lecteur_text in all_available_lecteurs:
                    # print(f"Essai avec : {lecteur_text}")
                    
                    try:
                        new_m3u8_event.clear()
                        pending_m3u8_url = None
                        
                        # selectionne le lecteur
                        await page.locator("#selectLecteurs").select_option(label=lecteur_text)
                        await asyncio.sleep(1)
                        
                        # Vérifier que le lecteur a bien changé
                        current_lecteur = await page.evaluate("document.querySelector('#selectLecteurs').value")
                        # print(f"Lecteur actif : {current_lecteur}")
                        
                        await page.bring_to_front()
                        
                        # Cliquer physiquement sur le select pour le focus
                        select_box = await page.locator("#selectEpisodes").bounding_box()
                        if select_box:
                            await page.mouse.click(
                                select_box['x'] + select_box['width'] / 2,
                                select_box['y'] + select_box['height'] / 2
                            )
                            await asyncio.sleep(0.5)
                        
                        # Navigation au clavier
                        current_text = await page.evaluate("document.querySelector('#selectEpisodes').value")
                        all_texts = [ep["text"] for ep in all_available_episodes]
                        
                        if current_text not in all_texts:
                            current_index = 0
                        else:
                            current_index = all_texts.index(current_text)
                        
                        target_index = all_texts.index(ep_text)
                        steps = target_index - current_index

                        if steps > 0:
                            for _ in range(steps):
                                await page.keyboard.press("ArrowDown")
                                await asyncio.sleep(0.2)
                        elif steps < 0:
                            for _ in range(abs(steps)):
                                await page.keyboard.press("ArrowUp")
                                await asyncio.sleep(0.2)
                        
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(1)
                        
                        # Vérifier la sélection
                        selected_episode = await page.evaluate("document.querySelector('#selectEpisodes').value")
                        
                        # Si ça n'a pas marché, fallback JavaScript
                        if selected_episode != ep_text:
                            # print(f"     Fallback JavaScript...")
                            await page.evaluate(f"""
                                const select = document.querySelector('#selectEpisodes');
                                select.value = '{ep_text}';
                                select.dispatchEvent(new Event('change', {{bubbles: true}}));
                                select.dispatchEvent(new Event('input', {{bubbles: true}}));
                            """)
                            await asyncio.sleep(2)
                            selected_episode = await page.evaluate("document.querySelector('#selectEpisodes').value")
                        
                        if selected_episode != ep_text:
                            print(f"Impossible de sélectionner {ep_text}")
                            continue
                        
                        # print(f"Attente du M3U8...")
                        await asyncio.wait_for(new_m3u8_event.wait(), timeout=30)
                        
                        if pending_m3u8_url:
                            found_links.append({"episode": ep_num_to_find, "url": pending_m3u8_url})
                            # print(f"SUCCÈS : M3U8 trouvé !")
                            m3u8_found_for_this_episode = True
                            break  # On passe au prochain épisode
                        
                    except asyncio.TimeoutError:
                        print(f"Timeout sur {lecteur_text}")
                    except Exception as e:
                        print(f"Erreur : {e}")

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