from flask import Flask, jsonify, request, Response
from src.backend import *

class Yui:

    app = Flask(__name__)
    app.json.ensure_ascii = False

    @app.route('/', methods=["GET"])
    def home():
        q = request.args.get("q", "").strip()
        if not q:
            return jsonify({"error": "Paramètre 'q' manquant"}), 400
        else:
            cardinal = "Cardinal.test()"
            return jsonify({
                'Bonjours' : "Je suis une api...",
                'Valeur q ' : q,
                'Cardinal value' : cardinal
            })
    
    @app.route('/api/getAllAnime', methods=["GET"])
    def getAllAnime():
        reset = request.args.get("r", "").strip()

        reponse = Cardinal.getAllAnime(reset)
        return jsonify(reponse)
        
    @app.route('/api/loadBaseAnimeData')
    def loadBaseAnimeData():
        return jsonify(Cardinal.loadBaseAnimeData())
    
    @app.route('/api/getSerchAnime', methods=["GET"]) # Exemple de request : http://127.0.0.1:5000/api/getSerchAnime?q=Frieren
    def serchAnime():
        querry = request.args.get("q", "").strip()
        limit = request.args.get("l", "").strip()

        if not querry:
            return jsonify({"error": "Paramètre 'q' manquant"}), 400
        try:
            limit = int(limit) if limit else 5   # convertir en entier
        except ValueError:
            limit = 5 # valeur par défaut si l'argument est invalide
        return jsonify(Cardinal.serchAnime(querry, limit))
    
    @app.route('/api/getInfoAnime', methods=["GET"])
    def getInfoAnime():
        querry = request.args.get("q", "").strip()
        if not querry:
            return jsonify({"error": "Paramètre 'q' manquant"}), 400
                
        return jsonify(Cardinal.getInfoAnime(querry))
    
    
    @app.route('/api/getAnimeLink', methods=["GET"])
    def getAnimeLink():
        nom = request.args.get("n", "").strip()
        saison = request.args.get("s", "").strip() # saison1 par défaut
        version = request.args.get("v", "").strip() # version sera en vostfr par défaut

        if not nom:
            return jsonify({"error": "Paramètre 'n' manquant"}), 400
        if not saison:
            saison = "saison1"
        if not version:
            version = "vostfr"
        
        return jsonify(Cardinal.getAnimeLink(nom, saison, version))