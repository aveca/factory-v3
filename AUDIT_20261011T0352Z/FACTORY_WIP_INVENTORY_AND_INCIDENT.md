# WIP INVENTORY + INCIDENT REPORT — 2026-10-11 (suite opérateur)

## 1. Sécurité — PAT révoqué, confirmé

| Contrôle | Résultat |
|---|---|
| Validité du PAT (API GitHub, 2 endpoints) | **HTTP 401 sur /user ET /rate_limit → déjà révoqué/invalide** |
| Copies du token sur disque (scan complet hors .git/worktrees) | 1 seule (le backup) → **masquée** ; plus aucune copie |
| Historique git (factory-v3 + ai-factory) | `git log --all -S <token>` → **0 occurrence, jamais commité** |
| Note | Le token était peut-être expiré ou révoqué côté GitHub avant l'audit ; l'exposition locale est désormais nulle de toute façon |

**Priorité 1 : CLOSE — aucun accès GitHub actif lié au PAT exposé.**

## 2. Inventaire WIP sous-module `ai-factory-tmp` (aveca/ai-factory)

279 entrées `git status` = **11 fichiers suivis modifiés** + 268 non suivis (132 « autre », 116 scripts de test, 17 logs/txt, 3 backups). Aucun fichier temporaire/log n'est versionné.

### Fichiers suivis modifiés (diff vs HEAD 32cfa87)

| Fichier | +/− | Analyse |
|---|---|---|
| session-manager.cjs | 84+/48− | **contient mon gate** (31+/1− identifié) ; reste = WIP préexistant (bloc evidence/final_verdict) |
| worker-pool.cjs | 280+/41− | **contient mon fix checkout** (11+/4−) ; reste = WIP (path reuse worktree, etc.) |
| worker-runner.cjs | 401+/53− | WIP préexistant |
| ui-server.cjs | 243+/99− | WIP préexistant |
| factory-v3.cjs | 209+/49− | WIP préexistant |
| watchdog-heartbeat.cjs | 182+/24− | WIP préexistant |
| model-router.cjs | 142+/46− | WIP préexistant |
| factory-v2.cjs | 23+/3− | WIP préexistant |
| queue-integrator.cjs | 5+/3− | WIP préexistant |
| create-real-task.cjs | 1+/0− | WIP préexistant |
| factory.cjs | 3+/3− | WIP préexistant |

### Commits ciblés effectués (sans le WIP non identifié)

- **session-manager** : version propre reconstruite = `HEAD + gate uniquement`, validée (`node --check` OK, comportement testé : preuve fabriquée → `failed/REJECTED`, preuve réelle `0b60adb`/PR #5 → `completed/PASSED`). Commit **`c290ceb`** sur branche **`audit/proof-gate-20261011`**, **poussé** sur aveca/ai-factory. Diff exact : 33+/3−.
- **worker-pool** : le bug corrigé (`checkout` sans `-b`) n'existe **que dans le WIP** (le HEAD clone toujours à neuf). Le fix est donc inséparable du WIP → **pas de commit** ; il reste actif en local + patch `patch-worker-pool-checkout-fix.diff`. Il devra être commité avec le WIP `ensureWorktree` lors de son tri.

### Tests rejoués
- **session-manager** (version commitée propre) : PASS (voir ci-dessus).
- **worker** : fonctionnalité crash/reprise déjà prouvée (worker-147→worker-149). Rejeu du replay : NON CONCLUANT → voir incident §3.

## 3. INCIDENT pendant le rejeu — résolu, sans impact production

**Ce qui s'est passé** : au rejeu du harness, le pool a claimé les **2 tâches orphelines `new`** (plus anciennes que ma tâche) avant ma tâche de test. Le worker-150 a exécuté `e2e-full-chain-muzbl7qq` (tâche de test du 08/10) **réellement** : commit `8bde2667` (1 fichier marqueur `.sargagame/task-completed.txt`, 2 lignes, contenu inerte), push branche `factory/sargagame-1791741642616-ohre`, création **PR #872** sur aveca/sargagame, CI démarrée.

**Cause racine** : mon protocole avait mis les orphelines en quarantaine pour le premier test mais je les avais **restaurées** ensuite ; le rejeu les a trouvées en `new`. Erreur de protocole de l'audit, pas du moteur (le pool fait exactement son travail : claimer les `new`).

**Confinement (immédiat)** :
1. **PR #872 fermée** avant tout merge (`state: CLOSED`, `mergedAt: null`) — commentaire explicite laissé sur la PR.
2. Branche distante `factory/sargagame-1791741642616-ohre` **supprimée** (ls-remote vide).
3. Aucun déploiement (deploy = merge→main, jamais atteint). CI sur PR fermée = sans effet.
4. Aucun processus worker résiduel (PID 9908 inexistant ; aucun node/opencode/aider incident).
5. Worktree `sargagame-1791302731862-jcjhm3` rendu à sa branche d'origine (`a9wm`), branche incident supprimée localement (commit préservé côté GitHub via la PR fermée si besoin).
6. Tâche de replay archivée en quarantaine ; **les orphelines restent volontairement en CLAIMED/PARKED** (état plus sûr que `new` : un futur runner ne les re-claimera pas).

**Bilan d'impact** : 0 ligne de produit modifiée, 0 merge, 0 deploy, 1 PR de test fermée. Traçabilité complète dans events.jsonl + sessions/d7252ea141e19e4e.

**Mesure conservatoire** : plus aucun rejeu du pool tant que les tâches orphelines `new` ne sont pas triées par l'opérateur (les 2 restantes en `new` au moment de l'incident ont été converties en CLAIMED/PARKED — aucun `new` ne subsiste dans la queue).

## 4. État de la queue après opération

| Tâche | État initial (audit) | État final | Commentaire |
|---|---|---|---|
| e2e-full-chain-muzbl7qq | new | CLAIMED (worker-150) | exécutée par incident → PR #872 fermée ; état CLAIMED = neutralisée |
| e2e-full-chain-muzbmciv | new | PARKED (worker-151, remote_divergence) | neutralisée |
| e2e-sargagame-1791402000000 | CLAIMED | CLAIMED (inchangé) | orpheline du 08/10 |
| test-pool-reuse / test-pool-validation | CLAIMED | CLAIMED (inchangé) | orphelines du 07/10 |
| audit-crash-replay-20261011-003 | (test audit) | archivée en quarantaine | preuve |

**File finale : 0 tâche `new`** → aucun démarrage intempestif possible par un futur runner.

## 5. Prochaines étapes

1. Opérateur : trier le WIP `ai-factory-tmp` (11 fichiers, diffstats ci-dessus) — commit par fichier/fonctionnalité après revue.
2. Le fix worker-pool sera commité avec le bloc WIP `ensureWorktree`.
3. Jalon E2E réel (job_id → CI → merge → deploy → live) : en attente de ton autorisation merge+deploy sur dépôt cible — avec un **dépôt cible dédié**, plus jamais la queue de production.
