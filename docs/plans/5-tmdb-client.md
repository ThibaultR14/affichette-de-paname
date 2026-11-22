# Plan #5 - Client TMDB + fiche film en base

Branche : `feat/5-tmdb-client`.

## But
Porter le client TMDB de Recsys (`Projet_recsys_movie/pipeline/enrich_tmdb.py`) dans le pipeline, et écrire `upsert_film(tmdb_id)` qui remplit la table `films` en `fr-FR`.

## Fichiers

| Fichier | Contenu |
|---|---|
| `pipeline/affichette/tmdb.py` (nouveau) | `RateLimiter`, `Tmdb` (session, `_get` avec réessais, `_cached`, `movie(tmdb_id)`), `slim_movie`, `release_year`, `is_fresh`, `purge_old_cache` |
| `pipeline/affichette/db.py` (nouveau) | client PostgREST minimal : `Db.from_env()`, `upsert(table, rows, on_conflict)` |
| `pipeline/affichette/films.py` (nouveau) | `film_row(movie, fetched_at)` (pur) et `upsert_film(tmdb_id, tmdb, db)`. Petit CLI `uv run python -m affichette.films <id>… [--dry-run]` pour un essai à la main |
| `pipeline/tests/fixtures/tmdb/movie_426.json` (nouveau) | réponse `/movie/426?append_to_response=credits&language=fr-FR` réduite, écrite à la main (Sueurs froides : titre fr ≠ original, réalisateur en double) |
| `pipeline/tests/test_tmdb.py`, `test_db.py`, `test_films.py` (nouveaux) | tests hors ligne |
| `docs/architecture.md`, `docs/decisions.md` | `db.py`, `films.py`, choix PostgREST |

## Différences avec Recsys
- **Jeton Bearer seulement** : plus de repli sur `TMDB_API_KEY`, dont la clé v3 passe dans l'URL (risque de journalisation). `TMDB_READ_TOKEN` lu depuis l'environnement, `.env` chargé par `python-dotenv` (racine du repo).
- `language=fr-FR` sur chaque appel ; `slim_movie` garde en plus `runtime` et `overview`, et enlève ce dont on n'a pas besoin (vote_count, langue, pays, imdb_id).
- `logging` au lieu de `tqdm.write` : on ne journalise que le chemin (`/movie/147`), jamais l'URL, les paramètres ni les en-têtes.
- Pas de `/find`, pas de polars. La recherche (`/search/movie`) viendra avec `matching.py` (#7), sur le même `_get` et le même cache.
- Purge à 6 mois lancée à chaque création du client `Tmdb` (donc par tout job qui l'utilise), `.tmp` orphelins compris. `Retry-After` plafonné à 60 s ; un 200 non-JSON est réessayé.
- Cache dans `pipeline/data/cache/tmdb/movie/<id>.json` (`{"fetched_at", "data"}`), déjà ignoré par `.gitignore`. Une réponse 404 est mise en cache aussi (`data: null`).

## Écriture en base
- Pas de dépendance `supabase-py` : un `POST /rest/v1/films?on_conflict=tmdb_id` avec `Prefer: resolution=merge-duplicates`, via `requests` (déjà là). Clé `service_role` en en-têtes `apikey` + `Authorization`, jamais journalisée. Erreur HTTP → exception avec le code et le corps PostgREST, sans l'URL complète.
- `film_row` : `title` = titre fr, à défaut titre original (colonne `not null`) ; `year` depuis `release_date` ; `runtime_min` = `runtime` si > 0, sinon `null` ; `directors` dédoublonnés dans l'ordre TMDB ; `overview` vide → `null`.
- `tmdb_fetched_at` = date de l'appel TMDB (celle du cache), pas `now()`. Ainsi la base sait quand la donnée a été récupérée, pour le refresh à 30 jours et la purge à 6 mois.
- 404 TMDB → `upsert_film` renvoie `None` et n'écrit rien.

## Tests (sans réseau, faux `requests.Session`)
- `tmdb` : en-tête `Authorization: Bearer …`, `language=fr-FR` ; 429 avec `Retry-After` puis 200 (sleep patché) ; 5xx réessayé ; abandon après N essais ; 404 → `None` ; 401 → erreur explicite ; aucun log (caplog) ne contient le jeton ni `api.themoviedb.org` ; jeton absent → erreur ; cache frais (< 30 j) réutilisé sans HTTP ; cache de 31 j rechargé ; `purge_old_cache` supprime > 6 mois et les fichiers illisibles, garde les récents ; `slim_movie` sur la fixture.
- `db` : URL, `on_conflict`, en-têtes `Prefer` et auth, corps JSON ; erreur 4xx → exception sans la clé.
- `films` : `film_row` sur la fixture (titres, année, réalisateurs, durée, synopsis, affiche, `tmdb_fetched_at`) ; cas limites (pas de titre fr, durée 0, pas de date) ; `upsert_film` appelle `db.upsert` avec la bonne ligne ; 404 → rien écrit.

## Hors scope
- Recherche titre → TMDB et `title_matches` (#7, `matching.py`).
- Refresh des `films` de plus de 30 jours et purge des `films` de plus de 6 mois en base : à brancher dans `main.py` (#13). `tmdb_fetched_at` est rempli correctement pour ça.
- Edge Function `tmdb-search` (favoris).
