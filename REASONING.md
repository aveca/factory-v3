# P2/P3 — Couche de raisonnement & orchestration adaptative (VERIFIEE)
Aucune simulation presentee comme native. Preuves = generations/tests reels. Aucun modele payant.

## Modeles et routes VERIFIES (generations reelles, cout 0)
- fast/balanced : openrouter-free/nvidia/nemotron-3.5-lightning:free — corps `"reasoning": {"enabled": true, "max_tokens": N}` verifie (reasoning_tokens=47). `reasoning_effort` NON supporte -> jamais envoye. Prix 0/0. Outils OK. ctx 131072.
- deep   : openrouter-free/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free — raisonnement NATIF (rt~128-147 tokens), outils OK, ctx 256000, maxc 65536, prix 0/0. Latence mesuree ~6-15s (reponse vide occasionnelle -> 1 reprise unique, pas de boucle). Plan + relecture contradictoire reelles obtenues.
- vision : openrouter-free/nvidia/nemotron-3.5-super-vl:free — analyse visuelle reelle (image 1x1 -> "Noir").
- secours local : ollama/qwen2.5-coder:7b (pas de raisonnement natif, maintenance only, ctx 65536).
- NVIDIA NIM stepfun-ai/step-5-preview : fonctionne (raisonnement natif, outils) MAIS cout/quota NON verifiable via l'API et tres lent (512 tok=127s). Garde en configuration (non retire) mais NON utilise par `deep` pour respecter la regle "pas de cout non verifiable".

## Niveaux logiques (orch.LEVELS) — budgets propres a chaque modele
- fast     : nemotron-3.5-lightning:free, raisonnement OFF, ctx 131072, out 1024, timeout 120s. (~0.3s)
- balanced : nemotron-3.5-lightning:free, raisonnement ON (budget 1024), ctx 131072, out 1024, timeout 120s.
- deep     : nemotron-3-nano-omni-30b-a3b-reasoning:free, raisonnement ON (budget 128), ctx 256000, out 1024, timeout 90s. (~6-15s)
- vision   : nemotron-3.5-super-vl:free, raisonnement OFF, ctx 256000, out 256, timeout 120s.

## Controle de contexte avant tout repli (P3)
validate_context_fit(model, messages) -> (fits, tokens, budget): bloque si le contexte est non reducible. fit_context tronque (systeme + note + tours recents) pour respecter le budget. Jamais d'envoi oversize a Ollama ni a une route incapable.

## Orchestration adaptative (A-F)
Triage(difficulte/risque/perimetre -> niveau) -> Plan(SANS modifier de fichier) -> Exec(unite verifiable, worktree isole, checkpoint)
-> Revue contradictoire (grille deterministe + relecture profonde `deep_review` sur le mode deep: erreurs, hypotheses non demontees, omissions, risques, verdict explicite BLOQUANT/OK; jamais auto-validation de l'auteur)
-> Verifier(criteres d'acceptation reellement verifies) -> Livrer(completed UNIQUEMENT si criteres verifies; sinon blocked/failed + reprise).
Branchee sur la file/verrous/bail/arbitrage P1 (handler f3 `orch`). Python pur: aucune fenetre, aucun sous-processus.

## Tests
- p2_tests.py : 10/10 PASS (orchestration, refus payant, pas de fenetre, contexte, reprise).
- p3_deep_test.py : 6/6 PASS (deep plan dans budget, relecture defaut reel -> BLOQUANT+findings, relecture saine = analyse genuine, contexte tronque sous budget).
- p3_f3_integration.py : INTEGRATION_OK (mission deep via file P1 -> completed, triage=deep, plan nemotron-nano, deep_review OK, verify passed, marqueur+patch, modele payant refuse).

## Limites honnetes
- Route OpenRouter free intermittente (reponse vide occasionnelle): 1 reprise unique, pas de boucle; si persistante -> deep bloqué (non simule).
- deep = contenu profond reellement obtenu (plan + relecture avec findings), dans le budget temps (90s) et generation.
- Pas de bascule vers OpenRouter/payant si 402/429: arret de la route.
- Fichiers: orch.py, f3.py (handler orch), p2_tests.py, p3_deep_test.py, p3_f3_integration.py, REASONING.md. Backups conserves: opencode.json.backup-p2-20261022-233910 (+ P0 backups). Pas de depot site, pas de secret, pas de deploiement.
