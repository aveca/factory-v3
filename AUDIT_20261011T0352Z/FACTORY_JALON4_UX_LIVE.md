# JALON 4 — AGENT UX LIVE RÉEL — 2026-10-11

Exécution de l'autorisation « Jalon 4 : Agent UX live réel » — cible exclusive aveca/sargagame.

## 1. Domaines réellement visités (Playwright/Chromium headless, 2026-10-11)

| Domaine | Région | Desktop `/` | Mobile `/` | `/fiabilite/` | Résultat |
|---|---|---|---|---|---|
| sargasses-martinique.com | mq | 200, carte OK, 25 boutons | 200, carte OK | 200 | ✅ sain |
| sargasses-guadeloupe.com | gp | 200, carte OK | 200, carte OK | 200 | ✅ sain |
| sargassummiami.com | florida | 200, carte OK, « 20 clean beaches » | 200, carte OK | **404** | ⚠ défaut |
| sargassumpuntacana.com | puntacana | 200, carte OK | 200, carte OK | **404** | ⚠ défaut |
| sargassumcancun.com | rivieramaya | 200, carte OK | 200, carte OK | **404** | ⚠ défaut |
| sargassumbarbados.com | barbados | **DNS ERR_NAME_NOT_RESOLVED** | idem | idem | ❌ site mort |

- 24 chargements de page réels, 24 screenshots (`ux-agent/runs/audit-*/screenshots/`), console + réseau capturés.
- Rapport brut : `C:\factory\ux-agent\runs\audit-1791743776077\audit-report.json`.

## 2. Défauts observés (dédupliqués, distingués réel vs légitime)

| # | Défaut | Classification | Preuve |
|---|---|---|---|
| D1 | `/fiabilite/` 404 sur les 3 domaines EN/ES (le slug FR n'existe que sur builds MQ/GP) ; 404 servi en français sur sites EN | **Réel, code** | 6 captures 404 identiques (25/21 Ko) vs pages réelles mq/gp (74/153 Ko) |
| D2 | sargassumbarbados.com : DNS ne résout pas | **Réel, infra (non-code)** — domaine dans `regions/barbados.json` mais jamais déployé | ERR_NAME_NOT_RESOLVED ×4 |
| D3 | `analytics_events` POST échoué sur gp | **Bénin** (beacon avorté par navigation) ; re-test ciblé : POST → **201 Created** | capture statut 201 |
| D4 | CSP `frame-ancestors` ignorée (délivrée via `<meta>`) | Mineur, connu | console ×12 |
| D5 | Titres « Score 0-100 » | **Non-défaut** (échelle, pas une valeur) | title complet vérifié |

## 3. Diagnostic avec appel modèle réel

- Modèle : **qwen2.5-coder:14b via Ollama local** (`POST /api/generate`) — 539 tokens prompt / 257 tokens response, température 0.2. Transcription : `C:\factory\ux-agent\diagnosis-model-qwen.txt`.
- Contribution du modèle : confirme D1 comme défaut réel à corriger, faible risque, testable.
- **Patch du modèle REJETÉ** (décision adversaire) : il inventait des ids de régions (`'mi','pc','cc'`) et altérait `IS_NEW_REGION` → aurait cassé les builds régionaux. Le fix retenu est aligné sur l'architecture existante (générateur `reliability-page.cjs`).

## 4. Correction réelle (branche `agent/qa/jalon4-fiabilite-redirect`, clone propre — 0 fichier du WIP touché)

- `scripts/lib/reliability-page.cjs` : en mode région, émission de `dist/fiabilite/index.html` = redirection permanente statique (meta refresh 0 + `location.replace` + canonical) vers le slug primaire (`/reliability/` EN, `/fiabilidad/` ES). Pas d'entrée sitemap (canonical inchangé).
- **Test de régression** : `tests/reliability-redirect.test.cjs` — 11 assertions (EN-primaire, ES-primaire, pureté sitemap, zéro donnée inventée) → **PASS**.
- **Régression complète** : `npm test` → **18/18 fichiers OK**.
- **Build** : `VITE_REGION=florida npm run build` → exit 0 ; `dist/fiabilite/index.html` généré ; **budget 209,5 Ko ≤ 210 Ko** ✓.

## 5. Vérification navigateur après correction (preview locale, avant/après)

- **Avant** (production live) : screenshot 404 « MÊME LE SATELLITE A PERDU CELLE-CI » (fr, sur site EN).
- **Après** (preview du build) : `http://127.0.0.1:4175/fiabilite/` → redirection vérifiée par journal serveur (`REQ /fiabilite/ 200` → `REQ /reliability/ 200`), URL finale `/reliability/`, titre « 96% Accurate Sargassum Forecasts, Verified — Florida », screenshot `after-redirect-preview.png`.
- Note de transparence : une première exécution du check navigateur a rendu REDIRECT_FAIL (artefact de démarrage du serveur statique) — ré-exécutée avec journal serveur → OK. Le journal est conservé comme preuve.

## 6. PR + CI (traçables)

- **PR #874** : https://github.com/aveca/sargagame/pull/874 — head `11769e0` (2 fichiers, +92/−0)
- **CI** (sur le SHA exact du job) :
  - `test-frontend` run 38166084802 → **success**
  - `perf` run 38166084782 → **success**
  - GitGuardian → pass
- **NON fusionnée** (production — aucune autorisation de merge/deploy demandée ni reçue).

## 7. Constats hors périmètre signalés (non corrigés)

1. `daily-copernicus.yml` : échec **sur toutes les branches y compris main** (startup failure 0 s, log absent) — préexistant, pipeline de déploiement à auditer séparément.
2. `sargassumbarbados.com` : DNS mort — décision infra (acheter/pointer le domaine ou retirer la région du registre).
3. Page 404 non localisée (fr sur sites EN) — partiellement atténuée par D1 fix sur /fiabilite/ uniquement.

## 8. Ce qui N'EST PAS prouvé (honnêteté)

- La production n'est **pas réparée** : la redirection n'agit qu'après merge + build + deploy FTP (autorisation requise).
- Le parcours testé couvre `/` et `/fiabilite/` — pas l'ensemble des 136+ pages ni les interactions paywall (aucun paiement, conformément aux gardes).
- barbados : jamais visité (inaccessible) — « inspecté » = constat d'inaccessibilité DNS, rien de plus.
- La boucle complète LLM-dans-le-worker (opencode) n'a pas piloté ce fix : le correctif a été écrit par l'agent d'audit avec diagnostic modèle réel en entrée.

## Verdict jalon 4 (cycle 1)

| Exigence | Statut |
|---|---|
| Domaines visités | **PASS** (6/6, dont 1 = constat DNS mort) |
| Parcours testés | **PASS** (24 chargements, 2 viewports, console+réseau+captures) |
| Défauts avec preuves | **PASS** (D1 code, D2 infra, D3 disculpé, D4/D5 mineurs) |
| Diagnostic avec vrai appel modèle | **PASS** (qwen2.5-coder:14b, tokens comptés, patch adversairement rejeté) |
| Correction réelle | **PASS** (2 fichiers, +92) |
| Régression concluante | **PASS** (test dédié 11/11 + suite 18/18) |
| Vérification navigateur | **PASS** (avant/après + journal serveur) |
| PR + CI traçables | **PASS** (PR #874, 3/3 checks verts) |
| Production réparée | **NOT YET** (merge + deploy = autorisation opérateur requise) |
