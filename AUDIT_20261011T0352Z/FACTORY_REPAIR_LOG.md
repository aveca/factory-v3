# FACTORY REPAIR LOG — 2026-10-11

## RÉPARATION APPLIQUÉE

### R1 — [P0] PAT GitHub en clair dans l'URL remote de C:\factory
- **Défaut** : `origin` = `https://ghp_****@github.com/aveca/factory-v3.git` — token personnel en texte clair dans `.git/config` (exposé à tout process/outil lisant la config du repo ; audit l'a détecté, valeur masquée volontairement dans tous les rapports).
- **Cause** : authentification git par token embarqué au lieu du credential manager.
- **Preuves** : `git remote get-url origin` (avant) ; scan de tous les `.git/config` de C:\ et C:\Users\user → seul C:\factory affecté.
- **Action** : `git remote set-url origin https://github.com/aveca/factory-v3.git`
- **Vérification** : `git ls-remote --heads origin` OK (auth par credential helper gh, token gho_ keyring) ; branche d'audit visible côté distant.
- **Réversibilité** : 1 commande pour revenir en arrière (déconseillé). **Résiduel** : le PAT `ghp_…` reste VALIDE côté GitHub → **révocation manuelle requise (action humaine)**.
- **Non testé** : impact sur les autres copies de la Factory si elles utilisaient le même remote (aucune autre copie avec token trouvée).

## RÉPARATIONS PROPOSÉES (diffs minimaux, NON appliqués)

### P1 — state-manager.cjs (copie canonique ambiguë : uniquement dans le worktree `sargagame-1791307932424-c8qw6x`)
```diff
@@ validateState (ligne ~327)
- if (!state.project || !['casinobae', 'sargagame', 'drone-martinique', 'generic', 'unknown'].includes(state.project)) {
+ if (!state.project || !['casinobabe', 'sargagame', 'drone-martinique', 'generic', 'unknown'].includes(state.project)) {

@@ persistEvent (ligne ~636)
- if (!state.event_id) {
-   state.event_id = event.event_id || `evt-${Date.now()}`
-   state.correlation_id = event.correlation_id || `corr-${Date.now()}`
-   state.project = event.project || state.project
+ if (!state.event_id || event.event_id !== state.event_id) {
+   // nouvel événement : nouvelle identité (event_id, correlation_id, project, source, event_type)
+   state.event_id = event.event_id || `evt-${Date.now()}`
+   state.correlation_id = event.correlation_id || `corr-${Date.now()}`
+   state.project = event.project || state.project
+   state.source = event.source || state.source
+   state.event_type = event.event_type || state.event_type

@@ nextTransition (ligne ~682) — valider la cohérence trigger/stage
+ const EXPECTED = { source: 'source_to_normalization', normalization: 'normalization_to_validation', /* … */ }
+ // ou : enregistrer trigger + from→to et rejeter un trigger incohérent
```
- **Non appliqué car** : la copie canonique vit dans un worktree temporaire ; appliquer le fix là serait perdu au nettoyage. Décision d'emplacement requise (ex. déplacer vers `C:\factory\engine\` versionné).

### P1 — Gate anti-preuve-fabriquée (worker/pool)
Tout `SESSION_COMPLETED` doit être rejeté si `commit_sha`/`merge_sha` ne matche pas `^[0-9a-f]{7,40}$` réel ou si `pr_url` n'est pas vérifiable via API. À ajouter dans le harvester d'events. Non implémenté (composant canonical ambigu — cf. ci-dessus).

### P2 — projects.json (registre — modification interdite sans autorisation)
Voir FACTORY_SUBPROJECT_MATRIX.md §Diff proposé.

## CORRECTIFS NON APPLIQUÉS / CONTRÔLES NON EXÉCUTÉS

| Item | Raison |
|---|---|
| Merge PR #5 (factory-v3) | interdit sans autorisation explicite |
| Déploiement / live check | interdit + auto_deploy=false |
| Nettoyage des ~70 worktrees sargagame | interdit sans inventaire + autorisation (contenu non identifié) |
| Suppression/modification de l'event fabriqué dans events.jsonl | append-only, preuve conservée |
| Révocation PAT + rotation | pas d'accès settings GitHub (humain requis) |
| Harness crash-recovery (crash + hang + reprise) | runner V3 non actif ; re-lancer nécessite de démarrer un runner — non fait sans mandat |
| Test fallback modèle (échec primaire → fallback) | non provoqué pour éviter chargement qwen3-coder:30b (18,5 Go) inutilement |
| Second runner pour test de concurrence | interdit par la mission |

## CE QUI N'A PAS PU ÊTRE TESTÉ
- Reprise après redémarrage Windows (redémarrage non autorisé).
- Chemin hermes/opencode/omniroute en appel réel.
- Déploiement Cloudflare/FTP sargagame et vérification live (aucun deploy déclenché).
- Preuve PR #838 revendiquée par certification-report.md (non recoupée).
