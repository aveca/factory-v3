# FACTORY V3 — RAPPORT MULTI-AGENTS & LIVRAISON WEB
Date : 2026-10-18 · Runtime réel : `C:\factory\ai-factory-tmp` (aveca/ai-factory, branche `feat/factory-agent-router-omniroute`)

## 1. Audit — constats factuels

| Constat | Preuve |
|---|---|
| 8 tâches bloquées ~50 h en `CLAIMED` par un worker mort (`worker-153`) | `queue/*.json`, `claimedAt` 16/10 19:13 ; `loadState()` ne restaure pas les claims ; `processQueue()` filtre `status==='new'` |
| **Drift config** : `agent_routing.json` ignoré au runtime | `defaultPolicy()` codé en dur ; le fichier n'était lu que si `options.policyFile` était passé |
| `botwow` mal déclaré dans `projects.json` | technologie `wow/lua`, `local_path C:/Users/user/botwow` (site Pages) alors que le backend Worker vit **non-commité** dans `Documents\GitHub\bot-wow\worker\` |
| `hermes.json` vide (2 o) | adaptateur présent, config absente — non bloquant pour le web |
| `Jiv` introuvable | aucun binaire/config/mention dans l'environnement — **pas d'agent fictif créé** |
| Runtime de production non commité | `worker-pool.cjs` = +306/−42 vs HEAD avant mon passage |

## 2. Travail livré — par projet

| Projet | Dépôt / branche | Blocage initial | Fichiers modifiés | Tests | Commits / push | Livraison visible | Déploiement |
|---|---|---|---|---|---|---|---|
| **Factory (usine)** | `aveca/ai-factory` @ `feat/factory-agent-router-omniroute` | 8 tâches CLAIMED mortes ; pas de ReplayPilot | `stale-claim-recovery.cjs` (nouveau), `worker-pool.cjs` (wiring), `agent-executor-interface.cjs` (adaptateur), `agent-router.cjs` (routage+drift), 3 fichiers de tests | 11 (stale) + 10 (adaptateur, réel) + 5 (dispatch réel) — **tous PASS** | `4b99b69` **poussé** | 8 tâches débloquées ; ReplayPilot intégré sans GUI ; drift de config corrigé | n/a (runtime local) |
| **Factory (config)** | `aveca/factory-v3` @ `factory-e2e-002` | routage absent pour desktop | `agent_routing.json` (`DESKTOP_WORKFLOW`, `allow_gui_input:false`) | via tests dispatch | `c1062dd` **poussé** | le fichier versionné est désormais lu au runtime | n/a |
| **Sargagame** | `aveca/sargagame` @ `factory/directive-cloud-neutralize-20261015` | build avortait le pipeline SEO (throw avalé) ; 0 breakpoint mobile dans `sg-ux-2026.css` | `src/sg-ux-2026.css`, `vite.config.js`, `tests/cta-mobile-tap.test.cjs` (nouveau) | **48/48** fichiers OK ; build prod vérifié ; guard : **98 URLs, 0 manquante** (avant : 3 + abort) | `f0dfce8e8`, `f1d5e242f` **poussés** | CTA mobile ≥48px, hover tactile neutralisé, anti-zoom iOS ; **pages mois régénérées** (`/sargasses-octobre-2026/`), 3 URLs sitemap 404 corrigées | **NON déployé** (FTP = autorisation requise) |
| **bot-wow.com** | `aveca/bot-wow` @ `feat/signup-honest-path` (nouvelle branche) | **aucun parcours d'inscription** (0 form, 0 input, 0 fetch) | `index.html`, `assets/app.js`, `tests/signup-contract.test.cjs` (nouveau) | test contrat + **vrai app.js en sandbox vm** — PASS | `f0223e9` **poussé** | formulaire beta honnête : succès **uniquement** après 2xx réel ; 404/5xx/réseau → « rien n'a été enregistré » | **NON déployé** (Pages via Actions du dépôt ; worker séparé) |
| **Casinobabe** | `aveca/Casinobabe` @ `fix/live-error-bus` (poussée nouvelle) | lien de téléchargement principal **404** (`Casinobaba` ≠ `Casinobabe`) | `site/sales.html` | suite wasmoon verte inchangée (14/14, pipeline PASS) — jeu non touché | `6ef1ca5` **poussé** | téléchargement réparé (404→200 vérifié HTTP), `</b>` invalide supprimé, OG/Twitter/canonical ajoutés | n/a vérifié (Pages) |
| **ReplayPilot** | `aveca/replaypilot` @ `feat/ollama-local-backend` | (mission précédente) | — | 269 passés | `37c1b1c` poussé | garde-fou HWND+PID, containment, recovery — consommé par le nouvel adaptateur | n/a |

## 3. Tests obligatoires (mission §7)

1. Routage agents → **PASS** (`test-desktop-dispatch.cjs`, 5/5, routeur réel)
2. Fallback agent indisponible → mécanisme existant (`FREE_ONLY`, `getCandidates`) non régressé ; nouveau fallback testé implicitement (replaypilot absent → policy suivante)
3. Récupération tâche bloquée → **PASS** (`test-stale-claim-recovery.cjs`, 11/11, appliqué en réel 8/8)
4. Verrou anti-double-exécution → `runner-lock.cjs`/`worktree-lock.cjs` inchangés, pool chargé OK (non régressé)
5. Isolation dépôts/worktrees → chaque projet sur son dépôt/branche propres (voir tableau) ; aucun fichier partagé
6. Adaptateur ReplayPilot **sans input GUI** → **PASS** (10 tests réels, venv réel)
7. Refus sécurité + coordonnées hors limites → **PASS** (21+10 tests replaypilot + cas adverses 11/11)
8. Preuves et statut terminal → artifacts dans les tâches ; statuts `PASS/FAIL/BLOCKED/NOT_PROVEN` ci-dessous
9. Tests web → sargagame 48/48 + build ; casinobabe suite verte ; botwow test contrat
10. Déploiement non autorisé → **respecté** : rien déployé (sargagame FTP, bot-wow Pages/worker, casinobabe) — documenté par projet

## 4. Statuts honnêtes

| Item | Statut |
|---|---|
| Usine : tasks pollables + ReplayPilot intégré + drift corrigé | **PASS** |
| Run GUI Execute de bout en bout (modèle pilote l'app) | **NOT_PROVEN** — interrompu par l'arrivée de cette mission ; nécessite autorisation GUI distincte |
| bot-wow : `/api/subscribe` + table `botwow_emails` côté worker | **BLOCKED** — backend séparé, migration D1 phase-4 existante non appliquée, déploiement à autoriser |
| Sargagame : déploiement FTP | **BLOCKED** — autorisation requise (politique projets.json) |
| Casinobabe : correctifs addon Lua | **NOT_PROVEN** — suite verte en l'état ; session de jeu active → aucune interaction WoW |
| Hermes | **BLOCKED** — `hermes.json` vide ; adaptateur existant non configuré |
| Jiv | **NOT_FOUND** — nom ambigu, aucun adaptateur créé |

## 5. Prochaines tâches autonomes (ordre)

1. `bot-wow` : handler `/api/subscribe` + binding D1 `botwow_emails` dans `worker/index.js` (code + tests unitaires mock-D1) — prêt à déployer dès autorisation
2. `sargagame` : déployer via `npm run ftp-deploy` après autorisation, puis vérifier `/sargasses-octobre-2026/` en ligne
3. Run GUI Execute ReplayPilot (autorisation distincte, ~2 min)
4. `hermes.json` : renseigner la config ou désactiver le fallback hermes dans le routage
5. `projects.json` : corriger l'entrée `botwow` (technologie `cloudflare-worker`, chemin du checkout Pages, live_urls)
