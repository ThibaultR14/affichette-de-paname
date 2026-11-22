# Plan #7 - Premier adaptateur (SCARE) + upsert idempotent

Branche : `feat/7-scare-import`.

## But
Premier import de bout en bout : jeu SCARE (data.gouv.fr) → normalisation → correspondance TMDB (#6) → `films` → `screenings` → `cinemas` (état d'import) → `import_runs`. Salles couvertes : les 6 salles `source = 'scare'` du seed (Champo, Saint-André-des-Arts, Grand Action, plus les événements de Louxor, Sept Parnassiens, Épée de Bois).

## Choix
- **Fenêtre** : séances de `[aujourd'hui 00:00 Paris, +7 jours[`, comme la SPEC. `coverage_until` = date (Paris) de la dernière séance importée de la salle. Les séances au-delà de 7 jours ne sont pas importées (on évite des centaines de recherches TMDB inutiles) ; elles arriveront avec les imports suivants.
- **`source_key`** = `scare:<cinema_id>:<showid>` (`showid` unique sur les 440 lignes du spike). Je vérifie sa stabilité en comparant l'extrait du spike (22/11 19 h) à un appel réel pendant l'implémentation.
- **Version** (`filmversion` + `filmaudio`) : `VOST` ou `ST` dans l'audio → `VOSTFR` ; `VERSION_ORIGINAL`, `VO` → `VO` ; `VF`, `VERSION_LOCAL`, `VERSION_ORIGINAL_LOCAL` (films français : *Huit femmes*, *Intouchables*) → `VF` ; vide → `null`.
- **Format** : SCARE n'a pas de champ. `normalize_format` sur le titre puis sur `description` (« Projection 35mm » existe dans l'extrait).
- **Durée** : `filmduration` est en **secondes** (5160 pour un film de 86 min) → `runtime_hint` en minutes. Pas utilisé pour l'heure de fin (on prend la durée TMDB, cf. SPEC), seulement passé dans `RawScreening`.
- **Réservation** : `showurl` si présent, sinon `null` (le front retombera sur `website_url` de la salle, pas de duplication en base).
- Lignes sans `showstart` ignorées ; lignes de salles hors de notre liste ignorées (Balzac, Entrepôt…).
- **Correspondance** : `Matcher` de #6 avec `tmdb_hint = _donnees_imdb.id`, `director_hint = filmdirector`, `event_label = evenement`, `DbTitleMatchStore` vidé en fin de run.
- **Films** : pour chaque `tmdb_id` trouvé, absent de `films` ou rafraîchi il y a plus de 30 jours → `upsert_film` (#5). Si TMDB ne connaît pas l'id (404), la séance passe à `tmdb_id = null` (sinon la clé étrangère casse l'upsert).
- **Upsert `screenings`** (`on_conflict=source_key`) : `cinema_id, tmdb_id, raw_title, starts_at (UTC), version, format, booking_url, source_key, last_seen_at = now, cancelled_at = null` (une séance qui réapparaît est « désannulée »). `first_seen_at` n'est pas envoyé : PostgREST ne met à jour que les colonnes envoyées, donc il garde sa valeur d'insertion.
- **Annulations** : salle importée avec succès → les séances non annulées de la salle dans `[max(now, début fenêtre), fin fenêtre[` absentes de l'import reçoivent `cancelled_at = now` (PATCH filtré par `source_key=in.(…)`). Les séances passées et celles au-delà de la fenêtre ne sont pas touchées.
- **Échec** : toute exception sur une salle (source, TMDB, base) → `import_runs.status = 'error'` avec le message, `cinemas.last_import_at = now, last_import_ok = false`, rien d'autre de touché (ni séances, ni `coverage_until`). Les autres salles continuent. Si l'appel SCARE échoue, toutes les salles SCARE sont en échec. Si SCARE répond **0 ligne parisienne**, c'est traité comme une panne de la source (sinon toutes les séances futures seraient annulées).
- **`import_runs`** : une ligne par salle, insérée en fin de traitement de la salle (`started_at`, `finished_at`, `status`, `n_screenings`, `n_unmatched`, `error`).
- **`--dry-run`** : lit la base (salles, films connus, séances existantes, cache `title_matches`) mais n'écrit rien. Les écritures prévues sont affichées (compteurs par table et par salle). TMDB est appelé normalement (cache local).
- **`--cinema <id>`** (répétable) : limite l'import à ces salles ; id inconnu ou sans source → erreur.
- Rapport en fin de run : par salle (statut, séances, non-correspondances, annulations, couverture), plus `MatchReport.summary()`. Code de sortie 1 si au moins une salle est en échec (pour #13).

## Fichiers

| Fichier | Contenu |
|---|---|
| `pipeline/affichette/sources/__init__.py` | `RawScreening` (dataclass gelée, champs de `architecture.md`), `Cinema` (id, name, source, source_ref, website_url), `Source` (Protocol : `fetch(cinema, start, end)`), `SourceError` |
| `pipeline/affichette/sources/scare.py` (nouveau) | `ScareSource(session)` : un seul téléchargement paginé (`qs=cinecp:75*`, `size=1000`, `next`) par run, mémorisé ; `fetch(cinema, start, end)` filtre par `cinenom == source_ref` et par fenêtre ; `parse_row(row, cinema_id)` ; `scare_version(version, audio)`. User-Agent générique, erreurs réseau sans URL complète |
| `pipeline/affichette/normalize.py` | `to_utc(dt)` (refuse une date naïve), `paris_day_bounds(day, days)` |
| `pipeline/affichette/db.py` | `insert(table, rows)` et `update(table, values, filters)` (PATCH), même gestion d'erreur ; `DryRunDb` : lectures transmises, écritures enregistrées et jamais envoyées |
| `pipeline/affichette/upsert.py` (nouveau) | `screening_rows(...)`, `sync_cinema(db, cinema, rows, window, now) -> SyncResult` (upsert + annulations + `cinemas`), `mark_failed(db, cinema_id, now)` |
| `pipeline/affichette/main.py` (nouveau) | `run(db, tmdb, sources, cinemas, now, matcher) -> RunReport` testable, `main(argv)` avec `--dry-run`, `--cinema`. `uv run python -m affichette.main --dry-run` |
| `pipeline/tests/fixtures/scare/page1.json`, `page2.json` (nouveaux) | extrait réel des lignes parisiennes (Licence Ouverte 2.0), sans `filmposter`, `filmstoryline`, `filmtrailer`, `filmcast` ; dates réécrites autour d'un « maintenant » fixe ; couvre : film avec id TMDB, sans id, événement, VOST/ST, VERSION_ORIGINAL_LOCAL, « Projection 35mm », sans `showstart`, sans `showurl`, salle hors liste, séance hors fenêtre |
| `pipeline/tests/test_scare.py`, `test_upsert.py`, `test_main.py` (nouveaux), `test_db.py`, `test_normalize.py` | voir ci-dessous |
| `docs/architecture.md`, `docs/decisions.md`, `docs/spikes/01-sources.md` | contrat réel, stabilité de `showid`, choix version/fenêtre/0 ligne |

Pas de migration : le schéma de #3 a déjà toutes les colonnes et la contrainte unique sur `source_key`.

## Tests (hors ligne)
- `test_scare.py` : pagination (2 pages, `next`), un seul téléchargement pour plusieurs salles, filtrage par `cinenom` et fenêtre, ligne sans `showstart` ignorée, `source_key`, heure convertie en UTC (`+0100` sans deux-points), table de version complète, format depuis le titre/la description, durée en minutes, `tmdb_hint`, `director_hint`, `event_label`, `booking_url` null ; erreur HTTP / réseau → `SourceError` sans URL.
- `test_upsert.py` (faux `Db` en mémoire qui applique upsert/patch sur des dictionnaires) :
  - **idempotence** : deux syncs identiques → même nombre de lignes, `first_seen_at` inchangé, `last_seen_at` avancé ;
  - séance future disparue → `cancelled_at` ; séance passée ou hors fenêtre disparue → intacte ; séance réapparue → `cancelled_at = null` ;
  - `cinemas` : `last_import_ok`, `coverage_until`.
- `test_main.py` : run complet sur les fixtures avec faux TMDB et faux `Db` : séances écrites pour 3 salles, films upsertés seulement si absents/périmés, id TMDB inconnu → `tmdb_id` null ; salle en échec (source qui lève pour une salle) → séances intactes, `last_import_ok = false`, `import_runs` en `error`, autres salles OK ; SCARE à 0 ligne → toutes en échec, rien d'annulé ; `--dry-run` → aucune écriture envoyée ; `--cinema champo` → une seule salle ; `--cinema inconnue` → erreur ; code de sortie 1 si échec.
- `test_db.py` : `insert`, `update` (méthode PATCH, filtres, en-têtes), `DryRunDb`.
- `test_normalize.py` : `to_utc`, `paris_day_bounds` (passage à l'heure d'hiver).

## Vérification à la main
- `uv run python -m affichette.main --dry-run` contre le projet cloud, puis un vrai import (`--cinema champo` d'abord), relancé une seconde fois pour constater 0 nouvelle ligne. Je te demande avant d'écrire dans la base cloud.

## Hors scope
- Workflow GitHub Actions, issue automatique en cas d'échec (#13), alertes (#18), autres adaptateurs (#14, #24-#30).
- Purge des films de plus de 6 mois en base (pas encore de film en base ; à traiter avec #13).
- Affichage de la couverture (#12).
