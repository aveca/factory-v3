# FACTORY GLOBAL AUDIT — Factory V3

- **Date audit** : 2026-10-11 (UTC), machine DESKTOP-HG0O76B
- **Portée** : audit global, sous-projets, certification E2E
- **Mode** : lecture seule → tests non destructifs → 1 réparation P0 (réversible)

## 1. Inventaire de l'installation

| Composant | Chemin | Rôle | État |
|---|---|---|---|
| Plan de contrôle V3 | `C:\factory` (git → github.com/aveca/factory-v3) | Registres, events, control plane, worktrees | Branch `factory-e2e-002`, working tree sale (modifs + ~40 non-suivis) |
| Routeur local V4 | `C:\factory-config` (factory_router.local.py + agent_routing.local.json) | Routage local-only aider+Ollama | Opérationnel (testé réel) |
| Service python V3 | `C:\factory-service` (factory_service.py) | Service de fond | **Non actif** (aucun process python) |
| Usine contenu Sargasses | `C:\Users\user\sargagame-tmp\scripts\local-factory` + copie `Documents\Backup\sargagame` | Rendu vidéo/FB quotidien | Active (tâches planifiées SargaFactory, SargaFactory-Serve) — distincte de la Factory de dev |
| Sentinelles | `C:\autobot\scripts\factory` (gmail/github sentinels, watchdog) | Poll status.json, incidents | Active (status.json rafraîchi aujourd'hui) |
| Worktrees | `C:\factory\worktrees\sargagame\…` (~70 répertoires) | Isolation des jobs | **Majorité obsolètes**, 1 seul contient le pipeline canonique (`sargagame-1791307932424-c8qw6x`) |

**Anomalies d'inventaire**
- Le moteur pipeline V3 (`factory-pipeline.cjs`, `state-manager.cjs`, `factory-pipeline-v1.0.1.json`) n'existe que dans **un worktree temporaire** — aucune copie canonique hors worktree.
- `C:\Users\user\CLAUDE.md` déclare « Ollama désinstallé le 2026-04-17 » → **faux** : Ollama tourne (PID 31492, port 11434, 9 modèles).
- 2 processus node actifs = session opencode (cet outil), **pas** un runner Factory.

## 2. Verdict de certification

| Capacité | Verdict | Preuve | Blocage restant |
|---|---|---|---|
| FACTORY_REAL_WORK | **PASS** | PRs sargagame #866–#870 et Casinobabe #33–#37 créées le 2026-10-10/11 ; commit `a42510b8` vérifié via API GitHub ; appel réel aider+Ollama ayant modifié un fichier + 2 commits (sandbox) | — |
| FACTORY_SINGLE_JOB_CORRELATION | **PARTIAL** | Chaîne complète prouvée pour `job-20261010-p0-cert-001` (branche → commit 90aaa7573 → PR #867 MERGED) et pour l'E2E audit `factory-audit-e2e-20261010-001` ; MAIS bug `persistEvent` (projet figé au 1er event) et event fabriqué (`abc123def456`/`pull/123`) | Corriger state-manager ; gate anti-placeholder |
| FACTORY_FULL_E2E | **PARTIAL** | E2E audit : branche → push → PR #5 → CI verte (run 38109595451) ; étapes merge/deploy/live non exécutées (interdites sans autorisation) | Merge+deploy+live sur dépôt de test |
| FACTORY_PRODUCTION | **NOT_PROVEN** | Aucun déploiement vérifié pendant l'audit (auto_deploy=false dans desired-state.json) | Autorisation explicite + run réel |
| FACTORY_SUBPROJECT_ROUTING | **PARTIAL** | Routage sargagame prouvé (jobs 20261010) ; casinobabe/botwow/trading-bot : chemins locaux inexistants + typo `casinobae` dans le validateur | Corriger projects.json + state-manager |
| FACTORY_RUNNER_RECOVERY | **NOT_PROVEN** | Heartbeat `control/heartbeat.json` figé au 2026-10-07 (PID 14956 inexistant) ; `runner.lock` supprimé (non commité) ; rapports antérieurs revendiquent PASS mais non reproductibles à froid | Re-run harness crash-recovery |
| FACTORY_SECURITY_GOVERNANCE | **PARTIAL** | Fail-closed validé (routeur local refuse cloud/vision) ; P0 réparé (PAT retiré du remote) ; **event fabriqué** dans events.jsonl = violation gouvernance | Gate anti-SHA placeholder ; révocation du PAT exposé |

**Verdict global : PARTIAL**

## 3. Défauts reproductibles (par priorité)

### P0
1. ~~PAT GitHub `ghp_…` en clair dans `C:\factory\.git/config` (URL remote)~~ — **RÉPARÉ** (remote assaini, connectivité re-vérifiée). **Le token reste valide côté GitHub → révocation manuelle requise.**

### P1
2. `state-manager.cjs` : liste des projets valides = `['casinobae','sargagame','drone-martinique','generic','unknown']` — typo `casinobae` vs `casinobabe` (projects.json). Un job casinobabe échouerait la validation.
3. `state-manager.cjs:632 persistEvent` : `state.project` n'est mis à jour que si `state.event_id` est null → le 2e job hérite du projet du 1er (corrélation cassée). Reprouvé pendant l'audit (emit casinobabe puis sargagame → `state.project=casinobabe`).
4. `events.jsonl` ligne finale : `SESSION_COMPLETED` avec preuves **fabriquées** (`commit_sha: abc123def456`, `pr_url: …/pull/123`, `merge_sha: 789ghi012jkl`) — succès simulé enregistré comme réel. Ne pas supprimer (append-only) ; ajouter un gate rejetant les SHA placeholders.

### P2
5. `nextTransition` ignore le nom du trigger (avance toujours au stage suivant, enregistre le trigger verbatim dans l'historique) — historique trompeur.
6. Chemins locaux `projects.json` inexistants : `sargagame-tmp/Casinobabe`, `sargagame-tmp/botwow`, `sargagame-trading-bot` (réel : `C:\factory\Casinobabe`, `C:\Users\user\trading-bot`).
7. ~70 worktrees sargagame obsolètes — nettoyage interdit sans inventaire + autorisation.
8. Double « état autoritaire » contradictoire : `control/heartbeat.json` (07/10, stale) vs `status.json` (live, écrit par sentinelles) vs `control/state.json` (07/10).
9. Divergence registres : `repos.json` (7 repos) vs `agent_routing.local.json` (sargagame seulement) vs `desired-state.json` (`allowed_projects: ["sargagame"]`).

### P3
10. `C:\Users\user\CLAUDE.md` obsolète (Ollama,stack LLM).
11. Rapports de certification antérieurs contradictoires à la racine de `C:\factory` (FAIL du 07/10 vs PASS du même jour) — bruit de gouvernance.

## 4. Actions exécutées / bloquées

**Exécutées (sans effet de production)** : inventaire ; test Ollama réel (PONG) ; E2E routage aider+Ollama en sandbox (fichier modifié, 2 commits) ; tests pipeline state-manager en sandbox (copie) ; E2E GitHub corrélé (branche, push, PR #5, CI) ; réparation P0 remote URL.

**Bloquées (interdites/absentes autorisation)** : merge PR #5 ; tout déploiement ; nettoyage worktrees ; modification projects.json/repos.json ; suppression/modification d'events ; second runner de test ; révocation du PAT (pas d'accès aux settings GitHub via ce canal).

## 5. Prochaine action minimale recommandée

1. **Révoquer le PAT `ghp_…` exposé** (github.com → Settings → Developer settings → Tokens) — 2 min, humain.
2. Appliquer le diff `state-manager.cjs` proposé dans FACTORY_REPAIR_LOG.md (typo + persistEvent + triggers).
3. Re-lancer le harness crash-recovery pour repasser FACTORY_RUNNER_RECOVERY d'un statut NOT_PROVEN.
