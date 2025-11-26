try:
    from .src.api import *
    from .src.utils.config import Config, Utils
except ImportError:
    from src.api import *
    from src.utils.config import Config, Utils

class Api:
    
    @staticmethod
    def launch(port=5000, ip="127.0.0.1", debug_state: bool = True, reload_status: bool = True):
        """
        Lance l'application Yui avec les paramètres spécifiés.

        Args:
            port (int): Port sur lequel l'application sera accessible. Default 5000.
            ip (str): Adresse IP d'écoute. Default "127.0.0.1".
            debug_state (bool): Active le mode debug. Default True.
            reload_status (bool): Active le reloader automatique. Default True.
        """

        Utils.hashCheck()
        Utils.gitCheck()

        Config.IP = ip
        Config.PORT = port

        Yui.app.run(
            host=ip,
            port=port,
            debug=debug_state, 
            use_reloader=reload_status
            )

if __name__ == "__main__":
    Api.launch()