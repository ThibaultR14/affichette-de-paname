# Plan #24 - Adaptateur Dulac (Reflet Médicis)

Branche : `feat/24-dulac`, empilée sur `feat/13-cron-import` (PR #44 pas encore fusionnée). Sous-issue de #14.

## But
Importer les séances du Reflet Médicis depuis `GET https://www.dulaccinemas.com/api/home-bootstrap?days=7`. La salle est déjà dans le seed (`source = 'dulac'`, `source_ref = '583'`).

## Ce que dit la réponse (extrait du spike, 22/11)
- `seances_week[]` : `id`, `date` (UTC sans « Z » : `title` « …:24/11/2026 20:00:00 » pour `date` `2026-11-24T19:00:00`), `version` (`VF` | `VOST`), `format` (toujours vide), `booking_url` (ticketingcine, `#showsession?id=emsx…`), `is_cancelled`, `is_special`, `type` (`standard` | `avant-premiere`), `event_label`, `film_id`, `salle_id`.
- Pas de `cinema_id` sur la séance : salle → cinéma par `salles_by_id[salle_id].cinema_id` (`583` = Reflet Medicis, salles 584, 586, 596).
- `films_by_id[film_id]` : `title`, `original_title`, `duration` (min), `directors[]`, `director`, `year` (souvent 0), `release_date` (date de **sortie ou ressortie** en France : 2026 pour *Pierre ou les ambiguïtés*), `projection_formats[]`.
- `meta.truncated`, `meta.seances_max` (1 500).
- **Doublon réel** : *Mysterious Skin* le 24/11 à 20 h apparaît deux fois (séances 18652 et 18657, deux fiches film), mais avec le même `showsession id=emsx082400076647`.

## Choix
- **Un seul appel par run**, mémorisé (succès ou échec) comme `ScareSource`, même si une seule salle l'utilise aujourd'hui : les 4 autres salles Dulac sont hors liste.
- **Filtre** : `salles_by_id[salle_id].cinema_id == cinema.source_ref`. Salle absente de `cinemas_by_id` → `SourceError` (renommage : sinon toutes ses séances seraient annulées).
- **Heure** : `date` naïve → UTC ; si elle a un décalage, on le garde. Illisible → séance ignorée avec un avertissement.
- **`source_key`** = `dulac:<cinema_id>:<id de séance>`. Révisé après la review : au départ, c'était l'id `showsession` de la billetterie, mais il change quand le lien de réservation apparaît (annulation puis réinsertion).
- **Dédoublonnage** sur (salle, heure de début), même si un seul des doublons a un lien : on garde la séance dont la fiche film est la plus complète (titre original, réalisateur, date de sortie, lien de réservation), puis l'id le plus ancien.
- **Garde-fous ajoutés après la review** : aucune salle rattachée au cinéma dans `salles_by_id` → `SourceError` ; séance sans fiche film → ignorée avec un avertissement, et `SourceError` si aucune séance de la salle n'a de fiche (sinon tout serait annulé).
- **Annulées** (`is_cancelled`) : ignorées, donc marquées `cancelled_at` par `sync_cinema` si elles étaient en base.
- **Version** : `VOST` → `VOSTFR`, `VF` → `VF`, sinon `normalize_version`.
- **Format** : `format`, puis `projection_formats`, puis `normalize_format` sur le titre et sur `info`.
- **Indices TMDB** : `raw_title = title` ; `director_hint` = `directors` joints par « , » (ou `director`) ; `runtime_hint = duration` si > 0 ; `year_hint = year` si > 0. On **n'utilise pas** `release_date` : pour une ressortie, ce serait l'année de ressortie et ±1 rejetterait le bon film.
- **`event_label`** : `event_label` de la séance seulement si `is_special` ou `type != standard` (« first session » sur une séance standard n'est pas un événement).
- **Pannes** : réseau / HTTP ≠ 200 / JSON illisible ou sans `seances_week` → `SourceError` sans URL. `truncated: true` → `SourceError` (des séances manquantes seraient annulées). 0 séance sur les 5 salles → `SourceError` (panne, pas « tout annulé »). Une salle présente sans séance dans la fenêtre reste un import réussi.
- User-Agent générique comme SCARE, `timeout` 30 s.
- **CGU** : non lues, comme convenu (site local, cf. `local-first-legal-later`). Le spike note « à lire avant la mise en ligne », et la case de l'issue reste ouverte.

## Fichiers
| Fichier | Contenu |
|---|---|
| `pipeline/affichette/sources/dulac.py` (nouveau) | `DulacSource(session)`, `parse_seance(seance, film, cinema_id)`, `dulac_version` |
| `pipeline/affichette/main.py` | `{"scare": ScareSource(), "dulac": DulacSource()}` |
| `pipeline/tests/fixtures/dulac/home-bootstrap.json` (nouveau) | extrait réel du 22/11 réduit : séances du Reflet Médicis (dont le doublon *Mysterious Skin*, l'avant-première, « first session ») + 2 séances d'autres salles Dulac, fiches film sans affiche/synopsis/casting, `salles_by_id`, `cinemas_by_id` sans les champs d'accessibilité. Une séance passée à `is_cancelled: true` et une à 23 h 30 UTC (lendemain à Paris), signalées dans le README des fixtures |
| `pipeline/tests/test_dulac.py` (nouveau) | voir ci-dessous |
| `pipeline/tests/fixtures/README.md`, `docs/architecture.md`, `docs/spikes/01-sources.md` | description de la fixture, du contrat Dulac, du doublon et de `release_date` |

## Tests (hors ligne)
- Seules les séances du Reflet Médicis sont gardées ; un seul appel HTTP (`days=7`) même pour deux `fetch`.
- `date` sans « Z » lue en UTC (`2026-11-24T19:00:00` → 19:00 UTC = 20:00 Paris) ; 23:30 UTC le 27/11 → 28/11 à Paris, dans la fenêtre ; filtrage par fenêtre.
- VOST → VOSTFR, VF → VF ; `booking_url` repris ; `year = 0` → `year_hint None` ; `release_date` ignorée ; `director_hint`, `runtime_hint`.
- Séance annulée absente ; doublon *Mysterious Skin* → une seule séance, fiche complète gardée ; `source_key` sur l'id de séance, indépendant de `booking_url` ; doublon avec et sans lien fusionné ; salle sans salle de projection rattachée, fiches film absentes.
- `event_label` : avant-première oui, « first session » standard non.
- Erreurs : réseau (message sans URL), HTTP 500, JSON illisible, `truncated`, 0 séance, salle absente de `cinemas_by_id`, `source_ref` manquant.
- `test_main.py` : un run avec `dulac` dans les sources importe `reflet-medicis` (si le test existant le permet sans trop de plomberie).

## Vérification à la main
- `uv run python -m affichette.main --dry-run --cinema reflet-medicis` : un vrai appel à l'API Dulac, lecture de la base cloud, aucune écriture. Je te montre le rapport (séances, taux de correspondance TMDB).

## Hors scope
- Les 4 autres salles Dulac (hors des 19).
- Lecture des CGU (avant la mise en ligne).
- Indice `original_title` pour la correspondance (`RawScreening` n'a pas ce champ ; à voir si le taux de correspondance du Reflet est mauvais).
