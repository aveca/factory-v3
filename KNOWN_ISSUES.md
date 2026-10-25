# Known Issues — Factory V3 runtime (Windows)

## [OPEN] Popups console cmd.exe des serveurs MCP OpenCode

- Symptome: fenetres `cmd.exe` qui flashent; ~20 processus `cmd /d /s /c npx @playwright/mcp`
  et `chrome-devtools-mcp`, regenères a chaque appel outil navigateur.
- Cause racine (demontree): OpenCode lance les serveurs MCP locaux via `npx` (= `npx.cmd`)
  donc via un shell `cmd.exe` -> console allouee sur Windows (pas de CREATE_NO_WINDOW).
- Proprietaire: harness OpenCode (spawn interne). PAS la Factory V3.

### Fait (config / Factory)
- `C:\Users\user\.config\opencode\opencode.json` -> `mcp.playwright.enabled=false`
  (serveur inutilise; ses outils etaient deja `playwright_*:false`). Backup:
  `opencode.json.backup-mcp-cleanup-20261025`. Verifie: outils `browser.*` intacts.
- Arbre Vite orphelin fuite (preview :4173) termine.
- `autonomy.py`: spawns de missions (git/npm/gh) via `_run()` = CREATE_NO_WINDOW +
  STARTF_USESHOWWINDOW(SW_HIDE) -> plus de fenetre quand une mission tourne (teste rc=0).

### Reste a faire (niveau harness — agent futur)
- `chrome-devtools-mcp` est le backend des outils browser: `enabled:false` dans opencode.jsonc
  MAIS il tourne quand meme -> lance par OpenCode en interne, non controllable par config.
- Correctif propose (amont OpenCode): lancer ce MCP en `node <chemin/index.js>` direct
  (sans npx) OU forcer CREATE_NO_WINDOW/DETACHED_PROCESS dans le spawner MCP d'OpenCode.
- NE PAS desactiver: casserait les outils navigateur.
