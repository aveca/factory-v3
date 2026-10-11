# JALON 3 — CERTIFICATION E2E STAGING — 2026-10-11

Autorisation opérateur : « AUTORISATION LIMITÉE — JALON 3 FACTORY E2E » (dépôt + environnement de staging dédiés uniquement).

## Isolation (démontrée AVANT exécution)

| Contrôle | Preuve |
|---|---|
| Dépôt dédié créé | `aveca/factory-e2e-staging` (public, créé 2026-10-11, seed commit `8744bf7`) |
| Déploiement staging uniquement | GitHub Pages du repo dédié (`build_type: workflow`, URL https://aveca.github.io/factory-e2e-staging/) — 0 domaine/Worker de production |
| Workflows scopés | `ci.yml` (pull_request) + `deploy-staging.yml` (push main, `permissions: pages/id-token`, étape anti-secrets dans l'artefact) |
| Secrets du repo | **0 secret** (gh secret list vide) |
| File de jobs isolée | `C:\factory\staging-e2e\queue` — créée vide, aucune tâche historique |
| Aucune ancienne tâche reprise | File production vérifiée **new=0** avant lancement ; file staging créée ex nihilo |
| Runner unique + verrou | `state/staging.lock` {pid, at} + reclaim stale 10 min + refus si runner vivant ; production : aucun pool actif |
| Ressources gratuites | GitHub public + Pages (gratuits), aucune dépense |
| WIP exclu | Ni les 279 fichiers WIP, ni le patch worker-pool ; branche `audit/proof-gate-20261011` **non fusionnée** |

## Chaîne exécutée — job `factory-e2e-staging-20261011-002` (run certifiant)

| # | Étape | Artefact réel | Vérification indépendante |
|---|---|---|---|
| 1 | Job créé | `staging-e2e/queue/job-…-002.json`, job_id `factory-e2e-staging-20261011-002` | fichier + events |
| 2 | Attribution runner | `TASK_CLAIMED` par `staging-runner-1` (verrou acquis puis libéré) | events staging |
| 3 | Modification réelle | `version.js` réécrit avec job_id + timestamp (déterministe, inoffensif) | contenu du commit distant |
| 4 | Tests réels | `node e2e/test.js` → `E2E_STAGING_TESTS_OK` | sortie dans events |
| 5 | Push branche | `factory/e2e-mv45egt2` @ `dfa0a73` | `ls-remote` == commit local |
| 6 | PR réelle | **PR #2** https://github.com/aveca/factory-e2e-staging/pull/2 — body contient JOB_ID | gh pr view |
| 7 | CI réelle | run **38163365509** → success, headSha `dfa0a73` (exactement le commit du job) | gh run view |
| 8 | PR vérifiée | OPEN + tous checks SUCCESS avant merge | statutCheckRollup |
| 9 | Merge réel | **MERGED**, merge commit `224a9f547af12f85e1527ba640be38aa9adce0e5` | gh pr view |
| 10 | Deploy staging | run **38163383907** « Deploy E2E Staging (GitHub Pages) » → success, headSha `224a9f5` (= merge) | gh run view |
| 11 | Live vérifié | **HTTP 200** sur version.js : `{job:"factory-e2e-staging-20261011-002",…,worker:"staging-worker"}` | fetch indépendant avec no-cache |
| 12 | Corrélation | commit `dfa0a73` (message = job_id) → PR #2 → CI headSha idem → merge `224a9f5` → deploy headSha idem → live job_id idem | recoupé GitHub + HTTP |

**Fichier de preuve machine** : `staging-e2e/state/proof-factory-e2e-staging-20261011-002.json` — tous champs cohérents avec les vérifications indépendantes ci-dessus.

**Session** : `SESSION_COMPLETED`, **proof_gate = PASSED** (gate fail-closed session-manager : les preuves SHA/PR sont réelles, pas des placeholders). Job 001 (premier run) : chaîne identique réussie (commit `9f0d566a`, PR #1, CI 38163237090, deploy 38163251017, live 200) — crash cosmétique en sortie (`0xC0000409`, artefact Node/Windows sur `process.exit` avec fetch en attente) corrigé depuis ; conservé comme preuve de répétabilité.

## Identifiants réels (run certifiant 002)

```
job_id      : factory-e2e-staging-20261011-002
commit      : dfa0a73ef1ea9d5378cd0f073ac7e09db71e9faa
PR          : #2  https://github.com/aveca/factory-e2e-staging/pull/2 (MERGED)
merge commit: 224a9f547af12f85e1527ba640be38aa9adce0e5
CI run      : 38163365509 (success, headSha = commit du job)
Deploy run  : 38163383907 (success, headSha = merge commit)
Live        : HTTP 200 — job_id présent dans le contenu déployé
URL live    : https://aveca.github.io/factory-e2e-staging/version.js
```

## Contrôles NON vérifiés / limites explicites

1. **Pas d'appel LLM dans cette chaîne** : la modification est déterministe (code worker). L'appel modèle réel (aider+Ollama) est prouvé séparément (FACTORY_ROUTING_AUDIT) mais n'est pas dans cette exécution.
2. **Runner = instance staging dérivée** (patterns du pool + session-manager avec gate) — pas le worker-pool de production (WIP non commité, exclu par consigne).
3. **Vérification fonctionnelle** limitée au marqueur attendu (contenu HTTP) — c'est le seul changement produit.
4. **Branch protection** : le repo de test n'a pas de règles de protection (repo public de test) ; l'ordre CI→merge a été vérifié par le worker et recoupé via gh.
5. **Reprise après crash / concurrence multi-jobs** : hors périmètre de ce jalon (prouvés séparément au §S5 du repair log).
6. **Persistance 24/7** : hors périmètre — le runner staging est un processus one-shot avec verrou.

## Verdict

| Critère opérateur | Statut |
|---|---|
| Job réellement exécuté | ✅ |
| Commit issu du job | ✅ (message = job_id, SHA vérifié distant) |
| PR créée et contrôlée | ✅ (PR #2, checks SUCCESS avant merge) |
| CI réussie sur le commit attendu | ✅ (headSha identique) |
| Fusion dans le dépôt de test | ✅ (mergeSha vérifié) |
| Deploy staging terminé | ✅ (run success sur le merge commit) |
| Live confirmant le changement | ✅ (HTTP 200, job_id dans le contenu) |
| Corrélation bout en bout | ✅ (job_id/SHA/identifiants recoupés indépendamment) |

**JALON 3 : PASS** (sur le périmètre staging ci-dessus).

**La Factory complète n'est PAS certifiée par ce seul test** : restent conditionnels — worker-pool de production (WIP à trier), chaîne LLM-dans-la-boucle, autonomie 24/7, et tout exécution touchant un projet réel.
