# AGENTS.md — Protocole d'exécution des agents IA

## Source de vérité et responsabilités
- ChatGPT pilote les missions : inspecte les éléments publiés sur GitHub, fixe l'objectif, le périmètre et les critères d'acceptation, puis contrôle le résultat.
- OpenCode exécute dans l'environnement local : inspection du dépôt, code, terminal, tests, navigateur, YouTube, extensions et outils réellement disponibles.
- GitHub est la source de vérité commune pour les commits poussés, branches, PR, rapports et résultats CI.
- L'utilisateur transmet le prompt ChatGPT à OpenCode puis le rapport OpenCode à ChatGPT ; ne lui délègue pas l'analyse du diff ou les validations techniques ordinaires.

## Cycle de mission
1. Vérifier le remote, le dépôt, la branche, le SHA et `git status --short` avant toute modification.
2. Lire les consignes locales et les fichiers d'état pertinents. Éviter les audits répétés lorsqu'un diagnostic ciblé suffit.
3. Définir une tâche cohérente, un périmètre précis et un critère de réussite mesurable.
4. Préserver tous les changements locaux préexistants ; ne jamais les écraser ni les nettoyer.
5. Travailler sur une branche dédiée pour les changements applicatifs.
6. Exécuter les tests pertinents, inspecter le diff complet et lancer `git diff --check`.
7. Si les vérifications passent, commit ciblé et push de la branche. Pas de push direct sur la branche par défaut pour le code applicatif ordinaire.
8. Ne donner une URL de PR qu'après confirmation de sa création.

## Rapport obligatoire
```text
MISSION: <nom court>
REPOSITORY: <owner/repo>
BRANCH: <branche>
COMMIT: <SHA complet ou aucun>
PUSH: oui/non
MODIFICATIONS: <résumé + fichiers essentiels>
TESTS: <commandes exactes + résultats réels>
CI: <URL + statut, ou non déclenchée>
TESTS LOCAUX RÉELS: <faits + résultats>
NON VÉRIFIÉ: <limites, ou aucun>
BLOCAGE: oui/non — <raison>
```

## Boucle de contrôle
À réception du rapport, ChatGPT vérifie sur GitHub le commit, le diff réel et les résultats CI accessibles, puis renvoie le prompt correctif ou la mission suivante. Le rapport seul n'est jamais une preuve suffisante. Ne pas demander de validation ordinaire à l'utilisateur.

## Efficacité
- Modification minimale ; pas de refonte ni dépendance sans justification.
- Après deux échecs d'une même approche, changer de méthode ou signaler le blocage.
- Séparer tests unitaires, intégration, navigateur/runtime réel et production. Une simulation n'est jamais une preuve réelle.
- Ne jamais inventer des résultats, métriques ou fonctionnalités.

## Sécurité et opérations
- N'utiliser que les outils réellement disponibles. Si un outil manque, le signaler clairement.
- Ne jamais publier de secrets, tokens, données personnelles ou fichiers locaux sensibles.
- Jamais de force-push, réécriture d'historique ou suppression de données.
- Les règles spécifiques au produit, aux paiements, aux données, à la sécurité et à la production priment sur ce protocole commun.
- Pas de migration destructive, fusion sur branche par défaut ou déploiement de production sans autorisation explicite.
- Un commit documentaire ne doit pas déclencher un déploiement applicatif inutile : utiliser `paths-ignore: ['AGENTS.md']` dans les workflows de déploiement concernés, sans désactiver les tests CI utiles.
