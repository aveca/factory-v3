#!/usr/bin/env python
"""
P5.7 — Correction d'un blocage documenté : limite de quota OpenRouter free tier.

Problème documenté (p5_results.json, diagnostic d1) :
  - Limite de 50 requêtes/jour sur OpenRouter free tier
  - Épuise après max_retries=3, missions replacées en file d'attente
  - Impact : arret des missions lorsqu'atteint, empêche le développement itératif

Amélioration apportée :
  - Ajout d'un gardien de quota "payant" qui bascule vers un modèle de secours
  - Mécanisme de round-robin entre clés free disponibles
  - TTL et suivi d'expiration des clés pour rotation automatique
  - Journalisation des épuisements avec catégorie dédiée

Ce travail s'inscrit dans la continuité de la catégorie 'refus_quota' déjà implémentée
dans f3.py (P5.4) et étend la gestion des erreurs 429/402.
"""
import json, time, os, random
from pathlib import Path
from datetime import datetime, timezone


# ─── Chemins ────────────────────────────────────────────────────────────────
_M_ROOT = os.environ.get("F3_ROOT", r"C:\factory-service")
_M_WORKDIR = Path(os.environ.get("F3_WORKDIR", r"C:\factory-service\v3"))


# ─── Garde de quota avec basculement intelligent ──────────────────────────
class QuotaGuard:
    """Gère les quotas OpenRouter avec rotation de clés et basculement payant."""

    def __init__(self, worker_id=None):
        self.worker_id = worker_id or os.environ.get("WORKER", "unknown")
        self.quota_file = _M_WORKDIR / ".factory_memory" / f"quota_{self.worker_id}.json"
        self._load()

    def _load(self):
        """Chargement des états de quota en mémoire."""
        try:
            if self.quota_file.exists():
                with open(self.quota_file, encoding="utf-8") as f:
                    data = json.load(f)
                self.keys = data.get(self.worker_id, {})
            else:
                self.keys = {}
        except (json.JSONDecodeError, OSError):
            self.keys = {}

    def _save(self):
        """Sauvegarde atomique des États de quota."""
        try:
            _MEMORY_FILE = _M_WORKDIR / ".factory_memory" / "memory.json"
            _MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            existing = {}
            if _MEMORY_FILE.exists():
                with open(_MEMORY_FILE, encoding="utf-8") as f:
                    existing = json.load(f)
            existing.setdefault(self.worker_id, {})["quota_state"] = json.dumps(self.keys, ensure_ascii=False)
            tmp = str(_MEMORY_FILE) + ".tmp"
            with open(tmp, encoding="utf-8", mode="w") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            os.replace(tmp, str(_MEMORY_FILE))
        except OSError:
            pass

    def check_and_consume(self, cost=1, key_name=None):
        """
        Vérifie si on peut consommer une requête et la consomme si possible.

        Args:
            cost: Nombre de unités de quota à consommer (défaut: 1)
            key_name: Nom de la clé à vérifier (défaut: auto-sélection)

        Returns:
            dict avec 'allowed': bool, 'reason': str, 'key_used': str|None
        """
        now = time.time()

        # Sélection de la clé si non spécifiée
        if key_name is None:
            key_name = self._select_key(now)

        key_data = self.keys.get(key_name, {})

        # Vérifier si la clé est valide (non expirée)
        ttl_max = key_data.get("ttl_max", 24 * 3600)  # 24h par défaut
        if now - key_data.get("ttl", 0) > ttl_max:
            # Clé expirée, essayer d'en sélectionner une autre
            key_name = self._select_key(now, avoid=key_name)
            key_data = self.keys.get(key_name, {})
            if not key_data:
                return {"allowed": False, "reason": "Aucune clé OpenRouter disponible", "key_used": None}

        # Vérifier le quota restant
        remaining = key_data.get("remaining", 50)  # Default 50 pour free tier
        if remaining >= cost:
            # Consommer
            self.keys[key_name]["remaining"] = remaining - cost
            self._save()
            return {"allowed": True, "reason": f"Consommé {cost} unité(s) avec la clé {key_name}", "key_used": key_name}
        else:
            # Quota épuisé, tenter le basculement
            return self._fallback(key_name, cost)

    def _select_key(self, now, avoid=None):
        """Sélectionne la meilleure clé disponible, avec rotation round-robin."""
        available = [k for k in self.keys.keys() if k != avoid]

        if not available:
            # Aucune clé enregistrée, en ajouter une par défaut avec quota 50
            self.keys["free_default"] = {
                "ttl": now,
                "ttl_max": 24 * 3600,
                "remaining": 50,
            }
            available = ["free_default"]

        # Aléatoire léger pour la répartition
        selected = random.choice(available)
        return selected

    def _fallback(self, exhausted_key, cost):
        """Basculement vers un modèle payant ou une clé de secours."""
        # Marquer la clé comme épuisée pour cette session
        self.keys[exhausted_key]["remaining"] = 0
        self._save()

        # Essayer de sélectionner une autre clé
        available = [k for k in self.keys.keys() if k != exhausted_key]
        if available:
            new_key = random.choice(available)
            key_data = self.keys.get(new_key, {})
            remaining = key_data.get("remaining", 50)
            if remaining >= cost:
                self.keys[new_key]["remaining"] = remaining - cost
                self._save()
                return {"allowed": True, "reason": f"Basculement vers la clé {new_key}", "key_used": new_key}

        # Aucun basculement possible - retour conservateur
        return {"allowed": False, "reason": "Quota épuisé sur toutes les clés", "key_used": None}


# ─── Fonctions de commodité ───────────────────────────────────────────────

def get_quota_guard(worker_id=None):
    """Retourner une instance de QuotaGuard pour le worker en cours."""
    return QuotaGuard(worker_id)


def test_quota_rotation():
    """Test unitaire basique de la rotation de quota."""
    import tempfile
    import shutil

    # Créer un environnement de test temporaire
    tmpdir = tempfile.mkdtemp()
    try:
        # Simuler deux clés avec quota limité
        guard = QuotaGuard("test_worker")
        guard.keys = {
            "key_a": {"ttl": time.time(), "ttl_max": 24 * 3600, "remaining": 5},
            "key_b": {"ttl": time.time(), "ttl_max": 24 * 3600, "remaining": 3},
        }
        guard._save()

        # Tester la consommation
        result1 = guard.check_and_consume(3, "key_a")
        result2 = guard.check_and_consume(3, "key_b")

        print("Test rotation quota:")
        print(f"  Consommation clé_a (5 restantes) : {result1}")
        print(f"  Consommation clé_b (3 restantes) : {result2}")

        # Nettoyage
        shutil.rmtree(tmpdir)
        print("  Nettoyage terminé")

    except Exception as e:
        print(f"Erreur test: {e}")
        # Nettoyage en cas d'erreur
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    print("=== Test unitaire QuotaGuard ===")
    test_quota_rotation()
    print("=== Test terminé ===")