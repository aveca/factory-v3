# FACTORY JOB CORRELATION — 2026-10-11

## Modèle d'état réel (documenté avant test)

**Source** : `state-manager.cjs` v1.0.1 + `factory-pipeline-v1.0.1.json` (contrat).

- **Stages** : `source → normalization → validation → dedup → priority → routing → queue → handler → result → recovery → retry|park`
- **Status pipeline** : pending / processing / success / failed / parked / cancelled
- **Result statuses** : SUCCESS / RETRY / PARKED / FAILED
- **Exit gate déterministe** : terminal_status ∈ {SUCCESS, RETRY, PARKED, FAILED} avec conditions croisées (pipeline.status + result.status + recovery.type).
- **Observabilité exigée** : execution_id, correlation_id, handler, handler_version, attempt, started_at, ended_at, status, side_effects.
- Projet valide attendu par le validateur : `casinobae`(sic), sargagame, drone-martinique, generic, unknown.

## Tests exécutés (sandbox `…\Temp\opencode\factory-pipeline-test`, copies — aucun fichier Factory modifié)

| Test | Commande | Résultat |
|---|---|---|
| Transitions successives | `next` ×7 | source→…→recovery atteints, exit 0 — **MAIS** le trigger passé est ignoré : l'historique a enregistré `queue→handler [source_to_normalization]` etc. (labels trompeurs) |
| Transition invalide | `next` depuis recovery | `Invalid transition recovery → retry via dedup_to_priority` — bien rejetée ✅ |
| Event casinobabe | persistEvent | persisté mais **validation FAIL** : `Invalid or missing project` (typo casinobae) + observabilité manquante |
| Event sargagame après casinobabe | persistEvent | **state.project = casinobabe** (le projet du nouvel event est ignoré si un event_id existe déjà) → **bug de corrélation prouvé** |

## Preuves de corrélation réelles (chaîne complète)

### Job `job-20261010-p0-cert-001` (sous-projet sargagame)
| Étape | Preuve |
|---|---|
| Branche locale | `agent/local/job-20261010-p0-cert-001` (dossier `C:\Users\user\sargagame-job-20261010-p0-cert-001`, git log vérifié) |
| Commit | `90aaa7573` « fix(certification): bounded wait for CI checks + payment-sensitive flag in deploy gate » |
| PR | #867 aveca/sargagame — **MERGED** (gh pr list 2026-10-11) |
| Events autopilot | `.autopilot/AUTOPILOT_FACTORY_EVENT-*.json` (smoke-token-verification, paid-funnel-e2e, etc.) |

### Autres jobs 20261010 (vérifiés via gh pr list)
| job_id (nom de branche) | PR | État |
|---|---|---|
| job-20261010-p0-mqgp-001 | #868 | MERGED |
| job-20261010-sos-live-001 | #869 | MERGED |
| job-20261010-build-verify-001 | #866 | OPEN |
| job-20261010-rev-island-001 | #870 | OPEN |
| feat/* (Casinobabe, 5 PRs) | #33–#37 | OPEN |

### Job audit `factory-audit-e2e-20261010-001`
Voir FACTORY_E2E_CERTIFICATION.md — corrélation conservée marker → commit → PR → CI.

## Écarts de corrélation détectés (états vs réalité)

1. **Event fabriqué** : `events.jsonl` SESSION_COMPLETED du 2026-10-08T09:15:14Z porte `commit_sha: abc123def456`, `pr_url: …/pull/123`, `merge_sha: 789ghi012jkl`, `deploy_info: deployed to production` — valeurs placeholder **enregistrées comme succès réel**. Comparé à la réalité GitHub : aucun commit/PR correspondant. → échec traité comme succès, état mémoire/fichier non corrélé au réel.
2. **Contradiction de rapports** : `certification-report.md` (FACTORY_FULL_E2E=PASS, PR #838, commit a42510b8) vs `FACTORY_V3_E2E_REPORT.md` (FACTORY_FULL_E2E=FAIL, PR #1). Le commit a42510b8 existe réellement (vérifié API) mais `pull/838` n'a pas été retrouvé dans les 5 PRs récentes de sargagame (866-870) — preuve PR #838 non recoupée pendant l'audit.
3. **Trois « états autoritaires » divergents** : `control/state.json` (07/10, provenance null), `control/heartbeat.json` (07/10), `status.json` (live sentinelle). Aucun ne porte de job courant.
4. **persistEvent fige le projet** (bug §tests) → deux jobs dans le même état pipeline seraient attribués au premier projet.

## Verdicts

| Critère | Verdict |
|---|---|
| Transitions respectées / rejet invalides | **PASS** |
| Corrélation job_id bout-en-bout (jobs réels 20261010) | **PASS** (branche→commit→PR→merge recoupés) |
| État fichiers corrélés à la réalité distante | **PARTIAL** (events fabriqués, 3 sources d'état divergentes) |
| Unicité identifiants entre composants | **PARTIAL** (job_id stable sur les jobs réels ; persistEvent casse le projet sur events multiples) |
