# Journal des décisions

## 2026-11-22 - Lint front : oxlint plutôt qu'ESLint
- Contexte : le template Vite actuel (Vite 8) génère une config oxlint et non plus ESLint.
- Décision : garder oxlint, avec les plugins react, typescript et oxc, plus Prettier pour le format. `npm run lint` lance les deux, et `npm run typecheck` lance `tsc -b`.
- Alternatives écartées : remettre ESLint (plus lent, config à maintenir, rien de nécessaire en plus).

## 2026-11-22 - Vitest lancé via un script wrapper (Windows)
- Contexte : quand le dossier est ouvert en `c:\…` (lettre de lecteur en minuscule, ce que fait VS Code), Vitest 5.1 charge deux copies de son runner. Toutes les suites échouent alors avec `Cannot read properties of undefined (reading 'config')`. Un projet vide lancé depuis `C:\` passe.
- Décision : `npm test` lance `web/scripts/vitest.mjs`, qui relance Vitest depuis le même chemin avec la lettre de lecteur en majuscule. Sans effet sur Linux (CI).
- Alternatives écartées : `root` ou `process.chdir` dans `vite.config.ts` (testé, sans effet, car le cwd est lu avant la config).

## 2026-11-22 - Nom : « L'Affichette de Paname »
- Contexte : « movieinparis » est le nom d'un compte Instagram existant, que je ne gère pas, et le reprendre prêterait à confusion.
- Décision : le site s'appelle « L'Affichette de Paname ». Le repo s'appelle `affichette-de-paname`.
- Alternatives écartées : « movieinparis » (confusion avec le compte Insta).

## 2026-11-22 - Design repris de Recsys_movie (direction « fanzine »)
- Contexte : il faut une direction visuelle, et Recsys_movie en a déjà une, validée.
- Décision : reprendre les jetons (couleurs, typo Courier Prime + Caveat), le ton et les principes de la direction « C · Fanzine », adaptés aux séances. Voir `docs/design.md`.
- Alternatives écartées : une nouvelle direction (plus de temps de design) ; s'inspirer du compte Insta (risque de copier une identité qui n'est pas la mienne).

## 2026-11-22 - Correspondance TMDB : affichage brut + overrides CSV
- Contexte : des titres de séance ne trouveront pas de film TMDB (cycles, courts, titres ambigus).
- Décision : la séance est affichée avec le titre de la salle, sans fiche. Un `pipeline/manual_overrides.csv` versionné corrige à la main, et un rapport des non-correspondances est produit à chaque import.
- Alternatives écartées : une page admin (trop d'UI et de droits pour la V1) ; masquer ces séances (perte d'information).

## 2026-11-22 - Alertes : dès détection, re-alerte après 30 jours d'absence
- Contexte : l'alerte doit être utile sans spammer.
- Décision : l'email part dès qu'un import trouve une séance d'un favori, groupé par utilisateur. Une nouvelle alerte ne part que si le film revient après 30 jours sans séance.
- Alternatives écartées : un récap hebdo (rate les films ajoutés en cours de semaine) ; une alerte par nouvelle salle (trop d'emails) ; un favori consommé après l'alerte.

## 2026-11-22 - Toute la programmation importée, filtre patrimoine par défaut (plus de 20 ans)
- Contexte : plusieurs salles passent aussi des films récents.
- Décision : on importe tout. Le filtre « patrimoine » (année TMDB ≤ année courante − 20) est actif par défaut, et les séances sans année restent visibles.
- Alternatives écartées : patrimoine uniquement à l'import (perte d'info, dilemme pour les films sans année) ; un seuil de 30 ans ; un curseur réglable.

## 2026-11-22 - Historique des séances conservé
- Contexte : la règle de re-alerte a besoin de savoir quand un film est passé pour la dernière fois, et la V3 pourra exploiter les données.
- Décision : les séances passées restent en base (faible volume). Les annulations sont marquées par `cancelled_at`.
- Alternatives écartées : purger après la date (il faudrait une table de dernière programmation par film).

## 2026-11-22 - Favoris = n'importe quel film TMDB
- Contexte : l'alerte apporte surtout quelque chose pour un film qu'on attend et qui n'est pas encore programmé.
- Décision : recherche TMDB intégrée au site, via une Edge Function Supabase pour que le jeton ne soit pas exposé.
- Alternatives écartées : favoris limités aux films programmés.

## 2026-11-22 - Auth par magic link
- Contexte : on envoie des emails, donc l'adresse doit être vérifiée, et je veux éviter de gérer des mots de passe.
- Décision : Supabase Auth en magic link uniquement.
- Alternatives écartées : email + mot de passe (réinitialisation, vérification) ; Google OAuth (configuration en plus, pas nécessaire en V1).

## 2026-11-22 - Stack : Supabase + React/Vite + job Python sur GitHub Actions
- Contexte : projet perso avec un budget d'hébergement minimal, mais il faut des comptes, des favoris et des emails, donc un site 100 % statique ne suffit pas. Le client TMDB existe déjà en Python (Recsys_movie).
- Décision :
  - front React + Vite + TS sur Cloudflare Pages ;
  - Supabase (Postgres, PostgREST, RLS, Auth) en free tier ;
  - job d'import Python 3.12 + uv, en cron sur GitHub Actions (repo public, minutes illimitées) ;
  - emails via Resend (free tier).
  - Coût : 0 €.
- Alternatives écartées : FastAPI + Postgres sur un VPS (~4 €/mois, serveur et auth à maintenir) ; séances en JSON statique + Supabase pour les comptes seulement (deux sources de vérité).
