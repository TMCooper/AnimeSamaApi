try:
    from .src.api import *
except ImportError:
    from src.api import *

class Api:
    @staticmethod
    def launch(port=5000, debug_state: bool = True, reload_status: bool = True):
        Yui.app.run(
            # host="0.0.0.0", # Peut être plus tard si l'api dois être accèssible a tous le reseaux
            port=port,
            debug=debug_state, 
            use_reloader=reload_status
            )

if __name__ == "__main__":
    Api.launch()