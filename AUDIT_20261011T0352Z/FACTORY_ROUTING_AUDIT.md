# FACTORY ROUTING AUDIT — 2026-10-11

## Configurations de routage présentes

| Fichier | Version | Agents | Modèles | Cloud |
|---|---|---|---|---|
| `C:\factory\agent_routing.json` (V3) | 13 types de mission | aider/ollama/opencode/hermes | qwen2.5-coder:7b, qwen3-coder:30b, qwen3:30b, nemotron-3-ultra:550b | useOmniRoute sur certains types |
| `C:\factory-config\agent_routing.local.json` (V4, active) | 8 types | aider uniquement | ollama/qwen2.5-coder:7b ↔ ollama/qwen3-coder:30b | **aucun (fail-closed local-only)** |

Fail-closed vérifié par code : `_validate_local_only()` rejette tout provider `cloud`/`router` et tout modèle vision au chargement — re-testé à l'exécution (`Config validated: local-only mode confirmed`).

## Table de routage réelle (V4, testée)

| Type | Agent | Modèle | Fallback |
|---|---|---|---|
| SIMPLE_FIX | aider | ollama/qwen2.5-coder:7b | qwen3-coder:30b |
| QUICK_CHANGE | aider | qwen2.5-coder:7b | qwen3-coder:30b |
| DEBUG_COMPLEX | aider | qwen3-coder:30b | qwen2.5-coder:7b |
| ARCHITECTURE | aider | qwen3-coder:30b | qwen2.5-coder:7b |
| REPO_EXPLORATION | aider | qwen3-coder:30b | qwen2.5-coder:7b |
| TEST_WRITING | aider | qwen2.5-coder:7b | qwen3-coder:30b |
| LUA_REPAIR | aider | qwen2.5-coder:7b | qwen3-coder:30b |
| DEFAULT | aider | qwen2.5-coder:7b | qwen3-coder:30b |
| DEPLOY_OPERATIONS | déterministe (V3 : agent=null) | — | — |

## Preuves d'appels réels

1. **Ollama direct** : `POST /api/generate qwen2.5-coder:7b` → réponse `PONG` (2026-10-11, port 11434). 9 modèles installés (qwen2.5-coder:7b/14b/32b, qwen3-coder:30b, qwen3.6, mistral, llama3:8b, etc.).
2. **Routage E2E réel** : `factory_router.local.py SIMPLE_FIX "…remplace hello par FACTORY_E2E_OK…" <sandbox>` →
   - route : SIMPLE_FIX → aider / ollama/qwen2.5-coder:7b
   - appel réel : aider v0.86.2, 609 tokens envoyés / 13 reçus
   - fichier modifié : vérifié (`FACTORY_E2E_OK`)
   - commits réels : `54a760e` (pre) + `5acd9e0` (edit) dans le dépôt sandbox
   - retour structuré : `{success:true, agent:aider, model:ollama/qwen2.5-coder:7b, returncode:0}`
3. **Agents installés** : aider 0.86.2 ✅, opencode 1.18.34 ✅, hermes v0.21.5 ✅, omniroute 3.8.51 ✅ (binaire seulement — aucun appel opencode/hermes/omniroute démontré pendant l'audit).

## Failles constatées

1. Le V3 `agent_routing.json` référence `nemotron-3-ultra:550b` — **absent d'Ollama** (9 modèles listés). Fallback ARCHITECTURE/DEFAULT V3 cassé si utilisé.
2. Le V3 `agent_routing.json` n'est consommé par aucun composant actif identifié (le service python V3 est arrêté) ; le routage actif est le V4. Deux sources de vérité en divergence.
3. Aucun compteur de coût/métriques trouvés pour les appels locaux (metrics.output_file `C:\factory-service\state\metrics.jsonl` — service non actif, fichier non produit).
4. `DEPLOY_OPERATIONS` : déterministe, sans agent — conforme fail-closed, non testé (aucun déploiement autorisé).
5. Le mode production n'a pas de gate démontré rejetant une réponse simulée comme succès (cf. event fabriqué dans events.jsonl, FACTORY_GLOBAL_AUDIT §3-P1.4).

## Verdict

| Critère | Verdict |
|---|---|
| Routage V4 local réel | **PASS** (appel réel prouvé, contenu vérifié) |
| Fail-closed local-only | **PASS** (validé au chargement) |
| Fallback modèle | **NOT_PROVEN** (pas d'échec primaire provoqué pendant l'audit) |
| Chaînes opencode/hermes/omniroute | **NOT_PROVEN** (installés, jamais appelés en preuve) |
| Compteurs de coût | **NOT_PROVEN** |
