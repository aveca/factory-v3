# Improvement Exchange — Auto-amélioration collective

## Objectif

Permettre à Factory, Sargagame et BOT-WOW de s’améliorer individuellement ET collectivement :
les améliorations circulent dans les deux sens, avec qualification, validation et mesure.

## Système central (dans ce dépôt)

- Identifier une amélioration dans un repository source.
- Analyser son utilité pour les autres projets.
- Distinguer capacités universelles vs capacités métier vs expérimentales.
- Vérifier dépendances et compatibilités.
- Préparer les adaptations.
- Créer des branches et PR dans les repositories concernés.
- Mesurer les résultats après intégration.

## Trois catégories

1. **Universal Capabilities** : contrôle desktop, souris, clavier, navigateur, sessions, supervision, récupération, orchestration, tests, observabilité. → diffusables.
2. **Project-Specific Capabilities** : SEO Sargagame, prévisions plages, acquisition touristique, funnel BOT-WOW, conversion SaaS. → jamais diffusées aveuglément.
3. **Experimental Capabilities** : nouvelles méthodes/agents non validés. → isolés jusqu’à validation.

## Distribution bidirectionnelle

- Factory améliore le contrôle OpenCode → Sargagame et BOT-WOW l’adoptent après leurs tests.
- Sargagame découvre une amélioration réutilisable → Factory la qualifie et la propose aux autres.
- Chaque repository peut être source d’innovation.

## Validation obligatoire avant distribution

1. Identifier fichiers et dépendances concernés.
2. Vérifier la compatibilité.
3. Créer une branche dédiée.
4. Exécuter les tests du projet cible.
5. Vérifier l’absence de régression.
6. Ouvrir une PR distincte.
7. Conserver un mécanisme de rollback.

Interdits : remplacer directement le code métier d’un projet par celui d’un autre ; partager secrets/données privées/configs confidentielles.

## Mémoire collective (3 niveaux)

1. Mémoire technique collective (partagée).
2. Mémoire interne Factory.
3. Mémoire métier indépendante par projet.

Apprentissages documentés, versionnés, consultables.

## Mesure (sans inventer de gains)

- nombre d’améliorations découvertes ;
- nombre qualifiées ;
- nombre de PR générées ;
- taux d’intégration réussie ;
- régressions détectées ;
- temps économisé ;
- gains techniques et commerciaux mesurables.

## Autonomie

Chaque instance peut identifier ses faiblesses, proposer des améliorations, développer ses capacités, tester, proposer aux autres. Factory coordonne les capacités communes sans empêcher l’autonomie des projets. Diffusion automatisable, mais chaque intégration respecte les contrôles/permissions/règles du dépôt destinataire.

## Statut

Système à implémenter progressivement dans les repositories existants, sans interrompre leurs missions commerciales. Cette documentation pose le cadre ; l’implémentation (qualification, PR automatiques, métriques) est le prochain jalon.
