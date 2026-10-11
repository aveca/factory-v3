# TESTS AND SANITIZED LOGS — Audit 2026-10-11

## Tests exécutés (horodatés UTC)

| # | Test | Heure | Résultat | Artefact |
|---|---|---|---|---|
| T1 | Ollama API tags (9 modèles) | 03:37 | OK | — |
| T2 | Génération réelle qwen2.5-coder:7b | 03:39 | `PONG` | — |
| T3 | Routage E2E aider+Ollama (SIMPLE_FIX, sandbox) | 03:41 | success, fichier modifié, commits `54a760e`+`5acd9e0` | `…\Temp\opencode\factory-router-e2e` |
| T4 | Pipeline state-manager : 7 transitions | 03:52 | avance OK, triggers ignorés | `…\Temp\opencode\factory-pipeline-test\state\pipeline-state.json` |
| T5 | Transition invalide depuis recovery | 03:53 | rejetée (exit 1) | idem |
| T6 | persistEvent casinobabe → validation | 03:57 | FAIL (typo casinobae) | idem |
| T7 | persistEvent sargagame après casinobabe | 03:57 | FAIL — project figé = bug corrélation | idem |
| T8 | Clone factory-v3 + branche + commit + push | 03:48 | commit `0b60adb` | `…\Temp\opencode\factory-v3-e2e` |
| T9 | PR #5 + CI | 03:49 | build SUCCESS run 38109595451, GitGuardian pass | github.com/aveca/factory-v3/pull/5 |
| T10 | Remote URL assaini + ls-remote | 03:59 | OK sans token | C:\factory\.git\config |
| T11 | Scan PAT dans tous les .git/config (C:\, C:\Users\user) | 04:05 | 1 seul hit = C:\factory (réparé) | — |

## Journal expurgé T3 (routage réel)

```
[LocalRouter] Config validated: local-only mode confirmed
[LocalRouter] SIMPLE_FIX -> aider/ollama/qwen2.5-coder:7b
Aider v0.86.2 / Model: ollama/qwen2.5-coder:7b with whole edit format
sandbox.txt → FACTORY_E2E_OK
Tokens: 609 sent, 13 received.
Commit 54a760e docs: ajouter un fichier sandbox.txt
Commit 5acd9e0 fix: remplace "hello" par "FACTORY_E2E_OK" dans sandbox.txt
{"success": true, "returncode": 0, "agent": "aider", "model": "ollama/qwen2.5-coder:7b"}
```

## Journal expurgé T7 (bug corrélation)

```
emit casinobabe  → persisted, validate: ["Invalid or missing project", …]
emit sargagame   → persisted, validate: ["Invalid or missing project", …]
debug: state.project after persist(sargagame) = "casinobabe"   ← BUG
```

## Liens GitHub (preuves distantes)

- PR audit (ouverte, non fusionnée) : https://github.com/aveca/factory-v3/pull/5
- CI run audit (success) : https://github.com/aveca/factory-v3/actions/runs/38109595451
- PRs sargagame jobs 20261010 : #866 (open), #867/#868/#869 (merged), #870 (open)
- PRs Casinobabe : #33–#37 (open)
- Historique CI rouge réel : runs 37687333736, 37687525481 (07/10)

## Note de sécurité des logs
Aucune valeur de secret n'est reproduite dans ce dossier. Le PAT détecté est référencé uniquement par son préfixe tronqué.
