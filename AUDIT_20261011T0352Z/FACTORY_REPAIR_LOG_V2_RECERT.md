# REPAIR LOG V2 + RE-CERTIFICATION — 2026-10-11 (suite audit AUDIT_20261011T0352Z)

Autorisation : instruction opérateur « vas-y, que faire pour avancer » (2026-10-11).

## R2 — [P1] Moteur pipeline canonisé + 4 correctifs appliqués et re-certifiés

**Emplacement canonique créé** : `C:\factory\engine\local-factory\` (state-manager.cjs, factory-pipeline.cjs, factory-pipeline-v1.0.1.json, verify-proof-gate.cjs). Le worktree d'origine (`sargagame-1791307932424-c8qw6x`) reste intact — réversible par suppression du dossier engine.

| Fix | Défaut (preuve audit) | Correction | Test |
|---|---|---|---|
| F1 | `casinobae` (typo) rejette tout job casinobabe | → `casinobabe` (2 occurrences : validateState + emitted_events) | T4 ✅ |
| F2 | `persistEvent` figeait project/corr sur le 1er event (corrélation cassée) | Nouvel event_id ⇒ nouvelle identité + pipeline frais + history préservée (append-only) | T5 ✅ |
| F3 | Validateur rejetait tout état frais (`result.status: pending` jamais accepté, observabilité exigée avant terminal) | `pending` accepté ; observabilité exigée seulement hors pending | T4/T5 valid ✅ |
| F4 | `nextTransition` ignorait le trigger (historique trompeur) | Trigger doit matcher `from_to_<stage>` canonique, sinon rejet | T3 ✅ |
| F5 | `dedupe.key` jamais initialisé sur état frais (`Missing dedupe.key`) | Clé stable par défaut `${project}/${event_type}/${event_id}` | T4/T5 valid ✅ |

**Résultats de re-certification** (`…\Temp\opencode\factory-engine-test\recert2.cjs`) :
```
T4 casinobabe persisted+valid: true
T2 all 8 correct triggers OK | stage: result
T3 wrong trigger rejected: true
T5 sargagame after casinobabe: project=sargagame corr=corr-B event_id=evt-B stage=source valid=true
T5b history preserved (append-only): 16 entries
T6 exit gate: {passed:false, terminal:null, state_valid:true}
```
T6 : `state_valid:true` + gate non-passé car job non terminal = comportement fail-closed correct.

## R3 — [P1] Gate anti-preuve-fabriquée installé et démontré

`C:\factory\engine\local-factory\verify-proof-gate.cjs` — détecte SHA placeholder, PRs improbables, succès sans preuve. **Exécution réelle sur le journal de production** :
```
GATE FAIL — 3 preuve(s) fabriquée(s)/suspecte(s):
  [SUCCESS_WITHOUT_PROOF] 2026-10-07T22:15:41Z QUEUE_ITEM_COMPLETED
  [SUCCESS_WITHOUT_PROOF] 2026-10-08T09:15:14Z SESSION_COMPLETED
  [FAKE_SHA] 2026-10-08T09:15:14Z abc123def4… (SESSION_COMPLETED)
```
Le contrôle est **détectif** (il ne réécrit pas les events, append-only préservé). Intégration bloquante dans le worker = étape suivante recommandée.

## R4 — [P2] projects.json : chemins morts corrigés (backup `projects.json.bak-audit-20261011`)

| Projet | Avant (inexistant) | Après (vérifié) |
|---|---|---|
| casinobabe | C:/Users/user/sargagame-tmp/Casinobabe | **C:/factory/Casinobabe** ✅ |
| trading-bot | C:/Users/user/sargagame-trading-bot | **C:/Users/user/trading-bot** ✅ |
| botwow | C:/Users/user/sargagame-tmp/botwow | **non modifié** — aucun checkout existant trouvé (C:\Users\user\botwow-migration ambigu) → décision opérateur requise |

Périmètre/permissions (`allowed_actions`, `human_gates`) inchangés. Fichiers non commités.

## Reste à faire (non fait ici)

| Item | Pourquoi |
|---|---|
| Révoquer le PAT `ghp_…` (valide côté GitHub) | Action humaine, settings GitHub |
| Intégrer verify-proof-gate en bloquant dans le worker/pool | Emplacement du writer d'events à confirmer (session-manager) |
| Commit des fichiers engine + projects.json + AUDIT_* | Commit uniquement sur demande explicite |
| Nettoyage des ~70 worktrees | Inventaire dirty/clean + autorisation |
| Démarrer/rebrancher le runner V3 + harness crash-recovery | Démarrer une usine autonome sans mandat explicite = risque d'actions non sollicitées |
| botwow : cloner ou retirer du registre | Décision opérateur |

## Verdicts mis à jour

| Capacité | Avant | Après |
|---|---|---|
| FACTORY_SUBPROJECT_ROUTING | PARTIAL | **PARTIAL** (2 chemins réparés, casinobabe exécutable ; botwow restant) |
| Machine d'état pipeline | PARTIAL (4 bugs prouvés) | **PASS** (5 fixes re-certifiés en sandbox) |
| FACTORY_SECURITY_GOVERNANCE | PARTIAL | **PARTIAL+** (gate détectif installé ; révocation PAT en attente) |
| FACTORY_SINGLE_JOB_CORRELATION | PARTIAL | **PARTIAL+** (corrélation multi-events réparée et prouvée ; events historiques fabriqués inchangés par design) |
