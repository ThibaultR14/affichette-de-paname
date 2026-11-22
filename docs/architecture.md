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
- `sources/` : un adaptateur par source. Chacun expose `fetch(cinema, start, end) -> list[RawScreening]`. `RawScreening` contient `source_key, cinema_id, raw_title, starts_at, version?, format?, booking_url?, runtime_hint?, year_hint?, director_hint?, tmdb_hint?, event_label?`.
  - `scare.py` : jeu ouvert SCARE (data.gouv.fr, API data-fair), plusieurs salles par appel. Premier adaptateur (#7).
  - Puis, dans #14 : `dulac.py` (Reflet Médicis, heures UTC sans « Z ») et un adaptateur HTML par site (Filmothèque, Espace Saint-Michel, Cinéma des Cinéastes, Club de l'Étoile). `webedia.py` (8 salles) n'est écrit qu'avec l'accord écrit des salles.
- `normalize.py` : fuseau Europe/Paris, conversion en UTC, normalisation VO/VOSTFR/VF et 35mm/70mm/4K/DCP.
- `tmdb.py` : client TMDB repris de Recsys_movie (`enrich_tmdb.py`) : jeton Bearer `TMDB_READ_TOKEN`, rate limiter, réessais sur 429, cache JSON réutilisé moins de 30 jours et purgé au-delà de 6 mois (CGU TMDB). Ne journalise jamais d'URL.
- `matching.py` : titre → `tmdb_id`. Ordre de priorité : `manual_overrides.csv`, puis le `tmdb_hint` de la source (SCARE), puis la table `title_matches`, puis la recherche TMDB (`language=fr-FR`, avec l'année si on l'a), puis le score (titre normalisé, année ±1, réalisateur si fourni). On ne fait rien sous le seuil de confiance (`tmdb_id = null`). La normalisation des titres reprend `titles.py` de Recsys.
- `upsert.py` : upsert par `source_key`. Pour une salle dont l'import a réussi, une séance future absente du nouvel import reçoit `cancelled_at`. Une salle en échec n'est pas touchée.
- `alerts.py` : favoris nouvellement programmés, puis un email groupé par utilisateur.
- `report.py` : entrée `import_runs`, résumé dans le log Actions, issue GitHub si une salle échoue.
- `main.py` : orchestration, avec `--dry-run` et `--cinema <id>`.

### `supabase/` - schéma
- `migrations/*.sql` : tables, index, règles RLS. Appliquées avec la CLI Supabase (`supabase db push`).
- `functions/tmdb-search/` : Edge Function (Deno) qui relaie la recherche TMDB pour l'ajout de favoris.
- `seed.sql` : les 19 salles (adresse, UGC, source).

### `web/` - front
- React + Vite + TS, routing côté client (`/`, `/film/:tmdbId`, `/favoris`, `/connexion`).
- `@supabase/supabase-js` pour les lectures, l'auth et les favoris.
- État des filtres dans l'URL (`?jour=2026-11-24&salles=champo,louxor&ugc=1&patrimoine=0`), pour qu'on puisse partager un lien.
- Affiches servies par le CDN TMDB (`image.tmdb.org`).
- Styles : jetons clair/sombre dans `src/styles/tokens.css` (`data-theme` sur `<html>`), un `.css` par composant dans `src/components/`. Page `/styleguide` (`src/pages/Styleguide.tsx`), choisie par `src/Root.tsx` en attendant le routeur.

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
