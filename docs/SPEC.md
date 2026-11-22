# SPEC - L'Affichette de Paname

> Version 0.2 - 2026-11-22. Issue de l'interview de démarrage, validée. Nom du repo : `affichette-de-paname`.

## Objectif

Centraliser les séances des cinémas indépendants parisiens sur **7 jours glissants**, pour qu'un cinéphile sache ce qui passe aujourd'hui comme dans 5 jours. Le site vise d'abord les **films de patrimoine** en salle. Aujourd'hui, la seule source pratique est le compte Instagram @movieinparis, alimenté à la main au jour le jour, qui ne permet pas de voir au-delà du lendemain.

Le site doit aussi prévenir l'utilisateur quand un film qu'il attend est programmé.

## Utilisateurs

- **Visiteur anonyme** : consulte les séances, filtre, ouvre les fiches film. C'est l'usage principal, sur mobile (dans la rue, le métro).
- **Utilisateur inscrit** (magic link) : en plus, tient une liste de films favoris, qui peuvent être n'importe quel film TMDB, programmé ou non, et reçoit un email quand l'un d'eux passe.
- **Admin** (moi) : surveille les imports, corrige les correspondances titre → TMDB via un fichier CSV versionné, et vérifie les infos des salles (UGC, adresses).

## Fonctionnalités MVP (V1)

