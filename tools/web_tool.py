"""Outil pour les interactions Web."""

from urllib.parse import urlparse

import httpx


class WebTool:
    """Outil pour naviguer et interagir avec le web via SearXNG."""

    def __init__(self):
        """Initialise l'outil Web."""
        self.name = "WebTool"
        # URL de votre instance SearXNG (ajustez le chemin si c'est /search ou /searx)
        self.base_url = "https://ddcm-local.myftp.org/searx/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def search(self, query: str):
        """Recherche sur le web via l'API JSON de SearXNG."""

        # Paramètres pour SearXNG
        params = {
            "q": query,
            "format": "json",  # On demande explicitement du JSON
            "language": "fr-FR",  # Optionnel: forcer la langue
            "safesearch": 0,
        }

        print(f"Searching SearXNG for: {query}...")

        try:
            # On utilise httpx pour appeler l'API locale/distante
            with httpx.Client(headers=self.headers, follow_redirects=True, timeout=15.0) as client:
                # L'URL finale sera https://ddcm-local.myftp.org/search/search?q=...&format=json
                response = client.get(f"{self.base_url}search", params=params)
                response.raise_for_status()
                data = response.json()

            results = []
            seen_domains = set()

            # SearXNG retourne les résultats dans la clé 'results'
            for entry in data.get("results", []):
                href = entry.get("url")
                domain = urlparse(href).netloc

                # Filtrage par domaine pour éviter les doublons
                if domain not in seen_domains:
                    if "linkedin" in href or "twitter" in href or "facebook" in href:
                        continue  # On ignore les résultats LinkedIn, Twitter et Facebook

                    results.append(
                        {
                            "link": href,
                            "link_name": entry.get("title"),
                            #    "snippet": entry.get('content', '') # SearXNG utilise 'content' pour le snippet
                        }
                    )
                    seen_domains.add(domain)

                # On s'arrête à 10 résultats pour ne pas surcharger l'Agent
                if len(results) >= 3:
                    break

            print(f"Found {len(results)} unique results.")
            return results

        except httpx.HTTPStatusError as e:
            print(f"Error: HTTP error occurred: {e.response.status_code}")
            return "Error searching for results."
        except Exception as e:
            print(f"Error: An unexpected error occurred: {str(e)}")
            return "Error searching for results."

    def fetch(self, url: str):
        """Récupère le contenu brut d'une page (inchangé)."""
        try:
            with httpx.Client(headers=self.headers, follow_redirects=True, timeout=10.0) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            return f"Error: {str(e)}"
