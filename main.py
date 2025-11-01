try:
    from .src.api import *
except ImportError:
    from src.api import *

class Api:
    def launch():
        Yui.app.run(debug=True)

if __name__ == "__main__":
    Api.launch()