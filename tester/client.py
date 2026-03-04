"""
client.py — Wrapper HTTP pour IPStack
- Timeout strict de 3 secondes
- 1 retry max en cas d'échec réseau ou 5xx
- Mesure de la latence de chaque requête
- Gestion explicite des codes 429 et 5xx
"""

import time
import os
import requests

BASE_URL = "https://api.ipstack.com"
TIMEOUT = 3  # secondes
MAX_RETRIES = 1
# La clé API est lue depuis la variable d'environnement IPSTACK_KEY
# (ne jamais hardcoder la clé dans le code)
API_KEY = os.environ.get("IPSTACK_KEY", "")


def get(endpoint: str, params: dict = None, retries: int = 0) -> dict:
    """
    Effectue une requête GET sur l'API IPStack.

    Retourne un dict contenant :
      - status_code (int)
      - json (dict | None)
      - latency_ms (float)
      - error (str | None)  — message d'erreur réseau si applicable
    """
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    all_params = {"access_key": API_KEY}
    if params:
        all_params.update(params)

    result = {
        "status_code": None,
        "json": None,
        "latency_ms": None,
        "error": None,
    }

    start = time.perf_counter()
    try:
        response = requests.get(url, params=all_params, timeout=TIMEOUT)
        elapsed = (time.perf_counter() - start) * 1000
        result["latency_ms"] = round(elapsed, 2)
        result["status_code"] = response.status_code

        # Gestion du rate limiting (429) — retry avec délai
        if response.status_code == 429:
            if retries < MAX_RETRIES:
                time.sleep(2)
                return get(endpoint, params, retries + 1)
            result["error"] = "Rate limit atteint (429)"
            return result

        # Gestion des erreurs serveur (5xx) avec 1 retry
        if response.status_code >= 500:
            if retries < MAX_RETRIES:
                time.sleep(1)
                return get(endpoint, params, retries + 1)
            result["error"] = f"Erreur serveur ({response.status_code}) après {MAX_RETRIES} retry"
            return result

        # Parsing JSON
        try:
            result["json"] = response.json()
        except ValueError:
            result["error"] = "Réponse non JSON"

    except requests.exceptions.Timeout:
        elapsed = (time.perf_counter() - start) * 1000
        result["latency_ms"] = round(elapsed, 2)
        if retries < MAX_RETRIES:
            return get(endpoint, params, retries + 1)
        result["error"] = f"Timeout après {MAX_RETRIES + 1} tentative(s)"

    except requests.exceptions.ConnectionError as exc:
        elapsed = (time.perf_counter() - start) * 1000
        result["latency_ms"] = round(elapsed, 2)
        if retries < MAX_RETRIES:
            time.sleep(1)
            return get(endpoint, params, retries + 1)
        result["error"] = f"Erreur de connexion : {exc}"

    return result
