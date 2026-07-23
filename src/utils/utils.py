import cloudscraper, re, requests, json

URL_PW = "https://anime-sama.pw"

class Utils:
    def findLink(URL_PW=URL_PW): # Function AI Assist

        scraper = cloudscraper.create_scraper()  # équivaut à un navigateur
        reponse = scraper.get(f"{URL_PW}")
        html = reponse.text

        # Extraire la liste des domaines du JavaScript
        pattern = r"const domains = \[(.*?)\];"
        match = re.search(pattern, html, re.DOTALL)

        if match:
            domains_js = match.group(1)
            
            # Extraire chaque domaine avec une regex
            domain_pattern = r"name: '([^']+)'"
            domains = re.findall(domain_pattern, domains_js)
            
            main_domain = None
            results = []
            url_final = []
            
            for domain in domains:
                # print(f"Vérification de : {domain}")
                
                try:
                    url = f"https://{domain}"
                    
                    # Première requête SANS suivre les redirections
                    response_no_redirect = scraper.get(url, timeout=5, allow_redirects=False)
                    
                    result = {
                        'domain': domain,
                        'initial_code': response_no_redirect.status_code,
                        'status': 'unknown'
                    }
                    
                    # Vérifier si c'est une redirection (301, 302, 307, 308)
                    if response_no_redirect.status_code in [301, 302, 303, 307, 308]:
                        redirect_to = response_no_redirect.headers.get('Location', '')
                        result['status'] = 'redirect'
                        result['redirect_to'] = redirect_to
                        
                        # Suivre la redirection pour voir où ça mène
                        response_with_redirect = scraper.get(url, timeout=5, allow_redirects=True)
                        result['final_code'] = response_with_redirect.status_code
                        result['final_url'] = response_with_redirect.url
                        
                        # print(f"{domain} redirige vers {redirect_to} (code: {response_no_redirect.status_code})")
                        # print(f"  URL finale: {result['final_url']} (code: {result['final_code']})")
                    
                    # Si code 200 = domaine principal actif
                    elif response_no_redirect.status_code == 200:
                        result['status'] = 'online'
                        result['final_code'] = 200
                        result['final_url'] = url
                        main_domain = f'https://{domain}'  # Domaine principal
                        
                    
                    # Autres codes
                    else:
                        result['status'] = 'other'
                        result['final_code'] = response_no_redirect.status_code
                        # print(f"{domain} retourne le code: {response_no_redirect.status_code}")
                    
                    results.append(result)
                        
                except requests.exceptions.RequestException as e:
                    # print(f"{domain} est inactif ou inaccessible: {e}")
                    results.append({
                        'domain': domain,
                        'status': 'offline',
                        'error': str(e)
                    })
                
            if main_domain:
                # print(f"\nDOMAINE PRINCIPAL: {main_domain}")
                return main_domain
            else:
                print("\nAucun domaine principal trouvé (code 200)")
                return None
        
        return None


    def transform_chapters(data: bytes, title: str) -> dict:
        chapters = json.loads(data.decode("utf-8"))

        # Structure de base
        result = {
            "title": title,
            "max_chapter": len(chapters)
        }

        sorted_chapters = sorted(chapters.items(), key=lambda item: int(item[0]))

        # Ajout des chapitres au format "chapitre n"
        for chapter_num, nb_images in sorted_chapters:
            result[f"{chapter_num}"] = nb_images

        return result