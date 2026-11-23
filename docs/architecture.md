# Architecture - L'Affichette de Paname

> Le comment. Le quoi est dans `SPEC.md`. Les sources des séances ont été choisies par le spike #1 (`docs/spikes/01-sources.md`). La partie « adaptateurs » ci-dessous est un contrat, implémenté à partir de #7.

## Vue d'ensemble

```
┌──────────────── GitHub Actions (cron quotidien + manuel) ────────────────┐
│  pipeline/ (Python 3.12, uv)                                              │
│                                                                           │
│  sources/<adaptateur>.py ──► normalize ──► match TMDB ──► upsert Supabase │
│   (1 adaptateur par source,   (heure     (cache + overrides  (service_role)│
│    cf. spike #1)               Paris,     CSV, client TMDB                 │
│                                VO/VF,     repris de Recsys)                │
│                                format)                                     │
│                                              │                            │
│                                              ▼                            │
│                          alerts.py : favoris nouvellement programmés      │
│                                 ──► Resend (1 email groupé / utilisateur) │
│                          report.py : rapport d'import, issue si échec     │
└──────────────────────────────────────┬────────────────────────────────────┘
                                       │ écrit
                              ┌────────▼────────┐
                              │    Supabase     │  Postgres + PostgREST + Auth
                              │  (free tier)    │  RLS : séances en lecture publique,
                              └────────▲────────┘  favoris privés par utilisateur
                                       │ lit (clé anon) / écrit favoris (JWT user)
┌──────────────────────────────────────┴────────────────────────────────────┐
│  web/ (React + Vite + TS, SPA)  ── Cloudflare Pages                        │
│  vue par film/jour · filtres (URL) · fiche film · favoris · magic link     │
│  recherche TMDB pour ajouter un favori : via une Edge Function Supabase    │
│  (le jeton TMDB ne va jamais dans le navigateur)                           │
└────────────────────────────────────────────────────────────────────────────┘
```

## Composants

### `pipeline/` - job d'import (Python)
- `sources/` : un adaptateur par source. Chacun expose `fetch(cinema, start, end) -> list[RawScreening]` (séances avec `start <= starts_at < end`, heures avec fuseau) et lève `SourceError` quand la salle ne peut pas être importée. `RawScreening` contient `source_key, cinema_id, raw_title, starts_at, version?, format?, booking_url?, runtime_hint?, year_hint?, director_hint?, tmdb_hint?, event_label?`. La salle passée est un `Cinema` (`id, name, source, source_ref, website_url`), lu dans la table `cinemas`.
  - `scare.py` : jeu ouvert SCARE (data.gouv.fr, API data-fair). Un seul téléchargement paginé des lignes `cinecp:75*` par run, partagé par les 6 salles `source = 'scare'` (un échec est aussi mémorisé : pas un appel par salle). Ligne → salle par `cinenom == source_ref`. `source_key = scare:<cinema_id>:<showid>`. Version : `VOST` ou `ST` dans `filmaudio` → VOSTFR, `VERSION_ORIGINAL`/`VO` → VO, `VF`/`VERSION_LOCAL`/`VERSION_ORIGINAL_LOCAL` (film français) → VF. Format cherché dans le titre puis dans `description`. `filmduration` est en secondes. `showurl` absent → `booking_url = null` (le front prendra `website_url`). Lignes sans `showstart` ignorées. 0 ligne parisienne = panne de la source, et une salle dont le `cinenom` n'apparaît plus du tout dans le jeu est en échec (renommage ou retrait : sinon toutes ses séances seraient annulées). Une salle présente sans séance dans la fenêtre reste un import réussi. Fixtures : extrait réel dans `tests/fixtures/scare/`.
  - Puis, dans #14 : `dulac.py` (Reflet Médicis, heures UTC sans « Z ») et un adaptateur HTML par site (Filmothèque, Espace Saint-Michel, Cinéma des Cinéastes, Club de l'Étoile). `webedia.py` (8 salles) n'est écrit qu'avec l'accord écrit des salles.
