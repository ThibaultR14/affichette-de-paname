# Plan #11 - Fiche film `/film/:tmdbId`

Issue : #11. Branche : `feat/11-fiche-film`, depuis `main`.

## Ce qui existe déjà

- `Root` choisit la page selon `window.location.pathname` (pas de routeur) : `/styleguide` en lazy, sinon `App`.
- `FilmCard` affiche les séances groupées par salle (heure de début → fin, pastilles, lien résa). `groupByFilm`, `fetchDayScreenings` (motif : client injectable, `null` → erreur).
- `films` contient déjà `original_title` et `overview`, lisibles par `anon` (RLS).
- `days.ts` : `parisDayRange`, `weekStarting`, `dayTitle`, `parisDate`.

## Comportement

- **Route** `/film/<entier positif>` (slash final toléré). Tout autre `/film/…` (`/film/abc`, `/film/0`) → 404.
- **Navigation** : mini-routeur maison (`lib/router.ts`), pas de dépendance. `navigate(path)` fait `pushState` (on veut pouvoir revenir), `usePathname()` relit sur `popstate`. Les liens restent de vrais `<a href>` (ouvrir dans un onglet, partager) ; le clic simple sans modificateur est intercepté.
- **Depuis l'accueil** : le titre d'une carte trouvée sur TMDB devient un lien vers sa fiche. Carte sans correspondance : pas de lien (pas de fiche, cf. SPEC).
- **Fiche** (lecture `films` par `tmdb_id`) :
  - affiche w500 scotchée (cadre pointillé si absente), titre, titre original seulement s'il diffère, « réalisateur, année · durée » (même ligne que la carte), synopsis (« (pas de synopsis en français sur tmdb) » en Caveat s'il manque) ;
  - lien retour « ← toutes les séances » : `history.back()` si on vient de l'accueil du site, sinon `/` ;
  - `document.title` = « <titre> · l'affichette de paname ».
- **Séances** : une requête `screenings` `tmdb_id = id`, non annulées, `[max(now, aujourd'hui 00:00 Paris), aujourd'hui + 7 jours 00:00 Paris[`, triées par heure. Regroupées par jour Paris puis par salle (salles par nom). Titre de section par jour : « aujourd'hui », « demain », « mercredi 25 ». Lien d'une heure comme sur l'accueil (`booking_url`, sinon `website_url`, sinon texte). Heure de fin avec la durée du film.
  - Aucune séance : « pas de séance dans les 7 prochains jours. » (le film peut être en base comme favori seulement).
  - Pas de filtres ici (patrimoine, salles, UGC) : la fiche montre tout.
- **404 propre** : id mal formé, ou film absent de `films` → page « 404 » : titre « film introuvable », annotation « (ce film n'est pas sur l'affichette, ou le lien est cassé) », lien « retour à l'accueil ». Aussi pour tout chemin inconnu (`/nimporte`), aujourd'hui servi par l'accueil.
- **Erreur réseau / client absent** : même message que l'accueil « (on n'arrive pas à joindre la base, réessaie plus tard) », pas un 404.
- Pages pas de vrai statut HTTP 404 (SPA sur Pages, pas de `404.html`) : on n'en a pas besoin pour l'instant.

## Étapes

