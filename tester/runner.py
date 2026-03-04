"""
runner.py — Exécute tous les tests et calcule les métriques QoS
Métriques calculées :
  - passed / failed / total
  - latency_ms_avg  : latence moyenne
  - latency_ms_p95  : 95ème centile de latence
  - error_rate      : taux d'erreur (failed / total)
  - availability    : 1.0 si au moins 1 test PASS, 0.0 sinon
"""

import datetime
import time
from tester.tests import ALL_TESTS


def _percentile(values: list, pct: float) -> float:
    """Calcule le percentile `pct` (0-100) d'une liste de valeurs."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * pct / 100)
    idx = min(idx, len(sorted_vals) - 1)
    return round(sorted_vals[idx], 2)


def run_all() -> dict:
    """
    Exécute tous les tests et retourne un dict structuré :
    {
      "api": "IPStack",
      "timestamp": "...",
      "summary": { passed, failed, total, error_rate, latency_ms_avg, latency_ms_p95, availability },
      "tests": [ {name, status, latency_ms, details}, ... ]
    }
    """
    results = []

    for i, test_fn in enumerate(ALL_TESTS):
        if i > 0:
            time.sleep(0.5)  # évite le rate limiting
        try:
            result = test_fn()
        except Exception as exc:
            result = {
                "name": test_fn.__name__,
                "status": "ERROR",
                "latency_ms": 0,
                "details": str(exc),
            }
        results.append(result)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = len(results) - passed
    total = len(results)

    latencies = [r["latency_ms"] for r in results if r["latency_ms"] is not None]
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    p95_latency = _percentile(latencies, 95)
    error_rate = round(failed / total, 4) if total > 0 else 0.0
    availability = 1.0 if passed > 0 else 0.0

    return {
        "api": "IPStack",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "summary": {
            "passed": passed,
            "failed": failed,
            "total": total,
            "error_rate": error_rate,
            "latency_ms_avg": avg_latency,
            "latency_ms_p95": p95_latency,
            "availability": availability,
        },
        "tests": results,
    }
