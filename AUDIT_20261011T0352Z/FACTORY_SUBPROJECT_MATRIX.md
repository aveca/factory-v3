# FACTORY SUBPROJECT MATRIX — Audit 2026-10-11

## Sources
- `C:\factory\projects.json` (4 projets, updatedAt 2026-10-06)
- `C:\factory\repos.json` (7 repos, snapshot 2026-10-06)
- `C:\factory\control\desired-state.json` (`allowed_projects: ["sargagame"]`, auto_deploy=false, auto_push/pr/ci=true)
- `C:\factory-config\agent_routing.local.json` (routage V4)

## Matrice

| Champ | sargagame | casinobabe | botwow | trading-bot |
|---|---|---|---|---|
| Repo GitHub | aveca/sargagame ✅ | aveca/Casinobabe ✅ | aveca/bot-wow ✅ | aveca/trading-bot ✅ |
| Branche défaut | main | main | main | main |
| local_path déclaré | C:/Users/user/sargagame-tmp | C:/Users/user/sargagame-tmp/Casinobabe | C:/Users/user/sargagame-tmp/botwow | C:/Users/user/sargagame-trading-bot |
| local_path réel | ✅ existe (git) | ❌ inexistant (réel : C:\factory\Casinobabe, git) | ❌ inexistant | ❌ inexistant (réel : C:\Users\user\trading-bot, git) |
| Test cmd | npm test | lua Casinobabe.lua --check | wasmoon-lua --wow-diagnostic | python -m pytest |
| Deploy | ftp-deploy + Cloudflare | — | — | railway |
| allowed_actions | git-commit, git-push, create-pr, deploy-ftp | lua-diagnostic, smoke-test | lua-diagnostic, smoke-test | code, commit, push, deploy |
| human_gates | secret_scan, scope_check, test_requirement | human-gate-secrets | human-gate-secrets | secret_scan, aml_check |
| autorisé dans desired-state | ✅ | ❌ (hors allowed_projects) | ❌ | ❌ |
| Preuve exécution récente | ✅ PRs #866–#870 (2026-10-10/11, 3 mergées) | ✅ PRs #33–#37 ouvertes 2026-10-11 | non prouvé | autopilot_supported=false |

## Repos déclarés (repos.json) vs réalité GitHub

| Repo | GitHub | Observations |
|---|---|---|
| aveca/sargagame | ✅ public | actif |
| aveca/Casinobabe | ✅ public | PRs ouvertes aujourd'hui |
| aveca/bot-wow | ✅ public | actif 10/10 |
| aveca/trading-bot | ✅ privé | last push 2026-04-22 |
| aveca/ai-factory | ✅ privé | actif 10/10 — **absent de projects.json** |
| aveca/AcimCaisse | ✅ public | dormant 2026-08 |
| aveca/naming | ✅ privé | dormant 2026-04 |

## Risques de routage croisé

1. **casinobabe.local_path pointe dans sargagame-tmp** → un job casinobabe pourrait écrire dans l'arborescence sargagame. Périmètre violé en cas d'exécution.
2. **state-manager.cjs valide `casinobae`** (typo) : incohérence d'identifiant canonique entre projects.json et le validateur.
3. **trading-bot : `autopilot_supported=false` mais `allowed_actions` inclut deploy** — garde aml_check/secret_scan obligatoires avant toute action.
4. `desired-state.json` limite à sargagame → toute mission casinobabe doit passer une mise à jour du périmètre (décision opérateur, pas d'auto-modification pendant l'audit).

## Diff proposé (non appliqué — modification de registre interdite sans autorisation)

```json
// projects.json
- "local_path": "C:/Users/user/sargagame-tmp/Casinobabe"
+ "local_path": "C:/factory/Casinobabe"
- "local_path": "C:/Users/user/sargagame-trading-bot"
+ "local_path": "C:/Users/user/trading-bot"
// botwow : local_path à créer/clarifier (aucun checkout actif trouvé)
```