1. **`lib/router.ts`** : `navigate(path)`, `usePathname()`, `parseRoute(pathname)` → `{ page: 'home' } | { page: 'styleguide' } | { page: 'film', tmdbId } | { page: 'not-found' }`, et un composant `Link` (clic intercepté sauf ctrl/meta/shift/alt, bouton du milieu, `target`).
2. **`Root.tsx`** : `usePathname()` + `parseRoute`, rend `App`, `Styleguide`, `FilmPage` (lazy) ou `NotFound`. `main.tsx` ne passe plus `pathname` (prop gardée en option pour les tests).
3. **`components/ShowtimeList.tsx`** : la liste « salle + heures + pastilles » extraite de `FilmCard`, réutilisée par la carte et la fiche (pas de changement visuel sur la carte).
4. **`lib/films.ts`** : `fetchFilm(tmdbId)` → `Film | null` (`maybeSingle`) ; `fetchFilmScreenings(tmdbId, { now, client })` sur la fenêtre de 7 jours (même garde 1 000 lignes) ; `groupByDay(rows, today)` (pure) → `{ day, cinemas: CinemaShowtimes[] }[]`. La conversion ligne → `Showtime` / `CinemaShowtimes` est partagée avec `groupByFilm` (petite fonction sortie de `screenings.ts`).
5. **`pages/FilmPage.tsx` (+ `.css`)** : `load` injectable ; états chargement / erreur / introuvable (→ `NotFound`) / fiche. Mobile : affiche 120 px à gauche du titre ; ≥ 640 px : affiche 260 px à gauche, texte et séances à droite. Synopsis limité à ~65 caractères de large.
6. **`pages/NotFound.tsx`** : page 404 réutilisée par la fiche et `Root`.
7. **`FilmCard`** : titre en `Link` vers `/film/<id>` quand `tmdbId` n'est pas nul (prop `href` optionnelle pour garder la carte statique sur `/styleguide`).
8. Docs : `architecture.md` (routeur maison, fiche, 404), `decisions.md` (routeur maison plutôt que react-router ; fiche sans filtres).

## Tests (écrits d'abord)

- `router.test.ts(x)` : `parseRoute` (`/`, `/film/123`, `/film/123/`, `/film/abc`, `/film/0`, `/film/12a`, `/styleguide`, inconnu) ; `navigate` fait `pushState` et `usePathname` suit, `popstate` relu ; `Link` : clic simple intercepté, ctrl+clic non.
- `films.test.ts` : requête (filtre `tmdb_id`, bornes de la fenêtre, `from = now` en cours de journée, `cancelled_at`, ordre), erreur Supabase, client `null`, garde 1 000 lignes ; `fetchFilm` → `null` si absent ; `groupByDay` : jours Paris (séance à 00:30 Paris rattachée au bon jour), salles par nom, repli du lien résa.
- `FilmPage.test.tsx` : fiche complète (affiche, titres, titre original masqué s'il est identique, synopsis, méta, séances par jour avec « 14:00 → 15:43 ») ; aucune séance ; film inconnu → 404 ; erreur → message base ; synopsis absent.
- `Root.test.tsx` : `/film/123` rend la fiche, `/film/abc` et `/nimporte` rendent la 404.
- `components.test.tsx` / `DayScreenings.test.tsx` : titre lien vers `/film/<id>` sur une carte trouvée, pas de lien sur une carte non trouvée ; clic → navigation sans rechargement.
- Vérif manuelle : `npm run dev` (port 5180), fiche d'un film programmé, d'un film sans séance, `/film/999999999`, captures 375 px et desktop, comparées à design.md.

## Fichiers touchés

- Nouveaux : `web/src/lib/router.ts`, `web/src/lib/router.test.tsx`, `web/src/lib/films.ts`, `web/src/lib/films.test.ts`, `web/src/components/ShowtimeList.tsx`, `web/src/pages/FilmPage.tsx`, `web/src/pages/FilmPage.css`, `web/src/pages/FilmPage.test.tsx`, `web/src/pages/NotFound.tsx`
- Modifiés : `web/src/Root.tsx`, `web/src/Root.test.tsx`, `web/src/main.tsx`, `web/src/components/FilmCard.tsx`, `web/src/components/FilmCard.css`, `web/src/components/components.test.tsx`, `web/src/components/DayScreenings.test.tsx`, `web/src/lib/screenings.ts`, `docs/architecture.md`, `docs/decisions.md`

## Hors scope

- Bouton favori sur la fiche (#17, il faut l'auth).
- Filtres sur la fiche ; historique des séances passées (SPEC : non exposé).
- Vrai statut HTTP 404 côté Cloudflare Pages ; balises meta / Open Graph par film.
- Restaurer le défilement de l'accueil au retour.
