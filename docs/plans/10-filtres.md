# Plan #10 - Filtres : salles, UGC, patrimoine

Issue : #10. Branche : `feat/10-filtres`, depuis `main`.

## Ce qui existe déjà

- `Chip` (bascule, `aria-pressed`) et `ActiveFilterChip` (« × louxor », pointillés) (#2), visibles sur `/styleguide`, avec un `.link-button` « tout effacer ».
- `useSelectedDay` (#9) écrit `?jour=` par `replaceState` en gardant les autres paramètres.
- `DayScreenings` charge le jour puis `groupByFilm` → cartes `DayFilm` (année, salles avec `acceptsUgc`).
- `fetchCinemas` (utilisé par `CinemaList`).

## Comportement

- URL (cf. architecture.md) : `?salles=champo,louxor&ugc=1&patrimoine=0`.
  - `salles` : ids séparés par des virgules ; vide ou absent = toutes. Les ids inconnus (absents de `cinemas`) sont ignorés et retirés de l'URL une fois la liste des salles chargée (pas si la liste revient vide). Les valeurs mal formées (`salles=Champo`, `ugc=oui`) sont retirées dès l'arrivée. Virgules non encodées dans l'URL.
  - `ugc=1` : seulement les salles qui acceptent la carte. Toute autre valeur = inactif.
  - `patrimoine` : **actif par défaut**, `patrimoine=0` le coupe. Le paramètre n'est écrit que pour le désactiver.
  - Écriture par `replaceState` comme le jour (pas d'entrée d'historique par clic), `?jour=` conservé ; `popstate` relu.
- Filtrage **côté client**, sur les cartes déjà chargées (pas de nouvelle requête quand on change un filtre) :
  - salles et UGC : on retire d'une carte les salles qui ne passent pas, puis les cartes sans salle ;
  - patrimoine : on garde une carte si `year <= année Paris de today − 20`, ou si l'année est inconnue (pas de correspondance TMDB, ou TMDB sans année).
- UI sous le bandeau des jours :
  - bouton « affiner » (`aria-expanded`, `aria-controls`) qui déplie le panneau sous la barre, sans modale. Fermé par défaut.
  - panneau : puces « patrimoine (+ de 20 ans) », « carte ugc », puis une puce par salle (nom, ordre alphabétique).
  - ligne des filtres actifs, toujours visible : « × patrimoine », « × carte ugc », « × <salle> »…, et « tout effacer » s'il y a au moins un filtre actif. « tout effacer » coupe aussi patrimoine (on voit tout).
- Titre : « N films demain » compte les cartes filtrées.
- Aucun résultat **à cause des filtres** (le jour a des films, aucun ne passe) : « rien ce jour-là avec ces filtres. essaie sans « patrimoine » ? » si patrimoine est actif, sinon « rien ce jour-là avec ces filtres. », plus un bouton « tout effacer ». Le message « rien de programmé … » (jour vide sans filtre) reste tel quel.

## Étapes

1. **`lib/url.ts`** : `replaceSearch(search)` sorti de `dayParam.ts` (partagé par les deux hooks).
2. **`lib/filters.ts`** (pur) : type `Filters = { cinemas: string[]; ugc: boolean; heritage: boolean }`, `DEFAULT_FILTERS`, `readFilters(search)`, `withFilters(search, filters)` (garde `jour` et le reste, `salles` trié et dédoublonné), `heritageMaxYear(today)`, `filterFilms(films, filters, today)`, `hasActiveFilters`. Puis le hook **`useFilters()`** → `{ filters, setFilters }` (lecture `window.location`, `replaceState`, `popstate`).
3. **`components/FilterPanel.tsx` (+ `.css`)** : bouton « affiner », panneau de `Chip`, ligne des `ActiveFilterChip` + « tout effacer ». Props : `cinemas`, `filters`, `onChange`.
4. **`DayScreenings`** : prop `filters` (défaut : `NO_FILTERS`, le composant n'impose pas patrimoine ; `App` passe toujours les filtres de l'URL) et `onClearFilters` ; applique `filterFilms` après chargement ; message dédié quand les filtres vident le jour.
5. **`App.tsx`** : charge les salles une fois (`fetchCinemas`) pour le panneau, retire de l'URL les ids inconnus, branche `useFilters`. `CinemaList` garde son propre chargement (hors scope de le mutualiser).
6. Docs : `architecture.md` (section front : filtres), `decisions.md` (filtrage client, patrimoine écrit seulement à 0, « tout effacer » coupe patrimoine).

## Tests (écrits d'abord)

- `filters.test.ts` : lecture (défauts, `salles` vide / doublons / ids mal formés, `ugc=1` vs autres, `patrimoine=0`), écriture qui garde `jour`, aller-retour ; `filterFilms` : salle, UGC, salle + UGC, patrimoine au seuil exact (année − 20 incluse, − 19 exclue), film sans année et sans TMDB toujours visibles, cartes sans salle retirées ; hook : `setFilters` écrit l'URL sans `pushState`, `popstate`.
- `FilterPanel.test.tsx` : panneau fermé par défaut, « affiner » l'ouvre (`aria-expanded`), bascule d'une salle / UGC / patrimoine, puce « × salle » retire la salle, « tout effacer » remet à vide (patrimoine coupé), pas de « tout effacer » sans filtre.
- `DayScreenings.test.tsx` : filtres appliqués sans recharger, compte du titre, message dédié avec ou sans patrimoine, jour vide sans filtre → ancien message.
- `App.test.tsx` : `?salles=louxor&ugc=1` → filtres appliqués et puces affichées ; clic sur une puce → URL mise à jour avec `jour` conservé ; patrimoine actif par défaut masque un film récent ; id inconnu retiré de l'URL.
- Vérif manuelle : `npm run dev`, capture 375 px et desktop, panneau ouvert.

## Fichiers touchés

- Nouveaux : `web/src/lib/url.ts`, `web/src/lib/filters.ts`, `web/src/lib/filters.test.ts`, `web/src/components/FilterPanel.tsx`, `web/src/components/FilterPanel.css`, `web/src/components/FilterPanel.test.tsx`
- Modifiés : `web/src/lib/dayParam.ts`, `web/src/components/DayScreenings.tsx`, `web/src/components/DayScreenings.css`, `web/src/components/DayScreenings.test.tsx`, `web/src/App.tsx`, `web/src/App.test.tsx`, `docs/architecture.md`, `docs/decisions.md`

## Hors scope

- Filtres sur la fiche film (#11) et sur les favoris.
- Filtres VO / VF, format, arrondissement, plage horaire.
- Mutualiser le chargement des salles entre `CinemaList` et le panneau.
- Compteur de séances par puce de salle.
