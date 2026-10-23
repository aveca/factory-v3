#!/usr/bin/env python3
"""P4/F — Mémoire persistante pour Factory V3.

Maintient des décisions, conventions et "leçons apprises" à travers les sessions.
Stockage JSON lightweight, sans dépendance externe. S'inscrit par-dessus
l'existant (SQLite + control.json) en ajoutant un espace de clé-valeur
persistant par mission/projet.
"""

import json, os, time
from pathlib import Path

# ─── Chemins ────────────────────────────────────────────────────────────────

# Racine de la mémoire: <F3_ROOT>/.factory_memory/<worker_id>.json
# Par défaut, F3_ROOT vaut C:\factory-service
_M_ROOT = os.environ.get("F3_ROOT", r"C:\factory-service")
_MEMORY_FILE = Path(_M_ROOT) / ".factory_memory" / "memory.json"

# Verrou simple pour l'écriture concurrente (le worker limitant à 1 via concurrency_limit)
_memory_lock = False

# ─── TTL (time-to-live) pour les patterns mémorisés ───────────────────────
# Durée de vie par défaut en secondes (24h) avant expiration et nettoyage automatique
DEFAULT_TTL_SECONDS = 24 * 3600

# ─── Classe Memory ─────────────────────────────────────────────────────────

class Memory:
    """Mémoire persistante JSON par worker, chargée au démarrage."""

    def __init__(self, worker_id: str | None = None):
        self.worker_id = worker_id or os.environ.get("WORKER", "unknown")
        self._data: dict = {}
        self._load()

    # ─── Chargement / sauvegarde ────────────────────────────────────────────

    def _load(self):
        """Chargement du fichier JSON en mémoire au démarrage."""
        try:
            if _MEMORY_FILE.exists():
                with open(_MEMORY_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                # Ne garde que les entrées de ce worker non expirées
                now = time.time()
                self._data = {
                    k: v for k, v in data.get(self.worker_id, {}).items()
                    if not self._is_expired(v)
                }
            else:
                self._data = {}
        except (json.JSONDecodeError, OSError):
            self._data = {}

    def _is_expired(self, value: dict) -> bool:
        """Vérifier si une entrée mémorisée a expiré."""
        if "ttl" not in value:
            return False  # Pas de TTL = jamais expiré
        return time.time() - value["ttl"] > value.get("ttl_max", DEFAULT_TTL_SECONDS)

    def _save(self):
        """Sauvegarde atomique du fichier JSON."""
        try:
            _MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            # Charger l'existant, mettre à jour seulement ce worker
            existing = {}
            if _MEMORY_FILE.exists():
                with open(_MEMORY_FILE, encoding="utf-8") as f:
                    existing = json.load(f)
            existing[self.worker_id] = self._data
            # Écriture temporaire + rename pour atomité
            tmp = str(_MEMORY_FILE) + ".tmp"
            with open(tmp, encoding="utf-8", mode="w") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            os.replace(tmp, str(_MEMORY_FILE))
        except OSError:
            pass  # Non critique si la sauvegarde échoue

    # ─── API publique ────────────────────────────────────────────────────────

    def remember(self, key: str, value: str | dict | list | int | float | None):
        """Stocker une valeur associée à une clé (persistée sur disque)."""
        if value is None:
            self._data.pop(key, None)
        elif isinstance(value, (str, int, float, bool)):
            self._data[key] = json.dumps(value, ensure_ascii=False) if not isinstance(value, bool) else str(value).lower()
        elif isinstance(value, (dict, list)):
            self._data[key] = json.dumps(value, ensure_ascii=False)
        else:
            self._data[key] = str(value)
        self._save()

    def recall(self, key: str, default=None):
        """Rappeler une valeur stockée. Retourne la valeur dé‑sérialisée."""
        raw = self._data.get(key)
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    def forget(self, key: str):
        """Supprimer une clé de la mémoire."""
        self._data.pop(key, None)
        self._save()

    def keys(self):
        """Retourner toutes les clés du worker courant."""
        return list(self._data.keys())

    def export(self) -> dict:
        """Retourner l'intégralité des données du worker (pour debug/sauvegarde manuelle)."""
        return dict(self._data)

    # ─── Nouvelles fonctions : patterns de défaut ────────────────────────────

    def remember_pattern(self, pattern_name: str, pattern_data: dict, ttl_hours: int = 24):
        """Mémoriser un pattern de défaut fréquent avec expiration TTL.

        Args:
            pattern_name: Nom identifiant le pattern (ex: "retry_after_30s_failure")
            pattern_data: Données structurées sur le pattern (ex: {"cause": "quota", "frequency": 5, "last_seen": "...}")
            ttl_hours: Durée de vie en heures avant expiration automatique
        """
        ttl_seconds = ttl_hours * 3600
        self._data[pattern_name] = {
            "data": pattern_data,
            "ttl": time.time(),
            "ttl_max": ttl_seconds,
        }
        self._save()

    def recall_pattern(self, pattern_name: str, default=None):
        """Rappeler un pattern de défaut si non expiré.

        Returns:
            Le dict de données du pattern si non expiré, sinon default.
        """
        stored = self._data.get(pattern_name)
        if stored is None:
            return default
        if self._is_expired(stored):
            # Nettoyer l'entrée expirée
            self.forget(pattern_name)
            return default
        return stored["data"]

    def forget_pattern(self, pattern_name: str):
        """Supprimer un pattern de mémorisation."""
        self.forget(pattern_name)

# ─── Instance globale (initialisée par le worker au besoin) ──────────────────

_memory_instance: Memory | None = None

def get_memory(worker_id: str | None = None) -> Memory:
    """Retourner l'instance globale de Memory pour le worker en cours."""
    global _memory_instance
    if _memory_instance is None or _memory_instance.worker_id != (worker_id or os.environ.get("WORKER", "unknown")):
        _memory_instance = Memory(worker_id)
    return _memory_instance

# Convenience functions
remember = get_memory().remember
recall = get_memory().recall
forget = get_memory().forget
remember_pattern = get_memory().remember_pattern
recall_pattern = get_memory().recall_pattern
forget_pattern = get_memory().forget_pattern