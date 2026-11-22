# Plan #6 - Correspondance titre → TMDB

Branche : `feat/6-tmdb-matching`.

## But
`matching.py` associe une séance (titre brut, salle, et les indices de la source) à un `tmdb_id`, ou à `null`, avec la stratégie retenue par le spike #1 (`docs/spikes/01-sources.md`, « Stratégie retenue »). Un rapport liste les non-correspondances à chaque exécution.

## Ordre de résolution
1. **`manual_overrides.csv`** : clé (titre normalisé, salle). La salle vide vaut pour toutes les salles, et la ligne propre à une salle passe avant. Un `tmdb_id` vide force « pas de film » (pour un événement qu'on confondrait avec un film).
2. **`tmdb_hint`** de la source (`_donnees_imdb.id` de SCARE, 107 accords sur 107 dans le spike) → `method = source`.
3. **Cache `title_matches`** : clé (titre normalisé, salle, année). Un résultat trouvé est réutilisé pendant 30 jours, un « pas trouvé » pendant 7 jours (TMDB ajoute des titres fr, les règles évoluent).
4. **Recherche TMDB** (`/search/movie`, `fr-FR`), règles du spike :
   - nettoyage du titre (`clean_title`, `director_hint`, `clean_director` repris du probe, avec ses cas corrigés : « de la ville », « Oslo, 31 août », préfixes d'événement) ;
   - similarité de titre sur le titre fr et le titre original (`normalize_title` existant + `SequenceMatcher`) ;
   - **réalisateur** : sur les 5 premiers résultats, similarité ≥ 0,7 et réalisateur commun → `method = director`, score = 0,6 + 0,4 × similarité, seuil 0,75. Les réalisateurs viennent de `tmdb.movie(id)` (même appel et même cache que `films`, rien de plus à appeler ensuite) ;
   - **titre seul** : score = similarité × 0,95 (1er résultat) ou × 0,8, × 0,9 si un réalisateur est connu mais ne concorde pas ; seuil 0,9 → `method = title` ; refus si plusieurs résultats ont le même titre (≥ 0,95) → `none:ambiguous` ;
   - **repli filmographie** : réalisateur connu mais aucun candidat validé → `/search/person` (département Directing), puis `/person/{id}/movie_credits` (job Director), similarité ≥ 0,8 → `method = director` ;
   - **année** (nouveau, aucune source du spike ne la donne, Webedia et Dulac oui) : un candidat dont l'année diffère de plus de 1 est écarté, et l'ambiguïté est levée si un seul homonyme tombe à ±1 an.
5. Sinon `tmdb_id = null`, avec la raison (`empty`, `no_result`, `ambiguous`, `low_score`).

## Seuil et mesure
- Seuils de départ = ceux du spike. `pipeline/scripts/eval_matching.py` (outil manuel, pas un test) rejoue l'échantillon de 220 titres du spike (`spikes/data/scare_titles.json`, local) **sans le `tmdb_hint`**, avec le vrai client (cache TMDB du pipeline), et affiche : taux de correspondance, accord avec l'id SCARE, nombre par méthode, et un balayage des deux seuils.
- Critère : taux ≥ 149/220 (68 %) et accord avec SCARE ≥ celui du spike (107/107). Les chiffres obtenus vont dans la PR et dans `docs/decisions.md`.
- Le script a besoin du réseau (environ 600 appels au premier passage, puis le cache) et de `TMDB_READ_TOKEN` : je le lance une fois, ici.

## Fichiers

| Fichier | Contenu |
|---|---|
| `pipeline/affichette/matching.py` (nouveau) | `MatchQuery` (raw_title, cinema_id, director_hint, year_hint, tmdb_hint, event_label), `Match` (tmdb_id, method, score, reason), `clean_title`, `director_hint`, `clean_director`, `title_score`, `load_overrides(path)`, `Matcher(tmdb, overrides, store).match(query)`, `MatchReport` (compteurs par méthode, non-correspondances séparées en « événements probables » / « films », correspondances `title` à relire, `summary()` en texte). CLI d'essai : `uv run python -m affichette.matching "Titre" [--director …] [--year …] [--cinema …]` |
| `pipeline/affichette/tmdb.py` | `search_movie(query, year=None)`, `search_person(name)`, `person_directing(person_id)` : réponses réduites (id, titres, date ; département) dans le cache existant (`search/`, `person/`, `person_credits/`, clé = titre normalisé + hachage court) |
| `pipeline/affichette/db.py` | `select(table, params) -> list[dict]` (GET PostgREST), même gestion d'erreur que `upsert` |
| `pipeline/affichette/matching.py` → `TitleMatchStore` | lit les `title_matches` d'une salle au début (un GET par salle), écrit les nouveaux résultats en un upsert à la fin (`on_conflict=normalized_title,cinema_id,year_hint`). Version en mémoire pour les tests et le `--dry-run` |
| `pipeline/manual_overrides.csv` (nouveau) | en-tête `title,cinema_id,tmdb_id,note`. `title` peut être le titre brut collé tel quel, il est normalisé au chargement. Lignes de départ : les cas du spike (« Sabrina » → 1954 pour la salle concernée, PARANOID PARK, …) si je les retrouve dans le CSV de résultats |
| `supabase/migrations/<date>_title_matches_method.sql` (nouveau) | `method in ('override','source','director','title','none')` à la place de `exact/fuzzy/override/none`, qui ne correspond plus à la stratégie. Table vide en prod, donc pas de reprise de données |
| `supabase/tests/rls.test.sql` | l'insert de test passe de `'exact'` à `'title'` |
| `pipeline/scripts/eval_matching.py` (nouveau) | voir « Seuil et mesure » |
| `pipeline/tests/test_matching.py` (nouveau), `test_tmdb.py`, `test_db.py` | voir ci-dessous |
| `docs/architecture.md`, `docs/decisions.md` | ordre réel, overrides, méthodes, durées de cache, chiffres mesurés |

Les overrides et le `tmdb_hint` ne sont pas écrits dans `title_matches` : le CSV et la source restent la vérité, et le cache ne garde que les résultats de recherche.

## Tests (hors ligne)
- `test_matching.py` avec un faux client TMDB en dictionnaire (recherches, réalisateurs, filmographies écrits à la main) :
  - nettoyage : préfixes d'événement, `[7/13]`, `+ débat`, `4K`, « Oslo, 31 août » intact, « de la ville » non pris pour un réalisateur, `LOSEY Joseph` → `Joseph Losey` ;
  - ordre : override > hint > cache > recherche ; override de salle > override global ; override vide → `null` ; override et hint n'appellent pas TMDB ;
  - réalisateur qui concorde accepté à 0,75 ; *Gruffalo* (même réalisateur, titre voisin < 0,7) refusé ; *Sabrina* sans réalisateur → `ambiguous` ; *Sabrina* avec `year_hint=1954` → accepté ; candidat à 3 ans d'écart écarté ; repli filmographie (*Eva*, Losey) ; titre seul à 0,89 refusé, à 0,9 accepté ;
  - cache : entrée trouvée de 29 jours réutilisée sans TMDB, de 31 jours recalculée, « none » de 8 jours recalculé ; un nouveau résultat est mis à écrire ;
  - rapport : compteurs, événements séparés des films, correspondances `title` listées, `summary()` sans URL ni jeton.
- `load_overrides` : normalisation du titre, salle vide, `tmdb_id` vide, ligne invalide → erreur qui cite le numéro de ligne.
- `test_tmdb.py` : `search_movie` envoie `query`, `language=fr-FR`, `year` si donné ; réponse réduite et mise en cache (deuxième appel sans HTTP) ; `search_person` / `person_directing` filtrent Directing / Director.
- `test_db.py` : `select` (URL, params, en-têtes, erreur sans la clé).
- `manual_overrides.csv` versionné : un test le charge pour vérifier qu'il reste valide.

## Hors scope
- Brancher le matcher dans l'import, écrire `screenings.tmdb_id` et upserter `films` (#7 pour SCARE, #13 pour `main.py`). Le rapport est prêt à être appelé par `report.py`.
- Doubles programmes (« FREDA + BOAT PEOPLE » → premier film seulement), comme dans le spike.
- Purge de `title_matches` : il ne contient que des id et des scores, pas de donnée TMDB.