### Séances
- Séances des 7 prochains jours (aujourd'hui inclus) pour les 20 salles : Filmothèque du Quartier Latin, Le Champo, Christine Cinéma Club, Écoles Cinéma Club, Le Brady, Sept Parnassiens, Saint-André-des-Arts, Publicis Cinémas, Le Louxor, Cinéma des Cinéastes, Le Saint-Germain-des-Prés, Club de l'Étoile, MK2 Cultissime, L'Archipel, Le Grand Action, Reflet Médicis, Nouvel Odéon, Épée de Bois, Mac-Mahon, Espace Saint-Michel.
- **Vue principale par film, pour un jour choisi** : bandeau de 7 jours en haut, puis une carte par film (affiche, titre, réalisateur, année, durée) avec la liste de ses séances (salle, heure de début et heure de fin, VO/VF, format).
- Pour chaque séance, si la source les fournit : **VO / VF**, **format** (35mm, 70mm, 4K…), **lien de réservation** (à défaut, lien vers la page programme de la salle).
- **Heure de fin** = début + durée TMDB, affichée seulement si la durée est connue.
- **Couverture par salle** : chaque salle affiche « programme connu jusqu'au <date> » et « mis à jour il y a <durée> ». Quand l'import d'une salle échoue, on garde ses dernières séances connues.

### Fiche film
- Données TMDB : affiche, titre français et titre original, synopsis, réalisateur(s), année, durée.
- Toutes les séances du film sur les 7 jours, toutes salles confondues.
- Bouton favori (si connecté).

### Filtres (combinables, état dans l'URL)
- Date (un des 7 jours).
- Salle (multi-sélection).
- **Accepte la carte UGC Illimité**. Hypothèse à vérifier : toutes les salles sauf Filmothèque du Quartier Latin, Le Saint-Germain-des-Prés, Club de l'Étoile, MK2 Cultissime et L'Archipel.
- **Patrimoine** (actif par défaut) : films sortis il y a plus de 20 ans, seuil glissant calculé à partir de l'année TMDB. Les séances sans correspondance TMDB, donc sans année connue, restent visibles avec le filtre actif.
- On importe toute la programmation, films récents compris, et on peut désactiver le filtre pour tout voir.

### Comptes, favoris, alertes
- Connexion par **magic link email** (Supabase Auth). Pas de mot de passe.
- Favoris : recherche TMDB intégrée, pour ajouter n'importe quel film même s'il n'est pas programmé, et bouton cœur sur les cartes et fiches.
- **Alerte email dès détection** : quand un import trouve une séance, dans les 7 jours, d'un film en favori, l'utilisateur reçoit un email avec les séances concernées.
- **Une seule alerte par période de programmation** : après une alerte, rien ne repart tant que le film reste programmé. Une nouvelle alerte part s'il revient après **30 jours sans aucune séance**.
- Plusieurs favoris détectés dans le même import sont regroupés en **un seul email**.
- Lien de désinscription en un clic dans chaque email. Suppression du compte possible (RGPD).

### Import (job planifié)
- Job Python lancé par GitHub Actions (cron quotidien, plus un déclenchement manuel).
- Pour chaque salle : récupération depuis la source retenue par le spike (#1), normalisation, puis upsert en base. Le job est idempotent : on peut le relancer sans créer de doublons.
- Correspondance titre → TMDB avec cache, plus un `manual_overrides.csv` versionné qui a toujours priorité.
- Une séance sans correspondance TMDB s'affiche quand même, avec le titre donné par la salle et sans fiche.
- Rapport à chaque import (séances par salle, non-correspondances, erreurs). Si une salle est en échec, le job ouvre une issue GitHub ou m'envoie un email.
- Envoi des alertes favoris à la fin de l'import.

## Hors scope

- **V2** : temps de trajet (à pied, métro, vélo) depuis la position de l'utilisateur jusqu'à la salle.
- **V3** : recommandations personnalisées (import Letterboxd).
- Scraping d'Allociné ou de tout agrégateur dont les CGU l'interdisent.
- Réservation ou paiement dans le site.
- Salles hors des 20 listées, hors Paris intra-muros.
- Page admin web : les corrections passent par le CSV et le repo.
- Récap hebdomadaire par email, préférences d'alerte fines.
- Application mobile native, PWA hors ligne, notifications push.
- Multilingue : le site est en français uniquement.
- Page publique d'historique des séances : l'historique est stocké, mais pas exposé.

## Stack

| Brique | Choix | Coût |
|---|---|---|
| Front | React + Vite + TypeScript, SPA, mobile-first | - |
| Hébergement front | Cloudflare Pages | 0 € |
| Base de données + API | Supabase (Postgres, PostgREST, règles RLS) | 0 € (free tier) |
| Auth | Supabase Auth, magic link | 0 € |
| Job d'import | Python 3.12 + uv, réutilise le client TMDB de Recsys_movie (cache, `.env`) | - |
| Planification | GitHub Actions cron (repo public, minutes illimitées) | 0 € |
| Emails | Resend (free tier : 3 000/mois, 100/jour) | 0 € |
| Tests / lint | Vitest + Testing Library + oxlint + Prettier (front) ; pytest + ruff (job) | - |
| Design | Reprise du design system de Recsys_movie (`docs/design-system.md`, maquette « fanzine ») | - |

Le front lit les séances directement dans Supabase en lecture publique via RLS, et lit et écrit les favoris de l'utilisateur connecté. Le job écrit avec la clé `service_role`, qui n'existe que dans les secrets GitHub Actions. L'import quotidien écrit en base tous les jours, ce qui empêche le free tier de se mettre en pause.

## Modèle de données

```
cinemas
  id               text PK          -- slug : "champo", "louxor"…
  name, address, arrondissement
  lat, lng         nullable         -- prévu pour la V2
  website_url, booking_base_url
  accepts_ugc      boolean
  ugc_verified_at  date nullable
  source           text             -- source d'import retenue (cf. spike #1)
  source_ref       text             -- identifiant de la salle dans cette source
  last_import_at, last_import_ok, coverage_until (date)

films                                -- uniquement les films TMDB rencontrés (séances ou favoris)
  tmdb_id          int PK
  title, original_title, year, runtime_min
  directors        text[]
  overview, poster_path
  tmdb_fetched_at  timestamptz      -- refresh < 30 j, purge > 6 mois (CGU TMDB)

screenings                           -- historique conservé
  id               bigint PK
  cinema_id        FK cinemas
  tmdb_id          FK films nullable -- null = pas de correspondance
  raw_title        text              -- titre tel que donné par la salle
  starts_at        timestamptz       -- Europe/Paris
  version          text nullable     -- VO | VOSTFR | VF
  format           text nullable     -- 35mm | 70mm | 4K | DCP…
  booking_url      text nullable
  source_key       text UNIQUE       -- clé stable de la séance dans la source → upsert idempotent
  first_seen_at, last_seen_at
  cancelled_at     nullable          -- séance future absente d'un import réussi

title_matches                        -- cache de correspondance titre → TMDB
  normalized_title, cinema_id nullable, year_hint nullable
  tmdb_id nullable, method (exact|fuzzy|override|none), score, matched_at

profiles
  user_id          uuid PK FK auth.users
  alerts_enabled   boolean default true
  unsubscribe_token uuid

favorites
  user_id, tmdb_id  PK composite
  created_at
  last_alerted_at  nullable

import_runs
  id, started_at, finished_at, cinema_id, status, n_screenings, n_unmatched, error
```

RLS : `cinemas`, `films` et `screenings` sont lisibles par tous. `favorites` et `profiles` ne sont lisibles et modifiables que par leur propriétaire. Seul le job (`service_role`) écrit les autres tables.

## Questions ouvertes

1. **Source des séances** : c'est le spike de l'issue #1, à traiter avant tout le reste. Pistes, dans l'ordre :
   1. data.gouv.fr « Programmation des cinémas indépendants » (CSV quotidien, Licence Ouverte 2.0) : quelles salles parisiennes de la liste, sur combien de jours, avec VO/VF et format ?
   2. cip-paris.fr (une fiche par salle) : séances récupérables ? Chargées en JS (API interne) ? Conditions d'utilisation ?
   3. Sites des salles (le réseau Action a peut-être un site commun ; vérifier aussi Écran Noir / Dulac / Cinémas Indépendants Parisiens).
   - Livrable attendu : un tableau salle × source × jours couverts × VO/VF × format × lien de réservation × CGU, plus une recommandation. Une salle peut avoir sa propre source.
   - Le spike teste aussi la **correspondance des titres** (souvent en français, vieux films) avec TMDB : taux de correspondance mesuré sur un échantillon réel, et stratégie (recherche `language=fr-FR`, année, réalisateur si fourni, fuzzy, overrides).
2. **Liste UGC Illimité** à vérifier sur le site UGC, en notant la date de vérification.
3. **Nom de domaine** : le nom est fixé (« L'Affichette de Paname »), le domaine reste à choisir. En attendant, le site est servi sur `*.pages.dev`.
4. **Canal d'alerte admin** en cas d'échec d'import : issue GitHub automatique ou email Resend.
5. **Fuseau et heure du cron** : à fixer selon l'heure de publication des sources (par ex. 6 h Europe/Paris, plus éventuellement un second passage le mercredi après-midi, jour des nouveaux programmes).
6. **Quotas Resend** (100 emails/jour) : suffisants pour un projet perso. À surveiller si le site est partagé.
