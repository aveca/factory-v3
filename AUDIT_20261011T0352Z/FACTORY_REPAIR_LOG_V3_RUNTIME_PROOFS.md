# REPAIR LOG V3 — preuves d'exécution réelle — 2026-10-11

Suite de `FACTORY_REPAIR_LOG_V2_RECERT.md`. Exécution de l'ordre opérateur (sécurité → commit contrôlé → botwow → gate bloquant + harness crash-recovery).

## S1 — Sécurité (fait, hors révocation)

| Contrôle | Résultat |
|---|---|
| Scan secrets dans C:\factory (jsonl/json/md/txt/cjs, hors .git/node_modules/worktrees) | 2 hits — tous dans `state\reports\github-auth-e2e.md` |
| Nature | Token `ghp_…` réel + référence `github_pat_…` dans un exemple de commande — fichier **non suivi** par git (pas de fuite distante) |
| Action | **Masqué** avec backup `github-auth-e2e.md.bak-secret-20261011` — 0 token restant |
| Secrets GitHub | factory-v3 : 0 ; Casinobabe : 0 ; sargagame : 48 secrets (noms listés, aucune valeur exposée, aucun `ghp_` dans les noms) |
| **Restant (humain)** | **Révoquer le PAT** Settings → Developer settings → Tokens ; remplacer s'il est copié ailleurs (aucune occurrence trouvée dans les .git/config après nettoyage, ni dans les secrets GitHub listés) |

## S2 — Commit contrôlé (fait)

- `projects.json` : diff sémantique vérifié = exactement 2 corrections de chemins (reformatage JSON inclus) — commit `98d1bea`
- Périmètre scanné avant commit : **0 secret**. Rapports d'audit + engine/ versionnés. Push `factory-e2e-002` (pas de déploiement : CI build seulement).
- Commit 2 : `1d33fda` botwow.

## S3 — Botwow (fait : option « cloner »)

- `botwow-migration` : non-git, projet TS/Cloudflare ≠ dépôt bot-wow → écarté.
- `aveca/bot-wow` cloné dans **`C:\Users\user\botwow`** (main @ `fba4f70`), registre mis à jour et poussé.
- **4/4 sous-projets ont désormais un checkout local valide.**

## S4 — Gate anti-preuve-fabriquée : BLOQUANT à l'exécution (fait)

**Cause racine documentée** : `ai-factory-tmp/run-full-e2e.cjs` (lignes 96/126) code en dur `sha: 'abc123def456'` → harness de test qui fabrique des preuves ; le git.log de la session 0528d178 montre init→commit→PR→merge→deploy en 1 ms.

**Intégration** : gate fail-closed dans `ai-factory-tmp/session-manager.cjs` → `completeSession()` (point unique d'émission des verdicts). Rejette : SHA non-hex / longueur invalide, placeholders connus (`abc123|123456|deadbeef|789ghi…`), pr_url non GitHub. Succès sans preuve valide ⇒ `success=false`, erreur `PROOF_GATE_REJECTED:*`, event `SESSION_FAILED`.

**Test d'exécution réel** (sessions de test `proofgate-fake-001/002`, `proofgate-real-001/002`) :
```
FAKE  -> status: failed  | gate: REJECTED | errors: PROOF_GATE_REJECTED:invalid_merge_sha:789ghi012jkl   (v1)
FAKE2 -> status: failed  | rejected: [invalid_commit_sha:abc123def456, invalid_merge_sha:789ghi012jkl]   (v2, liste noire ajoutée)
REAL  -> status: completed | gate: PASSED   (commit 0b60adb / PR #5 réels)
```
Limite connue : un `pr_url` plausible (ex. /pull/123) passe le format — la vérification d'existence doit se faire côté worker via API GitHub (recommandation, non implémenté).

## S5 — Harness crash-recovery : **PASS à l'exécution réelle** (fait)

**Correction préalable P1** (`worker-pool.cjs` `ensureWorktree`) : la branche « reuse existing worktree » faisait `git checkout <nouvelle-branche>` **sans `-b`** → échec systématique de démarrage des jobs. Fix : `rev-parse --verify` puis `checkout -b` si absente.

**Protocole hermétique** : 5 tâches orphelines de la queue mises en quarantaine (copie + restauration à l'identique après test) ; tâche de test dédiée `audit-crash-recovery-20261011-002` (`payload.forceCrash` → `process.exit(1)` avant toute écriture/commit/push).

**Chaîne observée (events réels, events.jsonl)** :
```
TASK_CLAIMED → QUEUE_ITEM_STARTED → WORKER_STARTED (worker-147) → TOOL_STARTED → FILE_MODIFIED (crash)
→ worker exit code=1 → FAILED → REPAIR_STARTED (attempt 1) → Retrying with new worker
→ WORKER_STARTED (worker-149) → …
```
```
[driver] PHASE1 OK: worker worker-147 crashed
[driver] RESULT crash=true recovery=true recoveryWorkers=worker-149
```

**Nettoyage post-test** : tâche de test archivée dans `queue-quarantine-audit20261011\`, file restaurée à l'identique (5 orphelines + .gitignore), branche de test `factory/sargagame-1791740329804-ic6j` supprimée, worktree rendu à sa branche d'origine (reflog vérifié), aucun processus orphelin.

**Anomalies résiduelles observées pendant le test** : (a) events `WORKER_STARTED` émis en double ; (b) le retry replante 3× (attendu avec forceCrash) avant park ; (c) `getOrphanedSessions` signale en boucle les sessions orphelines du 07-08/10 (bruit, pas de boucle de reprise infinie constatée).

## Versionnage des correctifs runtime

Le sous-module `ai-factory-tmp` (aveca/ai-factory) porte **279 fichiers WIP préexistants** : un commit de fichiers entiers embarquerait du WIP inconnu → commit **non contrôlé**. À la place :
- `AUDIT_20261011T0352Z\patch-session-manager-proof-gate.diff` (31+/1−)
- `AUDIT_20261011T0352Z\patch-worker-pool-checkout-fix.diff` (11+/4−)
- Backups rollback : `session-manager.cjs.bak-20261011`, `worker-pool.cjs.bak-20261011`
- Les correctifs sont **actifs en local** ; leur commit dans le sous-module requiert d'abord le tri du WIP (décision opérateur).

## Verdicts mis à jour

| Capacité | Avant | Après | Preuve |
|---|---|---|---|
| Détection de preuves fabriquées | PASS (détectif) | **PASS (bloquant à l'exécution)** | FAKE→failed/REJECTED, REAL→completed (S4) |
| Corrélation job de bout en bout | PARTIAL+ | PARTIAL+ (inchangé ; nécessite un job réel jusqu'à CI/merge) | — |
| Gouvernance de sécurité | PARTIAL+ | PARTIAL+ (token masqué ; **révocation PAT = humain**) | S1 |
| Récupération après crash | NOT_PROVEN | **PASS** | worker-147 crashé → worker-149 repris (S5) |
| Certification production complète | NOT_PROVEN | NOT_PROVEN (nécessite job réel → CI → merge → deploy → live) | — |
