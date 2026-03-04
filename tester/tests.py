"""
tests.py — Tests "as code" pour l'API IPStack
Au moins 6 tests couvrant :
  - Statut HTTP
  - Format JSON / Content-Type
  - Présence et type des champs obligatoires
  - Comportement sur entrée invalide
  - Sélection de champs (fields filter)
  - Endpoint /check (IP appelante)
"""

from tester.client import get


def _pass(name: str, latency: float) -> dict:
    return {"name": name, "status": "PASS", "latency_ms": latency, "details": ""}


def _fail(name: str, latency: float, details: str) -> dict:
    return {"name": name, "status": "FAIL", "latency_ms": latency, "details": details}


# ─────────────────────────────────────────────
# TEST 1 — Statut HTTP 200 sur une IP connue
# ─────────────────────────────────────────────
def test_http_status_valid_ip() -> dict:
    name = "TEST 1 — HTTP 200 sur IP valide (8.8.8.8)"
    res = get("8.8.8.8")
    lat = res["latency_ms"] or 0

    if res["error"]:
        return _fail(name, lat, res["error"])
    if res["status_code"] != 200:
        return _fail(name, lat, f"Statut attendu 200, reçu {res['status_code']}")
    return _pass(name, lat)


# ─────────────────────────────────────────────
# TEST 2 — Réponse est un objet JSON valide
# ─────────────────────────────────────────────
def test_response_is_json() -> dict:
    name = "TEST 2 — Réponse JSON valide"
    res = get("8.8.8.8")
    lat = res["latency_ms"] or 0

    if res["error"]:
        return _fail(name, lat, res["error"])
    if not isinstance(res["json"], dict):
        return _fail(name, lat, f"Réponse non-dict : {type(res['json'])}")
    return _pass(name, lat)


# ─────────────────────────────────────────────
# TEST 3 — Présence des champs obligatoires
# ─────────────────────────────────────────────
def test_required_fields_present() -> dict:
    name = "TEST 3 — Champs obligatoires présents"
    required = ["ip", "type", "country_code", "country_name", "latitude", "longitude"]
    res = get("8.8.8.8")
    lat = res["latency_ms"] or 0

    if res["error"]:
        return _fail(name, lat, res["error"])
    data = res["json"] or {}
    missing = [f for f in required if f not in data]
    if missing:
        return _fail(name, lat, f"Champs manquants : {missing}")
    return _pass(name, lat)


# ─────────────────────────────────────────────
# TEST 4 — Types des champs (ip=str, latitude=float/None)
# ─────────────────────────────────────────────
def test_field_types() -> dict:
    name = "TEST 4 — Types des champs (ip:str, latitude:float|None)"
    res = get("8.8.8.8")
    lat = res["latency_ms"] or 0

    if res["error"]:
        return _fail(name, lat, res["error"])
    data = res["json"] or {}

    errors = []
    if not isinstance(data.get("ip"), str):
        errors.append(f"ip devrait être str, reçu {type(data.get('ip'))}")
    if data.get("latitude") is not None and not isinstance(data.get("latitude"), (int, float)):
        errors.append(f"latitude devrait être float|None, reçu {type(data.get('latitude'))}")
    if data.get("longitude") is not None and not isinstance(data.get("longitude"), (int, float)):
        errors.append(f"longitude devrait être float|None, reçu {type(data.get('longitude'))}")

    if errors:
        return _fail(name, lat, " | ".join(errors))
    return _pass(name, lat)


# ─────────────────────────────────────────────
# TEST 5 — IP invalide renvoie success=False
# ─────────────────────────────────────────────
def test_invalid_ip_returns_error() -> dict:
    name = "TEST 5 — IP invalide → success=False avec champ error"
    res = get("not_an_ip")
    lat = res["latency_ms"] or 0

    if res["error"]:
        return _fail(name, lat, res["error"])
    data = res["json"] or {}

    # IPStack renvoie 200 mais avec success=false pour les entrées invalides
    if data.get("success") is not False:
        return _fail(name, lat, f"Attendu success=False, reçu : {data.get('success')}")
    if "error" not in data:
        return _fail(name, lat, "Champ 'error' absent dans la réponse d'erreur")
    if not isinstance(data["error"].get("code"), int):
        return _fail(name, lat, f"error.code devrait être int, reçu : {data['error'].get('code')}")
    return _pass(name, lat)


# ─────────────────────────────────────────────
# TEST 6 — Endpoint /check (IP appelante)
# ─────────────────────────────────────────────
def test_check_endpoint() -> dict:
    name = "TEST 6 — Endpoint /check retourne l'IP appelante"
    res = get("check")
    lat = res["latency_ms"] or 0

    if res["error"]:
        return _fail(name, lat, res["error"])
    data = res["json"] or {}

    if "ip" not in data:
        return _fail(name, lat, "Champ 'ip' absent dans /check")
    if not isinstance(data["ip"], str) or len(data["ip"]) < 7:
        return _fail(name, lat, f"Valeur ip invalide : {data.get('ip')}")
    return _pass(name, lat)


# ─────────────────────────────────────────────
# TEST 7 — Filtre de champs (fields=ip,country_name)
# ─────────────────────────────────────────────
def test_fields_filter() -> dict:
    name = "TEST 7 — Filtre fields=ip,country_name retourne uniquement ces champs"
    res = get("8.8.8.8", params={"fields": "ip,country_name"})
    lat = res["latency_ms"] or 0

    if res["error"]:
        return _fail(name, lat, res["error"])
    data = res["json"] or {}

    if "ip" not in data:
        return _fail(name, lat, "Champ 'ip' absent avec filtre fields")
    if "country_name" not in data:
        return _fail(name, lat, "Champ 'country_name' absent avec filtre fields")
    # latitude ne devrait pas être présent si filtré
    if "latitude" in data and data["latitude"] is not None:
        return _fail(name, lat, "Champ 'latitude' présent alors qu'il n'est pas dans le filtre")
    return _pass(name, lat)


# ─────────────────────────────────────────────
# TEST 8 — Valeur du champ 'ip' correspond à l'IP demandée
# ─────────────────────────────────────────────
def test_ip_value_matches_request() -> dict:
    name = "TEST 8 — Valeur ip dans la réponse = IP demandée (1.1.1.1)"
    res = get("1.1.1.1")
    lat = res["latency_ms"] or 0

    if res["error"]:
        return _fail(name, lat, res["error"])
    data = res["json"] or {}

    if data.get("ip") != "1.1.1.1":
        return _fail(name, lat, f"ip attendu '1.1.1.1', reçu '{data.get('ip')}'")
    return _pass(name, lat)


# ─────────────────────────────────────────────
# Liste de tous les tests à exécuter
# ─────────────────────────────────────────────
ALL_TESTS = [
    test_http_status_valid_ip,
    test_response_is_json,
    test_required_fields_present,
    test_field_types,
    test_invalid_ip_returns_error,
    test_check_endpoint,
    test_fields_filter,
    test_ip_value_matches_request,
]
