# FACTORY E2E CERTIFICATION — 2026-10-11

## Test E2E corrélé exécuté pendant l'audit

**Job ID unique** : `factory-audit-e2e-20261010-001`
**Dépôt** : aveca/factory-v3 (dépôt de test autorisé, déjà utilisé par les E2E précédents PR #1/#2)
**Périmètre** : branche + push + PR + CI. **Aucun merge, aucun deploy** (contrainte de gouvernance de l'audit).

| Champ | Valeur | Preuve |
|---|---|---|
| job_id | factory-audit-e2e-20261010-001 | marker + commit + PR |
| Sous-projet | factory-v3 (test) | — |
| Dépôt | github.com/aveca/factory-v3 | clone gh, push OK |
| Agent/modèle | non utilisé pour la création du marker (test de chaîne git, pas de code) — appel modèle réel prouvé séparément (FACTORY_ROUTING_AUDIT) | — |
| Branche | `factory-audit-e2e-20261010-001` | refs/heads vérifié via ls-remote |
| Commit | `0b60adb` « audit E2E marker (branch+PR+CI, no merge) » | git log + ls-remote |
| Tests | N/A (repo sans suite de tests ; CI = build) | — |
| Push | OK 2026-10-11T03:48Z | remote refs |
| PR | **#5** https://github.com/aveca/factory-v3/pull/5 — OPEN, MERGEABLE, **NON fusionnée** | gh pr view |
| CI | **build SUCCESS** (run 38109595451, 7s) + GitGuardian pass | gh pr checks / gh run list |
| Merge | NON exécuté (interdit) | NOT_PROVEN |
| Deploy | NON exécuté (interdit, auto_deploy=false) | NOT_PROVEN |
| Live check | NON exécuté | NOT_PROVEN |

**Corrélation** : le même job_id figure dans le fichier marker, le message de commit, le titre et le body de la PR → `FACTORY_SINGLE_JOB_CORRELATION` démontrée pour ce job.

## Table de preuves consolidée (tous jobs examinés)

| job_id | Sous-projet | Dépôt | Branche | Commit | Tests | Push | PR | CI | Merge | Deploy | Live |
|---|---|---|---|---|---|---|---|---|---|---|---|
| factory-audit-e2e-20261010-001 | factory-v3 (test) | aveca/factory-v3 | factory-audit-e2e-20261010-001 | 0b60adb | CI build ✅ | ✅ | #5 OPEN | ✅ success | NOT_PROVEN (interdit) | NOT_PROVEN | NOT_PROVEN |
| job-20261010-p0-cert-001 | sargagame | aveca/sargagame | agent/local/job-20261010-p0-cert-001 | 90aaa7573 | events autopilot | ✅ | #867 | recoupée | **MERGED** | NOT_PROVEN (post-merge auto selon AGENTS.md, non vérifié) | NOT_PROVEN |
| job-20261010-p0-mqgp-001 | sargagame | aveca/sargagame | agent/local/… | n.v. | n.v. | ✅ | #868 | n.v. | **MERGED** | NOT_PROVEN | NOT_PROVEN |
| job-20261010-sos-live-001 | sargagame | aveca/sargagame | agent/local/… | n.v. | n.v. | ✅ | #869 | n.v. | **MERGED** | NOT_PROVEN | NOT_PROVEN |
| job-20261010-build-verify-001 | sargagame | aveca/sargagame | agent/local/… | n.v. | n.v. | ✅ | #866 | n.v. | OPEN | NOT_PROVEN | NOT_PROVEN |
| job-20261010-rev-island-001 | sargagame | aveca/sargagame | agent/local/… | n.v. | n.v. | ✅ | #870 | n.v. | OPEN | NOT_PROVEN | NOT_PROVEN |
| (event du 08/10, sessions) | sargagame | — | — | abc123def456 **FABRIQUÉ** | — | — | pull/123 **INEXISTANT** | — | — | — | — |

## Chemins d'échec vérifiés (réels, historiques)

- CI rouge : run 37687333736 et 37687525481 (factory-v3, 07/10) en **failure** avant correction workflow → l'échec CI est possible et visible, pas masqué.
- 500/403/push refusé : non provoqués pendant l'audit (aucune tentative d'écriture non autorisée).
- PR conflictuelle : non provoquée.

## Verdicts

| Critère | Verdict | Justification |
|---|---|---|
| FACTORY_REAL_WORK | **PASS** | modifications réelles + commits + PRs réelles (audit + jobs 20261010 + appel aider réel) |
| FACTORY_SINGLE_JOB_CORRELATION | **PASS** | job audit + job p0-cert-001 corrélés de bout en bout sans perte d'id |
| FACTORY_FULL_E2E | **PARTIAL** | merge/deploy/live non exécutés (blocage : absence d'autorisation explicite) |
| FACTORY_PRODUCTION | **NOT_PROVEN** | aucun déploiement vérifié ; preuve « deployed to production » du 08/10 = fabriquée |
| FACTORY_SUBPROJECT_ROUTING | **PARTIAL** | sargagame routé correctement ; casinobabe/botwow/trading-bot non exécutables (chemins locaux morts + typo validateur) |
| FACTORY_RUNNER_RECOVERY | **NOT_PROVEN** | runner V3 mort, heartbeat 3 jours, harness non re-exécuté |
| FACTORY_SECURITY_GOVERNANCE | **PARTIAL** | fail-closed local prouvé ; P0 PAT réparé ; event fabriqué non encore gate-blocké |
