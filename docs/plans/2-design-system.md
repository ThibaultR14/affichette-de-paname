# Plan #2 - Design system

Issue : #2. Branche : `feat/2-design-system` (depuis `main`).

## TODO de `docs/design.md` : propositions à trancher

1. **Thème par défaut** : on suit la préférence du système (`prefers-color-scheme`), et clair si le système ne dit rien. La bascule « passer en sombre » / « passer en clair » est mémorisée (`localStorage`, clé `affichette-theme`, seule donnée stockée). Un script inline dans `index.html` pose `data-theme` avant le premier rendu.
   - Pourquoi pas « clair forcé » : le soir dans le métro, un écran blanc éblouit, et le système de l'utilisateur sait déjà ce qu'il préfère.
2. **Pastilles de séance** (`vo`, `vf`, `35mm`, `70mm`, `4k`…) : texte en minuscules, 13 px gras, bordure 1,5 px `ink`, coins 3 px, sans fond. Une seule forme pour toutes, aucune couleur en plus. La pastille `ugc` se met à côté du nom de la salle, pas à côté de l'heure, avec la même forme à bordure pleine (les pointillés restent réservés aux filtres actifs).
3. **Carte sur mobile** : sous 640 px, **ligne compacte** : vignette 2:3 de 80 px à gauche (scotch gardé, sans rotation), titre et méta à droite, séances en dessous sur toute la largeur. À partir de 640 px, **carte photo** de Recsys (rotation ±1,8°, affiche 2:3) dans une grille `minmax(260px, 1fr)`. Raison : les séances prennent de la place, une affiche pleine largeur obligerait à scroller deux écrans par film.

## Fichiers touchés

- `web/package.json` : `@fontsource/courier-prime`, `@fontsource/caveat`.
- `web/index.html` : script de thème avant le premier rendu.
- `web/src/styles/tokens.css` (nouveau) : imports des polices, jetons clair (`:root`) et sombre (`:root[data-theme='dark']`), `color-scheme`, ombre photo. Remplace les jetons de `index.css`, qui garde la base (body, liens, conteneur).
- `web/src/styles/contrast.test.ts` (nouveau, repris de Recsys) : AA (≥ 4,5:1) pour `ink`, `muted`, `pen` sur `paper` et `surface`, dans les deux thèmes ; bordures `ink` ≥ 3:1 ; `surface` ≠ `paper` ; aucun jeton orange ; le sombre redéfinit chaque jeton.
- `web/src/styles/fonts.test.ts` (nouveau) : aucune URL `fonts.googleapis`/`fonts.gstatic` dans `index.html` ni dans `src/**/*.css`.
- `web/src/lib/theme.ts` + test : `currentTheme`, `applyTheme` (stockage protégé par try/catch).
- `web/src/lib/days.ts` + test : `dayLabel(date, today)` → « auj. », « dem. », « mer. 25 ».
- `web/src/components/` (CSS plain, un fichier `.css` par composant, pas de Tailwind) :
  - `Button.tsx` : bouton principal (surface, bordure 2 px encre, 48 px, gras 16 px).
  - `Chip.tsx` : puce à bascule (`aria-pressed`, enfoncée = encre pleine / texte papier, ≥ 44 px) et variante `removable` (« × louxor », pointillés).
  - `Badge.tsx` : pastille de séance.
  - `DayStrip.tsx` : 7 puces défilantes, jour choisi souligné d'un trait ondulé au stylo (SVG), `aria-current="date"`, ≥ 44 px.
  - `FilmCard.tsx` (statique) : affiche ou cadre pointillé + « (on n'a pas trouvé ce film, désolé) », titre, « réalisateur, année · durée », séances groupées par salle (« 14:00 → 16:05 » en lien de réservation, heure de fin seulement si la durée est connue), pastilles, cœur favori sur l'étiquette « ✱ » (SVG, pas d'emoji).
  - `ThemeToggle.tsx` : lien-bouton « passer en sombre » / « passer en clair ».
- `web/src/pages/Styleguide.tsx` : jetons (nuanciers), typo, boutons, puces, pastilles, bandeau, cartes (avec et sans TMDB, avec et sans durée), bascule de thème. Données factices dans le fichier.
- `web/src/main.tsx` : `/styleguide` affiche la page (chargée en lazy), sinon `App`. Pas de routeur pour l'instant : il arrivera avec la vue principale.
- `docs/design.md` : TODO remplacés par les choix ci-dessus. `docs/decisions.md` : thème par défaut + CSS sans Tailwind.

## Étapes

1. Polices + `tokens.css` + `contrast.test.ts` + `fonts.test.ts` (tests d'abord).
2. `theme.ts` + script `index.html` + `ThemeToggle`.
3. `dayLabel` (test d'abord), puis `DayStrip`.
4. `Button`, `Chip`, `Badge`, `FilmCard`, avec tests Testing Library (rôles, `aria-pressed`, heure de fin absente sans durée, cadre sans affiche, liens de réservation).
5. Page `/styleguide`, capture d'écran mobile et desktop dans les deux thèmes si un navigateur est disponible, comparaison avec `docs/design.md`.
6. Docs, lint, tests, PR.

## Tests

- `contrast.test.ts`, `fonts.test.ts`, `theme.test.ts`, `days.test.ts` (`dayLabel`), un test par composant, un test de rendu de `/styleguide`.

## Hors scope

- Vue principale, filtres réels et état dans l'URL, routeur, données Supabase.
- Favori fonctionnel (le cœur est affiché, sans action).
- Pied de page et page « à propos » (TODO laissé dans `design.md`).
- Tests E2E/axe (Playwright) : pas encore dans le projet.
