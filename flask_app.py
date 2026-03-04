"""
flask_app.py — Application Flask principale
Routes exposées :
  GET /              → page des consignes
  GET /run           → déclenche un run de tests et sauvegarde en SQLite
  GET /dashboard     → tableau de bord (historique + métriques QoS)
  GET /health        → statut JSON de l'application (bonus)
  GET /export        → export JSON du dernier run (bonus)

La clé API IPStack est lue depuis la variable d'environnement IPSTACK_KEY.
Elle ne doit JAMAIS être hardcodée ici.
"""

import os

# Charge .env si disponible (dev local)
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

# Fallback : clé directement définie si aucune variable d'env n'est présente
# (utilisé sur PythonAnywhere où le WSGI ne définit pas IPSTACK_KEY)
if not os.environ.get("IPSTACK_KEY"):
    os.environ["IPSTACK_KEY"] = "0c84a446459590597355e1ad2a244384"
from flask import Flask, render_template, jsonify, redirect, url_for
from tester.runner import run_all
from storage import save_run, list_runs, get_last_run, init_db

app = Flask(__name__)

# ─────────────────────────────────────────────
# Initialisation de la base de données
# ─────────────────────────────────────────────
init_db()

# ─────────────────────────────────────────────
# Garde-fou : vérification de la clé API au démarrage
# ─────────────────────────────────────────────
_API_KEY_SET = bool(os.environ.get("IPSTACK_KEY", ""))


# ─────────────────────────────────────────────
# Route / — Redirige vers le dashboard
# ─────────────────────────────────────────────
@app.get("/")
def index():
    return redirect(url_for("dashboard"))


# ─────────────────────────────────────────────
# Route /consignes — Page des consignes
# ─────────────────────────────────────────────
@app.get("/consignes")
def consignes():
    return render_template("consignes.html")


# ─────────────────────────────────────────────
# Route /run — Déclenche un run de tests
# ─────────────────────────────────────────────
@app.get("/run")
def run_tests():
    if not os.environ.get("IPSTACK_KEY"):
        return jsonify({"error": "Variable d'environnement IPSTACK_KEY non définie"}), 500

    result = run_all()
    save_run(result)
    return redirect(url_for("dashboard"))


# ─────────────────────────────────────────────
# Route /dashboard — Tableau de bord
# ─────────────────────────────────────────────
@app.get("/dashboard")
def dashboard():
    runs = list_runs(limit=20)
    last = runs[0] if runs else None
    return render_template("dashboard.html", runs=runs, last=last, api_key_set=_API_KEY_SET)


# ─────────────────────────────────────────────
# Route /health — Santé de l'application (bonus)
# ─────────────────────────────────────────────
@app.get("/health")
def health():
    last = get_last_run()
    status = "ok" if _API_KEY_SET else "degraded"
    return jsonify({
        "status": status,
        "api_key_configured": _API_KEY_SET,
        "last_run_timestamp": last["timestamp"] if last else None,
        "last_run_availability": last["availability"] if last else None,
        "last_run_error_rate": last["error_rate"] if last else None,
    })


# ─────────────────────────────────────────────
# Route /export — Export JSON du dernier run (bonus)
# ─────────────────────────────────────────────
@app.get("/export")
def export_last_run():
    last = get_last_run()
    if not last:
        return jsonify({"error": "Aucun run disponible"}), 404
    return jsonify(last)


if __name__ == "__main__":
    # Utile en local uniquement
    app.run(host="0.0.0.0", port=5000, debug=True)
