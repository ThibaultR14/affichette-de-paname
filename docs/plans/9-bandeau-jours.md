# Plan #9 - Bandeau 7 jours + état dans l'URL

Issue : #9. Branche : `feat/9-bandeau-jours`, créée depuis `feat/8-seances-du-jour` (PR #38 pas encore mergée : la PR #9 visera `main` une fois #38 mergée, ou sera rebasée).

## Ce qui existe déjà

- `DayStrip` (#2) : 7 boutons, `aria-current="date"` + trait ondulé sur le jour choisi, 44 px de haut, `onSelect`. Visible sur `/styleguide`.
- `lib/days.ts` : `parisDate`, `rollingWeek`, `dayLabel`, `dayTitle`, `parisDayRange`.
- `App` passe `today` (calculé au montage) à `DayScreenings`.

## Comportement

- `?jour=AAAA-MM-JJ` choisit le jour. Absent, mal formé (`2026-13-40`, `demain`) ou hors des 7 jours glissants (passé ou trop loin) → aujourd'hui.
- Un `?jour=` invalide est retiré de l'URL au chargement (`replaceState`), pour que l'URL dise ce qu'on voit.
- Clic sur un jour → `?jour=` mis à jour avec `history.replaceState` (pas une entrée d'historique par clic : « retour » quitte le site au lieu de rejouer les jours). Les autres paramètres (filtres de #10) sont conservés. Le jour est écrit même pour « auj. » : un lien partagé désigne une date précise.
- `popstate` relu quand même (retour depuis une future page `/film/…`).
- **Minuit** (suite notée dans le plan #8) : `today` est recalculé à minuit Paris (minuteur sur `parisDayRange(today).to`) et au retour sur l'onglet (`visibilitychange`, les minuteurs dorment sur mobile). Si le jour choisi sort de la fenêtre, on revient à aujourd'hui.
- Clavier : boutons natifs (Tab, Entrée, Espace), contour `:focus-visible` déjà global. Au montage, le jour choisi est amené dans la zone visible du bandeau, sinon un lien vers le 7ᵉ jour ouvre un bandeau où il est caché à 375 px. On règle `scrollLeft` du bandeau, pas `scrollIntoView` (qui ferait aussi défiler la page, par exemple sur `/styleguide`).

## Étapes

1. **`lib/days.ts` → `resolveDay(param, week)`** (pure) : `param` s'il est dans `week`, sinon `week[0]`. L'appartenance à la liste suffit à valider le format.
2. **`lib/dayParam.ts`** : `readDayParam(search)` et `withDayParam(search, day)` (purs, `URLSearchParams`), puis le hook **`useSelectedDay(now?)`** → `{ today, week, day, setDay }` : lit `window.location`, écrit avec `replaceState`, écoute `popstate`, gère minuit et `visibilitychange`.
3. **`DayStrip`** : `scrollLeft` ajusté pour montrer le jour choisi (calcul par `getBoundingClientRect`).
4. **`App.tsx`** : `useSelectedDay()`, `DayStrip` sous la phrase d'accueil, `DayScreenings day={day} today={today}`.
5. Docs : `architecture.md` (section front), `decisions.md` (`replaceState`, jour toujours écrit, invalide → retiré).

## Tests (écrits d'abord)

- `days.test.ts` : `resolveDay` : dans la fenêtre, absent, mal formé, passé, au-delà de 7 jours.
- `dayParam.test.ts` : lecture / écriture en gardant les autres paramètres ; hook (fausses horloges) : jour par défaut, `?jour=` valide, invalide retiré de l'URL, `setDay` écrit l'URL sans `pushState`, `popstate`, passage de minuit qui fait sortir le jour choisi → aujourd'hui, `visibilitychange`.
- `components.test.tsx` : `DayStrip` règle `scrollLeft` pour montrer le jour choisi, sans `scrollIntoView` ; navigation clavier (focus au Tab sur chaque bouton).
- `App.test.tsx` : `?jour=` du lendemain → « … demain » et bouton « dem. » `aria-current` ; clic sur un jour → URL et vue changent ; date hors fenêtre → aujourd'hui.
- Vérif manuelle : `npm run dev`, capture 375 px et desktop, lien `?jour=` vers le 7ᵉ jour.

## Fichiers touchés

- Nouveaux : `web/src/lib/dayParam.ts`, `web/src/lib/dayParam.test.ts`
- Modifiés : `web/src/lib/days.ts`, `web/src/lib/days.test.ts`, `web/src/components/DayStrip.tsx`, `web/src/components/components.test.tsx`, `web/src/App.tsx`, `web/src/App.test.tsx`, `docs/architecture.md`, `docs/decisions.md`

## Hors scope

- Routeur (`/film/:id`, #11) : on lit `window.location` directement, le hook sera branché sur le routeur à ce moment-là.
- Filtres salles / UGC / patrimoine dans l'URL (#10) ; seul `jour` est géré ici (mais les autres paramètres sont préservés).
- Flèches gauche/droite dans le bandeau (motif « tabs » ARIA) : Tab suffit pour 7 boutons, et ce ne sont pas des onglets.
