# Factory Self — Auto-amélioration par contrôle desktop

## Principe

Factory V3 est simultanément :

1. un moteur universel de contrôle de l’ordinateur (partagé par Sargagame, BOT-WOW, Factory Self) ;
2. un opérateur autonome (`factory-self`) ;
3. une plateforme capable de s’auto-améliorer.

Un seul runtime est partagé. Trois instances indépendantes (`factory-self`, `sargagame`, `bot-wow`) possèdent chacune leur config, dépôt, tâches, sessions, permissions, logs et état. Les contextes commerciaux ne sont jamais mélangés.

## Instance factory-self

Responsabilités :
- observer l’environnement ;
- contrôler souris/clavier ;
- manipuler OpenCode Desktop ;
- créer/superviser ses propres sessions ;
- envoyer des prompts et lire les réponses ;
- développer/corriger son propre code ;
- tester, valider E2E, commiter, ouvrir des PR ;
- mesurer les améliorations.

## Factory Guardian (superviseur indépendant)

Processus séparé du runtime Factory Self :
- surveille la disponibilité du runtime et les heartbeats ;
- détecte les crashs ;
- conserve la dernière version fonctionnelle ;
- sauvegarde l’état des sessions/tâches ;
- redémarre si nécessaire ;
- déclenche un rollback contrôlé.

Factory Self ne doit jamais pouvoir détruire son dernier mécanisme de supervision.

## Boucle d’auto-amélioration

OBSERVATION → DÉTECTION DÉFAUT → PRIORISATION → TÂCHE → MODIFICATION CODE → TESTS → VALIDATION E2E → COMMIT → PR → MESURE → NOUVELLE ITÉRATION.

## Test fondateur (preuve réelle déjà obtenue)

Scénario « erreur OpenCode Session not found » :

1. Observation réelle : session `ses_e3aac5f31ffe9N2RILE0LUH8ss` inexistante sur le serveur (46 sessions listées, id absent).
2. Création d’une session réelle : `ses_e19c1bdd9ffeVbLk2cXaBklsP1` (projet Factory, répertoire `C:\factory`).
3. Envoi d’un prompt réel et réponse réelle reçue : `OK` (modèle `ollama/qwen2.5-coder:7b`, event `text` + `step_finish` reason `stop`).
4. Correction de persistance : `approvedSessions` du bridge mis à jour vers l’id valide.

Ce scénario valide les étapes 1–4 du test fondateur. Les étapes 5–8 (correction d’un défaut non destructif dans Factory, exécution des tests, preuve, PR) sont le prochain jalon.

## Règles de sécurité

- Branches dédiées, tests reproductibles.
- Aucun secret exposé.
- Rollback disponible avant toute activation.
- Aucune modification irréversible sans autorisation.
- Aucun paiement ni envoi massif autonome.
- Guardian opérationnel indépendamment du runtime modifié.

## Statut

Non déclaré opérationnel : la réussite complète du scénario (étapes 5–8) reste à démontrer.
