try:
    from .src.api import *
except ImportError:
    from src.api import *

class Api:
    @staticmethod
    def launch(debug_state: bool = True, reload_status: bool = False):
        Yui.app.run(debug=debug_state, use_reloader=reload_status)

if __name__ == "__main__":
    Api.launch()