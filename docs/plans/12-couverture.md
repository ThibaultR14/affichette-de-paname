# Plan #12 - Couverture par salle

Issue : #12. Branche : `feat/12-couverture`, depuis `main` (indépendante de #11 : aucun fichier en commun).

## Ce qui existe déjà

- Pipeline (#7) : `sync_cinema` écrit `last_import_at`, `last_import_ok = true`, `coverage_until` (date Paris de la dernière séance importée, inchangée si aucune séance). `mark_failed` écrit `last_import_at` et `last_import_ok = false`. Tests dans `test_upsert.py` et `test_main.py`. **Critère 1 déjà rempli**, à un détail près (ci-dessous).
- Front : `CinemaList` (bas de l'accueil, « les 19 salles ») lit `fetchCinemas` (`id, name, arrondissement, accepts_ugc`).
- `docs/design.md` § « Couverture d'une salle » : ligne `muted` sous le nom, « programme connu jusqu'au jeu. 27 · mis à jour il y a 3 h » ; échec → Caveat « (on n'a pas pu mettre à jour cette salle aujourd'hui) ».

## Le problème de `last_import_at`

`mark_failed` écrase `last_import_at` : une salle en échec depuis 3 jours afficherait « mis à jour il y a 2 h » alors que son programme date d'il y a 3 jours. Le « mis à jour il y a » doit dater le **dernier import réussi**.

**Choix proposé** : nouvelle colonne `cinemas.last_success_at timestamptz` (migration, remplie depuis `last_import_at` là où `last_import_ok`). `sync_cinema` l'écrit, `mark_failed` ne la touche pas. `last_import_at` garde son sens (dernière tentative, utile pour #13).
Alternative sans migration : `mark_failed` n'écrit plus `last_import_at`. Moins de travail, mais on perd la date de la dernière tentative dans `cinemas`.

## Comportement (front)

Dans `CinemaList`, sous chaque salle, une ligne `muted` :

| État | Ligne | Annotation Caveat |
|---|---|---|
| jamais importée (`last_success_at` null, pas d'échec) | « pas encore de programme pour cette salle » | - |
| import OK | « programme connu jusqu'au jeu. 27 · mis à jour il y a 3 h » | - |
| dernier import en échec, déjà réussi avant | même ligne (dernier succès) | « (on n'a pas pu mettre à jour cette salle aujourd'hui) » |
| en échec, jamais réussie | - | même annotation |
| OK mais `coverage_until` null (aucune séance jamais) | « mis à jour il y a 3 h » seul | - |

- Date : « jeu. 27 » si elle tombe dans `[aujourd'hui − 6 j, aujourd'hui + 7 j]`, sinon « 27 nov. » (sinon « jeu. 27 » est ambigu pour une couverture vieille de plusieurs semaines).
- Durée : « à l'instant » (< 1 min), « il y a 12 min », « il y a 3 h », « il y a 2 j » (arrondi à l'unité inférieure). Calculée au rendu (`now` injectable pour les tests).
- Le nom de la salle, la pastille `ugc` et l'arrondissement restent sur leur ligne ; la couverture passe dessous (pleine largeur).

## Étapes

1. **Migration** `supabase/migrations/20261123000000_cinemas_last_success.sql` : `add column last_success_at timestamptz`, backfill. Test pgTAP : colonne lisible par `anon`.
2. **Pipeline** `upsert.py` : `sync_cinema` ajoute `last_success_at = now` ; `mark_failed` inchangé. Tests : `test_upsert.py` (succès écrit `last_success_at`, échec ne l'écrit pas), `test_main.py` (salle en échec garde son `last_success_at`).
3. **`lib/cinemas.ts`** : `Cinema` gagne `coverageUntil: string | null`, `lastSuccessAt: string | null`, `lastImportOk: boolean | null` ; select étendu.
4. **`lib/coverage.ts`** (pur) : `coverageDate(day, today)`, `timeAgo(instant, now)`, `coverageStatus(cinema, now)` → `{ line: string | null; failed: boolean }`.
5. **`CinemaList`** : affiche la ligne et l'annotation ; prop `now` optionnelle. CSS dans `CinemaList.css`.
6. **`/styleguide`** : exemple de ligne de couverture (OK + échec), si la page montre déjà la liste des salles ; sinon ajout d'un petit exemple statique.
7. Docs : `architecture.md` (colonne, `lib/coverage.ts`), `decisions.md` (`last_success_at` vs `last_import_at`), SPEC modèle de données.

## Tests (écrits d'abord)

- `coverage.test.ts` : `timeAgo` (0 s, 59 s, 12 min, 3 h, 25 h → 1 j) ; `coverageDate` (dans la semaine → « jeu. 27 », vieille → « 27 nov. ») ; `coverageStatus` pour les 5 états du tableau.
- `cinemas.test.ts` : nouveau select et mapping.
- `CinemaList.test.tsx` : ligne affichée, annotation en échec, salle jamais importée.
- pytest : voir étape 2. pgTAP : étape 1.

## Hors scope

- Couverture affichée dans les cartes film ou la fiche (la SPEC la met « par salle ») et dans le panneau de filtres.
- Rapport / alerte d'échec (#13), nouvelles sources (#14).
- Rafraîchir « il y a … » sans rechargement de la page.
