import os
import re

class Mita:
    """Classe utilitaire pour les interactions avec le navigateur."""
    
    @staticmethod
    def find_browser_profile():
        home_dir = os.path.expanduser('~')
        edge_path = os.path.join(home_dir, 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data')
        chrome_path = os.path.join(home_dir, 'AppData', 'Local', 'Google', 'Chrome', 'User Data')
        if os.path.exists(edge_path): return edge_path, "msedge"
        if os.path.exists(chrome_path): return chrome_path, "chrome"
        return None, None

    @staticmethod
    async def get_available_episodes(page):
        try:
            # Attend que les options soient bien présentes dans le DOM.
            # On attend que la dernière option soit "attachée", ce qui garantit que la liste est complète.
            await page.locator("#selectEpisodes > option").last.wait_for(state="attached", timeout=15000)
            
            # Récupère toutes les options directement, sans clics.
            options = await page.locator("#selectEpisodes > option").all()
            episodes_list = []
            for opt in options:
                text = await opt.inner_text()
                match = re.search(r'\d+', text)
                if match:
                    episodes_list.append({"episode": int(match.group(0)), "text": text.strip()})
            return episodes_list
        except Exception as e:
            print(f"Erreur lors de la récupération des épisodes : {e}")
            return []

    @staticmethod
    async def get_available_lecteurs(page):
        """
        Récupère la liste des lecteurs depuis le menu déroulant '#selectLecteurs'.
        """
        try:
            options = await page.locator("#selectLecteurs > option").all()
            # Retourne simplement le texte de chaque option (ex: "Lecteur 1", "Lecteur 2")
            return [await opt.inner_text() for opt in options]
        except Exception as e:
            print(f"Erreur lors de la récupération des lecteurs : {e}")
            return []