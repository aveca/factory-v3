# FACTORY RUNNER AUDIT — 2026-10-11

## État actuel des runners

| Runner | Emplacement | État à l'audit |
|---|---|---|
| Runner V3 contrôle (PID 14956) | `C:\factory` control plane | **MORT** — heartbeat `control/heartbeat.json` figé à 2026-10-07T20:59:28Z ; PID inexistant |
| Runner contenu Sargasses | `Documents\Backup\sargagame` | **ACTIF** (tâche SargaFactory ; dernier run 2026-10-11T03:30Z — rendus mq/gp/puntacana/florida/rivieramaya=exists) |
| Sentinelles gmail/github | `C:\autobot\scripts\factory` | **ACTIVES** — `C:\factory\status.json` rafraîchi (gmail: GMAIL_AUTH_MISSING / credentials.json absent) |
| Service python V3 | `C:\factory-service` | non actif (aucun process python) |

Deux processus node actifs identifiés = session opencode (outil d'audit), **pas** un runner Factory. Aucun double-runner créé pendant l'audit.

## Verrous et concurrence

- Verrou runner : `runner.lock` à la racine `C:\factory` — **supprimé dans le working tree, suppression non commitée** (git status). Aucun runner actif ne le justifie → cohérent avec runner mort, mais la suppression devrait être commitée ou annulée explicitement.
- Verrou autopilot : `C:\Users\user\sargagame-tmp\.ai\autopilot\orchestrator.lock` (watchdog `factory-watchdog.cjs` : lecture/écriture atomique tmp+rename, heartbeat age en minutes, deleteLock propre).
- Verrou usine contenu : `scripts/local-factory/state/.lock` + `MultipleInstances=IgnoreNew` sur les tâches planifiées + reclaim si stale (factory.cjs:71-82).
- **Stratégie monotone vérifiée par lecture du code** : un seul runner, pas de restart storm, backoff, STOP file global (factory-watchdog.cjs en-tête).

## Tâches planifiées Windows

| Tâche | Dernière/Prochaine exécution | Action | Cible |
|---|---|---|---|
| SargaFactory | 05:30 quotidien | wscript run-hidden.vbs → node factory.cjs | Documents\Backup\sargagame (contenu Sargasses) |
| SargaFactory-Serve | 00:00 quotidien | idem + `--serve` | idem |
| Factory-Sentinels | 23:45 quotidien | node C:\autobot\scripts\factory\factory.cjs start | sentinelles + watchdog |

## Scénarios d'erreur testés pendant l'audit

| Scénario | Testé | Résultat |
|---|---|---|
| Erreur modèle | non (pas d'échec primaire provoqué) | — |
| Dépôt inaccessible | non | — |
| Test rouge | non | — |
| Runner mort + heartbeat stale | **oui (observé)** | heartbeat figé 3 jours, aucune reprise auto du runner V3 (aucun mécanisme de relance du runner V3 actif) |
| Crash-recovery harness | non re-exécuté | rapports antérieurs (certification-report.md 08/10) revendiquent PASS (process.exit(1) → WORKER_EXITED → REPAIR_STARTED → respawn ; hang → watchdog) mais **non reproductibles à froid actuellement** |

## Autonomie PC allumé / éteint

**Locale** : la Factory de dev ne tourne **pas** en continu — seul le rendu Sargasses + sentinelles sont planifiés. Un job Factory V3 soumis quand le runner V3 est mort reste en file (`queue/` vide à l'audit). Si Windows s'éteint : tout processus local meurt ; reprise = relance manuelle du runner ; les fichiers d'état persistés (state/, queue/, control/) permettraient une reprise sans duplication **à condition que le runner redémarre** — aucun autostart du runner V3 trouvé.

**Distante** : workflows GitHub configurés sur factory-v3 (Factory V3 CI — s'exécute sans le PC, prouvé : runs 376873…–381095…). Déploiements sargagame : workflows Cloudflare/FTP côté GitHub (jobs `20261010` mergés → CI → deploy auto selon AGENTS.md sargagame). Aucune preuve d'exécution remote trouvée pendant la période PC éteint (non demandée/limité au scope).

**Conclusion autonomie 24/7** : **NON certifiée** — la Factory de dev dépend d'un processus local non relancé automatiquement.

## Verdicts

| Critère | Verdict |
|---|---|
| Verrou unique / anti-doublon | **PASS** (code + MultipleInstances) |
| Heartbeat / détection stale | **PARTIAL** (détection existe ; aucune reprise automatique constatée) |
| Persistance file + reprise | **NOT_PROVEN** (queue vide, runner mort) |
| Reprise après redémarrage Windows | **NOT_PROVEN** (pas d'autostart runner V3) |
| Journaux exploitables | **PASS** (logs jsonl datés, incidents/, events.jsonl — dates cohérentes) |
