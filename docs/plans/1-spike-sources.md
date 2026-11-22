# Plan - #1 Spike : source des séances + correspondance TMDB

Branche : `feat/1-spike-sources`. Time-box : 1 jour. Livre une décision, pas du code de production.

## Étapes

1. **data.gouv.fr « Programmation des cinémas indépendants »**
   - Trouver le jeu de données, télécharger le CSV du jour dans `pipeline/spikes/data/` (non versionné).
   - Prototype `pipeline/spikes/datagouv_probe.py` : lister les salles parisiennes présentes, croiser avec nos 20 salles, mesurer l'horizon (jours couverts), la présence de VO/VF, format, lien de réservation, et les champs film (titre, année, réalisateur).
   - Noter la licence (Licence Ouverte 2.0) et la fréquence de mise à jour.
2. **cip-paris.fr**
   - Regarder une fiche salle : HTML statique ou API JSON interne (onglet réseau). Lire les mentions légales / CGU et `robots.txt`.
   - Prototype `pipeline/spikes/cip_probe.py` si une API est exploitable : mêmes mesures qu'en 1.
3. **Sites des salles** (pour les salles non couvertes par 1 ou 2)
   - Pour chaque salle manquante : format de la page programme (HTML, JSON, iCal, widget de billetterie type Ticketingcine / Webedia / Veezi…), horizon, VO/VF, format, lien résa, CGU, `robots.txt`.
   - Regrouper par plateforme commune (réseau Action, Dulac, Écran Noir, billetterie partagée) pour limiter le nombre d'adaptateurs.
   - Un prototype par plateforme commune seulement, s'il y en a une qui couvre ≥ 2 salles.
4. **Correspondance TMDB**
   - Prototype `pipeline/spikes/tmdb_match_probe.py` : sur ≥ 100 titres réels distincts tirés des sources ci-dessus, tester la stratégie de `architecture.md` (recherche `language=fr-FR`, puis avec année, puis score titre normalisé + année ±1 + réalisateur, fuzzy). Mesurer le taux de correspondance automatique et le taux d'erreurs (vérification manuelle d'un échantillon).
   - Jeton TMDB : lu depuis `C:\dev\Projet_recsys_movie\.env` (`TMDB_READ_TOKEN`) via `python-dotenv`, sans l'afficher ni le copier dans ce repo. Aucune URL TMDB journalisée. Cache des réponses dans `pipeline/data/cache/` (déjà ignoré par git).
   - Sortie : taux, liste des échecs typiques (cycles, avant-premières, ciné-concerts, titres avec « + débat », courts, titres retraduits), stratégie retenue et premiers candidats pour `manual_overrides.csv`.
5. **Livrables doc**
   - `docs/spikes/01-sources.md` : tableau salle × source × jours couverts × VO/VF × format × lien résa × CGU, résultats TMDB, recommandation.
   - `docs/decisions.md` : décision de source (éventuellement par salle).
   - Dans le même doc spike : plan de découpage de #7 (premier adaptateur, la source qui couvre le plus de salles) et de #14 (sous-issues par source/plateforme), heure du cron pour #13 (d'après l'heure de mise à jour observée des sources).
   - Mettre à jour la Question ouverte 1 de `SPEC.md` et la note « adaptateurs » de `architecture.md`.

## Fichiers touchés

- `docs/plans/1-spike-sources.md` (ce plan)
- `docs/spikes/01-sources.md` (nouveau)
- `docs/decisions.md`, `docs/SPEC.md`, `docs/architecture.md`
- `pipeline/spikes/*.py` (nouveau, jetable), `pipeline/spikes/README.md`
- `.gitignore` : `pipeline/spikes/data/` (données brutes et réponses téléchargées)
- `pipeline/pyproject.toml` : exclure `spikes/` de pytest ; ruff s'applique quand même (lint propre, pas de règle désactivée)

## Tests

- Pas de tests pour les prototypes (critère de l'issue : « non testés, non importés par le pipeline »).
- `uv run pytest`, `ruff check`, `ruff format --check` et les commandes front doivent rester verts.

## Hors scope

- Aucun adaptateur de production, aucune écriture en base (c'est #7).
- Pas de création des sous-issues de #14 sur GitHub sans ton accord : je les propose dans le doc spike.
- Pas de vérification de la liste UGC (Question ouverte 2).

## Garde-fous

- Pas d'Allociné ni d'agrégateur dont les CGU interdisent la collecte : si une salle n'est dispo que par là, elle est marquée « impossible » avec l'explication.
- Requêtes polies : peu de requêtes, User-Agent générique, respect de `robots.txt`.
