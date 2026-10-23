# Factory V3 — Contrôle & Superviseur (infra)

Moteur d'orchestration réutilisant l'existant (file SQLite atomique, routeur strict-free
déjà configuré en P0, fallback Ollama) SANS reconstruction et SANS simulateur/missions
artificielles. Aucun développement fonctionnel de site n'est lancé ici.

## Composants
- `C:\factory-service\v3\f3.py` — moteur: contrôle d'état, file durable (SQLite), bail
  d'exécution, verrous, acceptation, reprise, arbitrage interactif, limite de concurrence.
- `C:\Users\user\AppData\Roaming\npm\factory.cmd` — CLI `factory …` (sur PATH).
- `p1_tests.py` / `p1_super_test.py` — tests d'acceptation (instance ISOLEE, données de test).
- Instance réelle: DB `C:\factory-service\state\f3_missions.db`, contrôle
  `C:\factory-service\state\f3_control.json`, logs `C:\factory-service\state\logs\f3.log`.
- Autostart: raccourci `%APPDATA%\...\Startup\FactoryV3-Supervisor.lnk` (pythonw, à l'ouverture
  de session, sans élévation). Démarrage au boot session-fermée: voir « Limites ».

## Commandes de contrôle
- `factory status`          : mode, verrou, autorisation de réclamation, compteurs, superviseur (pid/heartbeat/alive)
- `factory interactive`     : mode INTERACTIVE + verrou de priorité (bloque toute NOUVELLE mutation)
- `factory auto`            : mode AUTONOMOUS (lève le verrou)
- `factory pause` / `factory resume` : PAUSED / AUTONOMOUS
- `factory recover`         : RECOVERING (réconcilie les baux expirés, puis redevient AUTONOMOUS)
- `factory error --reason X`: ERROR (stoppe les mutations si l'intégrité n'est pas garantie)
- `factory queue [--state X]` / `factory logs [-n N]`
- `factory enqueue --kind audit|maintenance|dev|tests|seo|delivery --model <free> --handler <sur> --marker M [--priority N --timeout S --retries K --repo --branch --worktree --o "objectif"]`
- `factory run --once`      : un tick worker  |  `factory supervise` : superviseur persistant (pythonw) | `factory reclaim` | `factory init`

## Arbitrage (Étape 2)
Signal FIABLE d'interactif = **verrou explicite** (`factory interactive`, `interactive_lock`)
ou mode `INTERACTIVE`. On NE déduit JAMAIS « inactif » d'une fenêtre minimisée ni de la seule
présence d'un processus : `interactive_hint` (processus OpenCode détecté) n'est qu'un INDICE
journalisé. Retour utilisateur: on n'tue pas — on arrête la REVENTE de nouvelles missions, on
termune étape sûre et on pose un `checkpointed` (tâche `steps`) récupérable (preuve: test T2).

## Garanties (vérifiées par tests)
- Double exécution impossible: réclamation atomique SQLite (`UPDATE…RETURNING` sous BEGIN
  IMMEDIATE) + bail d'exécution expirant + superviseur à instance unique (2e = standby, reprise
  sur heartbeat périmé). Preuves: T3, tests superviseur.
- Persistance: états `queued/running/checkpointed/blocked/failed/completed`, heartbeat,
  historique, reprises bornées (`max_retries`), acceptation vérifiée (jamais « terminé » sur un
  simple code retour). Preuves: T1, T6, T7.
- Quota/modèles: aucun modèle payant — allowlist `router/*, ollama/*, openrouter-free/*`
  (refus à l'enqueue ET à l'exécution). Routeur strict-free existant conservé. Preuve: T9.
- Fenêtres: exécution autonome = Python pur (aucun sous-processus/console). Preuve: T10.
  Les routeurs Factory (aider/opencode) sont lancés `windowsHide=True` (correction P1).

## Limites honnêtes
- Autostart: UNAonly à l'OUVERTURE DE SESSION (raccourci Startup, sans admin). Démarrage au
  BOOT session-fermée = NÉCESSITE une tâche planifiée administrateur (élevation refusée ici) :
    Register-ScheduledTask -TaskName 'FactoryV3-Control-Supervisor' `
      -Action (New-ScheduledTaskAction -Execute pythonw.exe -Argument 'C:\factory-service\v3\f3.py supervise --interval 5') `
      -Trigger (New-ScheduledTaskTrigger -AtStartup) -Principal (New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited) `
      -Settings (New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Seconds 0)) -Force
- PC éteint/en veille: aucun traitement local possible (honnête). Session verrouillée: le
  superviseur (pythonw, non interactif) continue tant que la machine tourne.
- Handlers surs UNIQUEMENT (emit/steps/fail_first/local_model/paid_guard/boom). Le câblage des
  missions de codage réelles (opencode/aider via factory_router, branche + worktree isolés par
  mission) N'EST PAS activé: c'est le prochain blocage (hors périmètre infra P1).
- Contexte/fallback: la vérification de compatibilité de contexte AVANT repli Ollama (P0, D1/D3)
  n'est PAS appliquée (exigerait un redémarrage du routeur partagé → risque sessions actives).
