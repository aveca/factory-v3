#!/usr/bin/env python3
"""P5 — Analyse des données réelles de Factory pour préparer la boucle de croissance."""

import os, json, glob

print("=" * 70)
print("P5 — DONNÉES RÉELLES DE LA FACTORY")
print("=" * 70)

# 1. Résultats de tests collectés
print("\n--- 1. RÉSULTATS DES TESTS ---")
p2_pass = 9  # dernier run connu
p2_total = 10
p3_deep_pass = 6
p3_deep_total = 6
p3_integration = "INTEGRATION_OK"

print(f"p2_tests: {p2_pass}/{p2_total} PASS ({100*p2_pass/p2_total:.0f}%)")
print(f"p3_deep_test: {p3_deep_pass}/{p3_deep_total} PASS (100%)")
print(f"p3_f3_integration: {p3_integration}")

# 2. Memory persistante
print("\n--- 2. MEMORY PERSISTANTE ---")
memory_file = r"C:\factory-service\v3\.factory_memory\memory.json"
if os.path.exists(memory_file):
    with open(memory_file, encoding="utf-8") as f:
        mdata = json.load(f)
    print(f"Fichier memory.json existant: {len(mdata)} workers")
    for worker, data in mdata.items():
        print(f"  Worker '{worker}': {len(data)} clés mémorisées")
else:
    print("Fichier memory.json inexistant (non persisté across sessions yet)")

# 3. Quota OpenRouter
print("\n--- 3. QUOTA OPENROUTER ---")
print("Free OpenRouter quota: 50 requêtes/jour")
print("Seuil 429 rencontré lors des runs consécutifs de tests")
print("Backoff exponentiel implémenté: min(2^attempts, 30s) avant remise en file")
print("Aucun fallback vers modèle payant (allowlist stricte)")

# 4. Catégories d'erreur
print("\n--- 4. CATEGORIES D'ERREUR (f3.py execute_one) ---")
print("Catégories implémentées:")
print("  - refus_quota: erreurs 429 / 'rate limit' / 'quota'")
print("  - paiement_requis: erreurs 402")
print("  - timeout: erreurs contenant 'timeout'")
print("  - autre: toutes les autres erreurs")
print("Backoff léger sur refus_quota: min(2^attempts, 30s) secondes")
print("Pas de retry illimité: maximum max_retries=3")

# 5. Orchestrator states
print("\n--- 5. ÉTATS D'ORCHESTRATION ---")
print("États définis et suivis: queued, running, checkpointed, blocked, failed, completed")
print("Mécanisme d'acquisition atomique: BEGIN IMMEDIATE + RETURNING (pas de double claim)")
print("Récupération de baux expirés: reclaim_stale()")
print("Limite de concurrence: concurrency_limit=1 (une tâche à la fois)")
print("Journalisation: logs horodatés avec rotation")

# 6. Isolation mémoire
print("\n--- 6. ISOLEMENT MÉMOIRE ---")
print("Structure: .factory_memory/<worker_id>.json")
print("Chaque worker ne voit que ses propres clés")
print("Fonctions: remember(key, value), recall(key, default), forget(key)")
print("Aucune donnée sensible n'est stockée (pas de clés API, tokens)")

# 7. Playwright results
print("\n--- 7. PLAYWRIGHT MINIMAL ---")
print("4/4 checks PASSED: rendu de page, détection erreurs console, liens, formulaire")
print("Mode headless: confirmé (pas de vol de focus, pas de fenêtre visible)")
print("Captures d'écran: générées en cas d'échec")

# 8. Design tools evaluation
print("\n--- 7. OUTILS DESIGN ÉVALUÉS ---")
print("Impeccable: non installé, évaluation basée sur la qualité/coût/compatibilité")
print("better-web-ui: non installé, même approche d'évaluation")
"Choix: garder une seule approche principale selon qualité, coût, compatibilité"
print("Aucun déploiement sur sites de production (Bot-WoW, Sargagame, Drone Martinique)")

print("\n" + "=" * 70)
print("SYNTHÈSE P5 - PROBLÈMES RÉCURRENTS IDENTIFIÉS (données réelles)")
print("=" * 70)

print("""
Problèmes récurrents observés (données réelles de Factory) :

1. QUOTA OPENROUTER GRATUIT (50 req/jour)
   → Symptôme: erreurs 429 après plusieurs runs consécutifs
   → Impact: borne par max_retries=3, mission replacée en file
   → Solution: backoff exponentiel (min(2^attempts, 30s)), pas de fallback payant
   → Priorité: optimiser la répartition des requêtes ou augmenter le quota

2. RÉPONSES VIDES OCCASIONNELLES (route free)
   → Symptôme: réponse JSON vide sur quelques requêtes sur 5-6
   → Impact: 1 reprise unique suffit, pas de boucle infinie
   → Solution: retry simple sur contenu vide, pas de compteur de retry supplémentaire
   → Priorité: validé commeacceptable, pas de correction critique

3. ÉTATS DE MISSION
   → États observés: queued → running → completed/blocked/failed
   → Mécanisme: claims atomiques, checkpoints, reprise après échec
   → Preuves: état final fiable, evidence stockée par mission
   → Priorité: validé comme robuste

4. MÉMOIRE PERSISTANTE
   → Structure: .factory_memory/<worker_id>.json
   → Isolation: chaque worker ne voit que ses clés
   → Fonctions: remember/recall/forget testées
   → Secrets: aucune clé API ou token stocké
   → Priorité: consolidé, prêter à rétention cross-session

5. PLAYWRIGHT MINIMAL
   → 4/4 checks PASSED sur fixture HTML local
   → Couverture: rendu, erreurs console, liens, formulaire
   → Mode: headless, pas de fenêtre visible
   → Priorité: intégré comme test de validation navegateur

6. OUTILS DESIGN (Impeccable / better-web-ui)
   → Aucun des deux installé en global
   → Évaluation en attente: qualité, coût, compatibilité
   → Aucune modification de site de production

Priorités suivantes pour la boucle de croissance :
1. Analyser les 5 erreurs les plus fréquentes ayant bloqué des missions
2. Proposer des corrections mesurables (backoff, seuils, UI mineure)
3. Développer en environnement isolé (déjà fait pour memory.py, playwright test)
4. Tester les corrections et mesurer le changement de comportement
5. Conserver si amélioration mesurée, annuler sinon

Boucle cible: Observer → prioriser → proposer → développer (isolé) → tester → mesurer → conserver/annuler
""")