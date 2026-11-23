# Plan #25 - Adaptateur HTML Filmothèque du Quartier Latin

Branche : `feat/25-filmotheque`, empilée sur `feat/24-dulac` (PR #45, elle-même sur #44). Sous-issue de #14.

## Ce que montre le site (relevé du 23/11, lafilmotheque.fr)
- `robots.txt` vide (200 avec notre User-Agent). WordPress, HTML rendu par le serveur.
- **Accueil** `https://lafilmotheque.fr/` (≈ 300 ko) :
  - `#front-this_week` : « Cette semaine du 18 au 24 novembre 2026 », une carte par film (titre, année, durée `01H55`, lien `/films/<slug>/`, salle et horaires par jour) ;
  - `#overlay-programmation` et `#overlay-programmation-next` : grilles horaires de la semaine en cours et de la suivante (« Programmation du 25 novembre au 1 décembre 2026 »). Le jour d'une séance n'y est donné que par sa position CSS (`left: 28.57 %`) : trop fragile pour en tirer les horaires, mais utile pour **lister les films** ;
  - note : « Le film débute 10 min après ouverture de la séance ».
- **Fiche film** `/films/<slug>/` (≈ 140 ko) : `h1` titre, `h3.director`, `ul.generic` (`1976`, `01H55`, `Couleurs`, `numérique 4K`), puis des blocs « Cette semaine » et « Prochainement » : `programmation-title R|B` (Salle Marilyn / Salle Audrey), `day-title` (« Mercredi 18 », sans mois), `day-hours` (`17H50`).
- Pas de VO/VF affichée, pas de lien de réservation par séance (le seul lien est le Cotecine général, qu'on ne suit pas).
- Particularités : même séance listée deux fois (« Mercredi 18 » et « mercredi 18 » à 19H30 pour *Ohong Village*), titres avec entités HTML (`&#8211;`), slugs en UTF-8 encodé.

## Choix
- **Accueil pour la liste des films, fiche film pour les séances.** On collecte les `/films/<slug>/` de `#front-this_week` et des deux grilles, puis une requête par fiche (≈ 45 par jour, 1 s entre deux, timeout 30 s). Les fiches donnent le jour en clair, le réalisateur et le format, et un seul parseur sert pour les deux semaines.
- **Dépendance** : `beautifulsoup4` (parseur `html.parser` de la stdlib, pas de lxml). Elle resservira pour #26 et #28.
- **Date** : « Mercredi 18 » est résolu vers l'unique date de `[aujourd'hui - 7 j, aujourd'hui + 21 j]` qui a ce jour de semaine et ce quantième ; ambigu ou introuvable → séance ignorée avec un avertissement. Heure `17H50` en Europe/Paris → UTC.
- **Heure de début = heure publiée** (ouverture de la séance), comme sur le site de la salle. Le décalage de 10 min avant le film n'est pas appliqué (noté dans `docs/decisions.md`).
- **`source_key`** = `filmotheque:<slug>:<R|B>:<AAAA-MM-JJTHH:MM>` (heure de Paris). Les doublons de la page fusionnent sur cette clé.
- **Format** : `normalize_format` sur chaque item de `ul.generic`, à défaut sur le texte de présentation de la fiche (ajout après la review) (`numérique 4K` → `4K`, `numérique 2K` → `DCP`, `35mm`…). **Version** : `normalize_version` sur les mêmes items, sinon `None`.
- **Indices TMDB** : `raw_title` = `h1` (entités décodées), `year_hint` = item à 4 chiffres, `runtime_hint` = `HHhMM` en minutes, `director_hint` = `h3.director`.
- **`booking_url` = None** : le front se replie sur `website_url` (https://lafilmotheque.fr/, la page programme), comme demandé par l'issue.
- **Seed** : `source = 'filmotheque'` (au lieu de `html`), `source_ref` null. Le registre de `main.py` gagne `"filmotheque": FilmothequeSource()`.
- **Pannes → `SourceError`** (les séances connues sont gardées) : accueil injoignable / HTTP ≠ 200 / aucun lien `/films/` ; **une seule fiche en échec** (sinon ses séances seraient annulées) ; salle, jour ou heure illisible sur une fiche (même raison, ajouté après la review) ; plus de 120 fiches (page anormale) ; aucune séance lue sur l'ensemble des fiches. Messages sans URL complète.
- **CGU** : mentions légales sans clause sur la collecte (spike) ; pas relu plus loin, cf. `local-first-legal-later`.

## Fichiers
| Fichier | Contenu |
|---|---|
| `pipeline/affichette/sources/filmotheque.py` (nouveau) | `FilmothequeSource(session, delay_s=1.0)`, `film_slugs(home_html)`, `parse_film_page(html, slug, cinema_id, today)`, `resolve_day(label, today)`, `parse_duration` |
| `pipeline/affichette/main.py` | ajout de la source au registre |
| `pipeline/pyproject.toml`, `uv.lock` | `beautifulsoup4` |
| `supabase/seed.sql` | `filmotheque` → `source = 'filmotheque'`, commentaire de l'en-tête |
| `pipeline/tests/fixtures/filmotheque/` (nouveau) | `home.html` réduit (scripts, SVG et segments vides retirés), 3-4 fiches réelles : *Taxi Driver* (4K, une salle), *Ohong Village* (deux salles, doublon), *Adieu Philippine* (« Prochainement » seulement), une fiche modifiée sans séance |
| `pipeline/tests/test_filmotheque.py` (nouveau) | voir ci-dessous |
| `pipeline/tests/fakes.py` | `FakeResponse.text` sur du HTML si besoin, `FakeSession` qui répond par URL |
| `docs/spikes/01-sources.md`, `docs/architecture.md`, `docs/decisions.md`, `pipeline/tests/fixtures/README.md` | contrat Filmothèque, statut V1 |

## Tests (hors ligne)
- `film_slugs` : slugs de la semaine et de la grille suivante, dédoublonnés, sans les liens d'événements ni `/la-filmo-plus/`.
- `resolve_day` : « Mercredi 18 » / « mardi 01 » (passage au mois suivant, et à l'année suivante en décembre) ; jour incohérent → `None`.
- `parse_film_page` : séances par salle (R/B), heure Paris → UTC (y compris après le changement d'heure), doublon fusionné, « Prochainement » lu, format `4K` / `DCP`, `year_hint`, `runtime_hint` (`01H55` → 115), `director_hint`, titre décodé, `booking_url` None.
- `fetch` : une requête accueil + une par fiche, User-Agent, pause entre les fiches (injectée à 0 dans les tests), filtrage par fenêtre.
- Erreurs : accueil en 500, réseau (message sans URL), aucun lien film, une fiche en 404, aucune séance au total.
- `test_main.py` : la source est dans le registre (si c'est simple avec la plomberie existante).

## Vérification à la main
- `uv run python -m affichette.main --dry-run --cinema filmotheque` : vrais appels au site, aucune écriture. Je te montre le rapport (séances, taux de correspondance TMDB).
- Toi : rejouer le seed sur le projet cloud (`npx supabase db push --remote --include-seed`) pour passer la salle en `source = 'filmotheque'`.

## Hors scope
- Libellés d'événement (`event-badge` de la grille : « Festival », « Ciné-club de la Crypte »).
- Correction des 10 min d'ouverture de séance.
- Les autres salles HTML (#26, #27, #28).
