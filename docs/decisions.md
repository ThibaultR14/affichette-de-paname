# Journal des décisions

## 2026-11-22 - Design system : thème du système, CSS sans Tailwind
- Contexte : issue #2, TODO de `docs/design.md`.
- Décision :
  - thème par défaut = préférence du système, clair à défaut, avec une bascule mémorisée (`affichette-theme`) ;
  - pastilles sans couleur (bordure encre), `ugc` à côté du nom de la salle ;
  - carte film en ligne compacte sous 640 px, carte photo au-delà ;
  - CSS classique : jetons en propriétés CSS (`web/src/styles/tokens.css`) et un `.css` par composant ;
  - polices auto-hébergées via `@fontsource`, vérifiées par `fonts.test.ts` ; contraste AA vérifié par `contrast.test.ts` ;
  - `/styleguide` servi aussi en production, chargé à la demande, sans routeur pour l'instant.
- Alternatives écartées : clair forcé (éblouit le soir) ; sombre par défaut comme Recsys (usage en extérieur) ; Tailwind comme Recsys (une dépendance et une config de plus pour une dizaine de composants) ; carte photo sur mobile (trop haute).

## 2026-11-22 - Sources des séances : SCARE d'abord, une source par salle ensuite
- Contexte : spike #1 (`docs/spikes/01-sources.md`). Aucune source unique ne couvre les salles, et cip-paris.fr ne publie pas de séances.
- Décision :
  - Source principale : le jeu ouvert SCARE « Programmation des cinémas indépendants » (data.gouv.fr, Licence Ouverte 2.0). Il couvre complètement Champo, Saint-André-des-Arts et Grand Action, et les événements de Louxor, Sept Parnassiens et Épée de Bois. C'est le premier adaptateur (#7).
  - Ensuite, une source par salle : API Dulac (Reflet Médicis), HTML des sites de Filmothèque, Espace Saint-Michel, Cinéma des Cinéastes et Club de l'Étoile. Les CGU sont à confirmer dans #14.
  - Le `tmdb_id` fourni par SCARE sert d'indice de correspondance, juste après `manual_overrides.csv` (accord de 107 sur 107 avec notre recherche).
- Alternatives écartées : cip-paris.fr (pas de séances) ; billetterie Cotecine (robots.txt `Disallow: /*`).

## 2026-11-22 - API Webedia exclue sans accord écrit des salles
- Contexte : 8 salles (Louxor, Brady, Mac-Mahon, Épée de Bois, Saint-Germain-des-Prés, Nouvel Odéon, Publicis, Sept Parnassiens) exposent une API JSON complète sur leur domaine. Elle est fournie par Webedia et liée à Allociné (codes salle Allociné, CDN acsta.net, réservation via tickets.allocine.fr pour le Nouvel Odéon). La CGU type interdit d'exploiter le site sans autorisation expresse.
- Décision : on ne la collecte pas tant qu'on n'a pas l'accord écrit de la salle. Un email de demande est préparé (annexe du spike) et propose aussi de rejoindre le jeu SCARE. L'adaptateur Webedia est une sous-issue bloquée de #14.
- Alternatives écartées : l'utiliser en « usage prudent » (zone grise vis-à-vis des CGU et de la règle « pas d'Allociné ») ; l'exclure définitivement (on perdrait la meilleure source si les salles acceptent).

## 2026-11-22 - MK2 Cultissime retiré, salles sans source documentées
- Contexte : « MK2 Cultissime » est un label de ciné-club mk2 joué dans plusieurs salles mk2, pas une salle, et les CGU mk2 interdisent la réutilisation. Christine Cinéma Club, Écoles Cinéma Club et L'Archipel n'ont pas d'autre source que la billetterie Cotecine, bloquée par robots.txt.
- Décision : MK2 Cultissime sort de la liste (19 salles). Christine, Écoles et Archipel restent dans la liste, marquées sans source, et sont incluses dans la demande d'accord.
- Alternatives écartées : les garder sans séances et sans explication.

## 2026-11-22 - Cron : 04 h UTC chaque jour, plus 13 h UTC le mercredi
- Contexte : SCARE est mis à jour vers 02 h 15 à Paris. Les salles en HTML publient leur nouvelle semaine le mercredi.
- Décision : `0 4 * * *` et `0 13 * * 3` (UTC) pour #13.
- Alternatives écartées : un horaire fixe à l'heure de Paris (le cron GitHub ne connaît que l'UTC, et une heure d'écart l'été ne change rien ici).

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
