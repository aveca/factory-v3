# Factory V3 — Lien dépôt GitHub

## Dépôt canonique

- URL : https://github.com/aveca/factory-v3
- Visibilité : PUBLIC
- Branche principale : `master`
- Dernier commit master : `4b3049233f7ca120fbffe6b712d5f4525bc77aae`
- Copie locale liée : `C:\factory\factory-v3-clone`

## Chemin local et raccordement

- Dossier local lié au dépôt : `C:\factory\factory-v3-clone`
- Remote `origin` : `https://github.com/aveca/factory-v3.git`
- Vérification : `git remote -v`, `git status`, `git branch -vv`, `git ls-remote origin`

## Note sur `C:\factory`

Le dossier racine `C:\factory` n'est **pas** un dépôt Git : c'est un espace de travail multi-projets
(84 Go, ~200 000 fichiers) contenant des journaux, états, caches et données potentiellement sensibles.
Le convertir en dépôt Git et y pousser l'intégralité du contenu publierait des secrets et dépasserait
les limites GitHub. Il ne doit donc **pas** être raccordé directement à `aveca/factory-v3`.

La copie de travail officielle de Factory V3 est `C:\factory\factory-v3-clone`.

## Procédure push/pull

```powershell
cd C:\factory\factory-v3-clone
git fetch origin
git status
git pull --ff-only
# nouvelle branche de travail
git checkout -b feat/<nom>
# ... commits ...
git push -u origin feat/<nom>
```

## Règles de branches et PR

- Ne jamais pousser directement sur `master` sans PR validée.
- Une branche = une mission (nommage `feat/`, `fix/`, `docs/`, `audit/`).
- Jamais `git push --force` ni `--mirror`.
- Vérifier l'absence de secrets avant tout push (`.env`, tokens, clés).

## Récupération après incident

```powershell
cd C:\factory\factory-v3-clone
git fetch origin
git checkout master
git reset --hard origin/master   # uniquement si aucun travail local non sauvegardé
```

En cas de dépôt local corrompu : recloner dans un nouveau dossier, ne jamais écraser `C:\factory`.