- `normalize.py` : fuseau Europe/Paris, conversion en UTC, normalisation VO/VOSTFR/VF et 35mm/70mm/4K/DCP.
- `tmdb.py` : client TMDB repris de Recsys_movie (`enrich_tmdb.py`) : jeton Bearer `TMDB_READ_TOKEN`, rate limiter, réessais sur 429, 5xx et erreurs réseau, `language=fr-FR`, cache JSON réutilisé moins de 30 jours et purgé au-delà de 6 mois (CGU TMDB). Ne journalise jamais d'URL. Cache dans `pipeline/data/cache/tmdb/<type>/<clé>.json` (ignoré par git), 404 compris.
- `db.py` : accès Supabase par PostgREST (`requests` seul, sans le paquet `supabase`) : `Db.from_env()` avec `select(table, params)`, `upsert(table, rows, on_conflict)` (seules les colonnes envoyées sont mises à jour), `insert(table, rows)` et `update(table, values, filters)` (PATCH, filtre obligatoire), `in_list(values)` pour un filtre `in.(...)` entre guillemets, avec la clé `service_role` en en-tête, jamais journalisée.
- `films.py` : `upsert_film(tmdb_id, tmdb, db)` remplit `films` (titre fr, à défaut original ; `tmdb_fetched_at` = date de l'appel TMDB, pas de l'écriture). Essai à la main : `uv run python -m affichette.films <id>… --dry-run`.
- `matching.py` : titre → `tmdb_id` (`Matcher.match(MatchQuery)`). Ordre : `manual_overrides.csv` (titre normalisé + salle, salle vide = toutes, `tmdb_id` vide = « pas un film »), puis le `tmdb_hint` de la source (SCARE), puis le cache `title_matches` (clé titre normalisé + salle + année ; trouvé réutilisé 30 jours, non trouvé 7 jours), puis la recherche TMDB `fr-FR` avec les règles du spike : réalisateur sur les 5 premiers résultats (variantes d'orthographe tolérées), titre seul sur un premier résultat sans homonyme, filmographie du réalisateur en repli, année ±1 si la source la donne. Sous le seuil : `tmdb_id = null`. `title_matches.method` ∈ `override, source, director, title, none` ; seuls les résultats de recherche y sont écrits, avec la raison d'un échec (`DbTitleMatchStore` : lecture par salle paginée à 1 000 lignes, `max_rows` de Supabase ; un upsert en fin de run). `MatchReport.summary()` : séances par méthode, non-correspondances (événements à part), correspondances par titre seul à relire. Essai : `uv run python -m affichette.matching "EVA" --director "LOSEY Joseph"`. Mesure sur l'échantillon du spike : `uv run python -m scripts.eval_matching [--sweep]`.
- `tmdb.py` sert aussi la recherche : `search_movie`, `search_person`, `person_directing` (réponses réduites, même cache). Les réalisateurs d'un candidat viennent de `movie(id)`, déjà utilisé pour `films`.
- `films.py` → `ensure_films(ids, tmdb, db, now)` : avant d'écrire les séances, chaque `tmdb_id` absent de `films` ou rafraîchi il y a plus de 30 jours est rechargé. Un id inconnu de TMDB (404) et absent de `films` est retiré de la séance (`tmdb_id = null`), sinon la clé étrangère casserait l'upsert.
- `upsert.py` : `sync_cinema` upserte les séances de la fenêtre sur `source_key` (`last_seen_at = now`, `cancelled_at = null` pour une séance qui revient, `first_seen_at` jamais envoyé donc conservé). Les séances non annulées de la salle dans `[max(now, début), fin[` absentes de l'import reçoivent `cancelled_at` (les séances passées et au-delà de la fenêtre ne sont pas touchées). Puis `cinemas` : `last_import_at`, `last_success_at`, `last_import_ok = true`, `coverage_until` = date Paris de la dernière séance importée (inchangée si la salle n'a aucune séance). `mark_failed` n'écrit que `last_import_at` et `last_import_ok = false` (`last_success_at` et `coverage_until` gardés). Les écritures ne sont pas transactionnelles (PostgREST, une requête par étape) : si une annulation ou la mise à jour de `cinemas` échoue après l'upsert, l'erreur commence par « écriture partielle ». Chaque étape étant idempotente, l'import suivant termine le travail.
- `alerts.py` : favoris nouvellement programmés, puis un email groupé par utilisateur.
- `main.py` : orchestration (`uv run python -m affichette.main [--dry-run] [--cinema <id>]…`). Fenêtre `[aujourd'hui 00:00 Paris, +7 jours[`. Pour chaque salle dont la source est connue : `fetch` → `Matcher` (#6) → `ensure_films` → `sync_cinema`, puis une ligne `import_runs` (`ok` ou `error` avec un message sans URL). Toute erreur d'une salle est isolée (`mark_failed`), les autres continuent. `title_matches` est écrit en un upsert à la fin. `--dry-run` passe par `DryRunDb` : lectures réelles, écritures seulement comptées et affichées. Sortie : rapport par salle + `MatchReport.summary()`, code 0 si tout va bien, 1 si une salle a échoué, 2 pour une option ou une configuration invalide.
- `report.py` (#13) : résumé dans le log Actions, issue GitHub si une salle échoue.

### `supabase/` - schéma
- `migrations/*.sql` : tables, index, règles RLS. Appliquées au projet cloud avec `npx supabase db push --remote` (`--dry-run` pour voir la liste d'abord). Sans `--remote`, la CLI vise la stack locale.
- `functions/tmdb-search/` : Edge Function (Deno) qui relaie la recherche TMDB pour l'ajout de favoris.
- `seed.sql` : les 19 salles (adresse, UGC, source), idempotent (`on conflict do update`). `source_ref` = `cinenom` exact pour SCARE, id de nœud pour Dulac.
- `tests/*.test.sql` : tests pgTAP (seed, RLS par rôle `anon` / `authenticated`), lancés par `supabase test db` en local et dans le job CI `supabase`.
- `templates/` : mails d'auth en français (`magic_link.html`, `confirmation.html`), branchés dans `config.toml` pour la stack locale (Mailpit sur `http://127.0.0.1:54324`) et collés dans le dashboard pour le projet cloud.
- `config.toml` : stack locale (`npx supabase start`, Docker). Le projet cloud est lié par `npx supabase link`. `db push --remote` applique les migrations, `db push --remote --include-seed` le seed. En local, `npx supabase db reset` rejoue migrations et seed.

### `web/` - front
- React + Vite + TS, routing côté client (`/`, `/film/:tmdbId`, `/favoris`, `/connexion`).
- `@supabase/supabase-js` pour les lectures, l'auth et les favoris.
- État des filtres dans l'URL (`?jour=2026-11-24&salles=champo,louxor&ugc=1&patrimoine=0`), pour qu'on puisse partager un lien.
- Affiches servies par le CDN TMDB (`image.tmdb.org`).
- Client Supabase dans `src/lib/supabase.ts` (`null` si les variables `VITE_*` manquent, la page affiche alors une erreur au lieu de planter). Lectures dans `src/lib/<table>.ts` (`fetchCinemas`), `fetchDayScreenings`).
- Vue du jour (`components/DayScreenings.tsx`) : `fetchDayScreenings(day)` lit en une requête `screenings` + `cinemas` + `films` (jointures PostgREST) sur `parisDayRange(day)` (`[00:00, 24:00[` Paris en UTC, jours de 23 h et 25 h compris), séances non annulées, à partir de maintenant pour aujourd'hui. Au-delà de 1 000 lignes (`max_rows`), erreur plutôt qu'un jour tronqué. `groupByFilm` fait une carte par `tmdb_id`, à défaut par titre brut (casse et espaces ignorés), salles par nom, séances par heure, cartes par titre. Lien d'une heure : `booking_url`, sinon `website_url` de la salle, sinon pas de lien. Affiches en `w342`.
- Jour choisi (`src/lib/dayParam.ts`, `useSelectedDay`) : `?jour=AAAA-MM-JJ` lu dans `window.location`. Absent, mal formé ou hors des 7 jours → aujourd'hui, et un `?jour=` invalide est retiré de l'URL. Un clic dans le bandeau (`DayStrip`) écrit `?jour=` par `history.replaceState` en gardant les autres paramètres. `today` avance à minuit Paris (minuteur) et au retour sur l'onglet (`visibilitychange`). Le bandeau fait défiler horizontalement le jour choisi dans sa zone visible, sans bouger la page.
- Filtres (`src/lib/filters.ts`, `useFilters` ; `components/FilterPanel.tsx`) : `?salles=a,b&ugc=1&patrimoine=0`, seules les valeurs différentes du défaut écrites (patrimoine actif par défaut), `replaceState` en gardant `jour`. `filterFilms` filtre les cartes du jour déjà chargées : salles et UGC retirent les salles qui ne passent pas puis les cartes vides, patrimoine garde `year <= année Paris de today − 20` et les films sans année. `App` charge les salles une fois pour le panneau et retire de l'URL les ids inconnus. Le panneau « affiner » se déplie sous le bandeau ; les filtres actifs sont des puces « × » avec « tout effacer » (qui coupe aussi patrimoine). `src/lib/url.ts` : `replaceSearch` partagé par les deux hooks.
- Routage (`src/lib/router.ts`, sans dépendance) : `parseRoute(pathname)` → accueil, `/styleguide`, `/film/<id>` (entier positif ≤ 2^31−1, slash final toléré) ou 404. `navigate` fait `pushState` (la fiche se quitte avec « retour »), `usePathname` suit `navigate` et `popstate`. `Link` est un vrai `<a href>` dont le clic simple navigue sur place (ctrl/cmd-clic : nouvel onglet). `Root` choisit la page ; styleguide et fiche sont chargés à la demande. Tout chemin inconnu affiche `pages/NotFound.tsx` (la réponse HTTP reste 200 : Pages sert `index.html`).
- Fiche film (`pages/FilmPage.tsx`, `src/lib/films.ts`) : `fetchFilm(id)` lit `films` (`maybeSingle`, `null` → 404 « film introuvable ») et `fetchFilmScreenings(id)` les séances non annulées du film de maintenant à la fin des 7 jours (même garde de 1 000 lignes). `groupByDay` regroupe par jour Paris puis par salle (`groupByCinema`, partagé avec `groupByFilm`). Pas de filtres sur la fiche. Le titre d'une carte trouvée sur TMDB mène à sa fiche ; « ← toutes les séances » fait `history.back()` si on vient du site (jour et filtres retrouvés), sinon mène à `/`. Affiche en `w500`. `components/ShowtimeList.tsx` : liste « salle + heures + pastilles » commune à la carte et à la fiche ; `lib/filmMeta.ts` : ligne « réalisateur, année · durée ».
- Couverture par salle (`lib/coverage.ts`, `components/CoverageLine.tsx`) : `fetchCinemas` lit aussi `coverage_until`, `last_success_at`, `last_import_ok`. `coverageStatus` donne la ligne « programme connu jusqu'au ven. 27 · mis à jour il y a 3 h » (« 16 nov. » au-delà de 6 jours, « il y a » depuis le dernier succès) et `failed` si le dernier import a échoué (annotation Caveat). Jamais importée : « pas encore de programme pour cette salle ». Affichée sous chaque salle de `CinemaList`, horloge figée au montage.
- Connexion (`src/lib/auth.ts`, `pages/LoginPage.tsx`, `components/AccountBar.tsx`) : magic link en flux implicite. `sendMagicLink(email)` appelle `signInWithOtp` avec `emailRedirectTo = <origin>/connexion` (compte créé au premier login, profil créé par le trigger `on_auth_user_created`). `useSession()` suit `onAuthStateChange` (`undefined` pendant la lecture du stockage, `null` déconnecté) ; la session est gardée et rafraîchie par supabase-js dans le `localStorage`. `/connexion` : formulaire → « regarde tes mails », erreurs (adresse, 429, lien expiré lu dans le hash par `readLinkError` puis retiré de l'URL), ou état connecté avec « se déconnecter » (`scope: 'local'`). `AccountBar` (rendu par `Root` sur toutes les pages sauf `/connexion`) : « connexion » ou l'email et « se déconnecter ». Dev sur le port 5180 (`vite.config.ts`), attendu par les redirections de `supabase/config.toml`.
- Styles : jetons clair/sombre dans `src/styles/tokens.css` (`data-theme` sur `<html>`), un `.css` par composant dans `src/components/`. Page `/styleguide` (`src/pages/Styleguide.tsx`).

## Déploiement du front

Cloudflare Pages, par l'intégration Git (pas de GitHub Action) : chaque push sur `main` part en production, chaque PR a sa preview (lien commenté sur la PR). Site servi sur `*.pages.dev` en attendant un domaine.

| Réglage Pages | Valeur |
|---|---|
| Production branch | `main` |
| Root directory | `web` |
| Build command | `npm run build` |
| Output directory | `dist` |
| Variables (Production et Preview) | `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` |

- Node : version lue dans `web/.nvmrc` (24, comme la CI).
- Routage SPA : pas de `404.html`, donc Pages renvoie `index.html` pour tout chemin inconnu (`/styleguide`, `/film/:id`). Pas de `_redirects`.
- Les variables `VITE_*` sont incluses dans le bundle au build : après les avoir changées, il faut relancer un déploiement.

## Flux de données

1. **Import (cron, par ex. 6 h Paris)** : pour chaque salle, `fetch` → `normalize` → `match` → `upsert` → `import_runs`. Les erreurs sont isolées par salle.
2. **Films** : chaque `tmdb_id` nouveau ou périmé (plus de 30 jours) est enrichi via `/movie/{id}?append_to_response=credits&language=fr-FR` puis stocké dans `films`.
3. **Alertes** : après l'upsert, voir la règle ci-dessous.
4. **Lecture** : le front interroge `screenings` (jointure `films`, `cinemas`) sur `[jour 00:00, jour+1 00:00[` Europe/Paris et regroupe par film côté client.

## Règle d'alerte

Pour chaque favori `(user, film)` dont l'utilisateur a `alerts_enabled` :
- on cherche les séances à venir du film dans les 7 jours (non annulées) ;
- on envoie si `last_alerted_at` est nul, **ou** si le film n'a eu **aucune séance** dans les 30 jours avant la plus proche de ces séances à venir (le film est absent depuis au moins 30 jours puis revient) ;
- après l'envoi, `last_alerted_at = now()`. L'envoi est groupé par utilisateur. Si l'email échoue, `last_alerted_at` reste inchangé et la tentative est refaite au prochain import.

## Schéma de BDD

Voir « Modèle de données » dans `SPEC.md`. Index prévus :
- `screenings (starts_at)`, `screenings (tmdb_id, starts_at)`, `screenings (cinema_id, starts_at)` ;
- `screenings.source_key` unique ;
- `favorites (tmdb_id)`.

## Secrets et environnements

| Secret | Où | Utilisé par |
|---|---|---|
| `TMDB_READ_TOKEN` | `.env` local, Actions secrets, secrets Edge Function | pipeline, tmdb-search |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | `.env` local, Actions secrets | pipeline uniquement |
| `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` | `web/.env.local`, Cloudflare Pages | front (publics par nature) |
| `RESEND_API_KEY` | `.env` local, Actions secrets | pipeline (alerts) |

Un seul projet Supabase en V1. Les tests du pipeline n'appellent pas le réseau : ils utilisent des fixtures enregistrées.
