# Plan #8 - Accueil : séances du jour, par film

Issue : #8. Branche : `feat/8-seances-du-jour` (depuis `main`).

## Ce qui existe déjà

- `FilmCard` / `FilmGrid` (statiques, #2) : affiche, titre, méta, séances groupées par salle, heure de fin si durée connue, carte « non trouvée ». Il manque seulement la source de données.
- `lib/days.ts` : `parisDate`, `rollingWeek`, `parisTime`. `lib/cinemas.ts` montre le motif (client injectable, `null` → erreur claire).

## Périmètre

La vue reçoit un `day` (date Paris `YYYY-MM-DD`). Dans cette issue, `App` lui passe **aujourd'hui**. Le bandeau 7 jours et `?jour=` dans l'URL sont #9, les filtres (dont patrimoine) #10, la couverture par salle #12, le cœur #17.

## Étapes

1. **`lib/days.ts` → `parisDayRange(day)`** : `[début, fin[` du jour Paris en instants UTC (ISO). Calcul par le décalage Europe/Paris de l'instant (Intl), donc correct les jours de changement d'heure (23 h et 25 h).
2. **`lib/screenings.ts`**
   - `fetchDayScreenings(day, { now, client })` : une requête PostgREST
     `screenings.select('source_key, raw_title, starts_at, version, format, booking_url, cinema:cinemas(id, name, accepts_ugc, website_url), film:films(tmdb_id, title, year, runtime_min, directors, poster_path)')`
     `.gte('starts_at', from).lt('starts_at', to).is('cancelled_at', null).order('starts_at')`.
     Pour **aujourd'hui**, `from = max(now, début du jour)` : on ne montre pas les séances déjà commencées (usage dans la rue). Les autres jours, tout le jour.
   - `groupByFilm(rows)` (pure) → `FilmCardProps[]` :
     - clé = `tmdb_id`, à défaut le titre brut (insensible à la casse et aux espaces) : deux séances non trouvées de même titre dans deux salles font une seule carte ;
     - dans une carte : salles triées par nom, séances par heure ;
     - cartes triées par titre (`localeCompare` fr) ;
     - `posterUrl = https://image.tmdb.org/t/p/w342<poster_path>` ;
     - `bookingUrl = booking_url ?? cinemas.website_url ?? null` ;
     - `tilt` déterministe dérivé de la clé (±1,8°), pour que les cartes ne bougent pas à chaque rendu.
   - 1 000 lignes max par requête (`max_rows`) : une journée en compte quelques centaines au plus. Si on atteint 1 000, on lève une erreur plutôt que d'afficher un jour tronqué en silence.
3. **`FilmCard`** : `bookingUrl` devient `string | null` ; sans lien, l'heure est un texte simple (pas de lien mort).
4. **`components/DayScreenings.tsx`** (+ `.css`) : `load` injectable comme `CinemaList`, rechargé quand `day` change (réponse périmée ignorée). États :
   - chargement : « on déplie l'affichette… » ;
   - erreur ou client absent : « (on n'arrive pas à joindre la base, réessaie plus tard) » en Caveat ;
   - vide : « rien de programmé ce jour-là pour l'instant. » + annotation « (les salles publient souvent le mercredi) » ;
   - sinon `FilmGrid` de `FilmCard`, avec un titre « 12 films aujourd'hui » (« demain », « mer. 25 » via `dayLabel`).
5. **`App.tsx`** : phrase d'accueil de design.md (« salut. voilà ce qui passe… »), `DayScreenings day={today}`, puis la liste des salles existante en dessous (#12 la transformera en couverture). Conteneur 1 200 px, marges 16/24 px.

## Tests (écrits d'abord)

- `days.test.ts` : `parisDayRange` en hiver, en été, les jours de passage à l'heure d'été (23 h) et d'hiver (25 h).
- `screenings.test.ts` : filtres envoyés au client simulé (bornes, `cancelled_at`, ordre), `from = now` pour aujourd'hui et pas les autres jours ; erreur Supabase ; client `null` ; erreur à 1 000 lignes. `groupByFilm` : regroupement par film puis salle, tri, séance sans fiche avec titre brut et sans affiche, deux séances non trouvées de même titre regroupées, repli de `booking_url` sur `website_url` puis `null`, URL d'affiche.
- `DayScreenings.test.tsx` : chargement, cartes (titre, réalisateur, « 14:00 → 15:43 », pastilles, lien résa), carte non trouvée, vide, erreur, rechargement quand `day` change.
- `components.test.tsx` : heure sans lien quand `bookingUrl` est `null`.
- `App.test.tsx` : modules simulés, la vue du jour est présente.
- Vérif manuelle : `npm run dev` sur le projet cloud (séances SCARE importées par #7), capture mobile 375 px et desktop, comparée à design.md.

## Fichiers touchés

- Nouveaux : `web/src/lib/screenings.ts`, `web/src/lib/screenings.test.ts`, `web/src/components/DayScreenings.tsx`, `web/src/components/DayScreenings.css`, `web/src/components/DayScreenings.test.tsx`
- Modifiés : `web/src/lib/days.ts`, `web/src/lib/days.test.ts`, `web/src/components/FilmCard.tsx`, `web/src/components/components.test.tsx`, `web/src/App.tsx`, `web/src/App.test.tsx`, `web/src/index.css` (conteneur), `docs/architecture.md`, `docs/decisions.md`

## Hors scope

- Bandeau 7 jours, `?jour=` (#9) ; filtres salles / UGC / patrimoine (#10) ; fiche film et lien depuis la carte (#11) ; couverture par salle (#12) ; favoris (#17) ; badge « programme non disponible » (#31).
- Vue SQL ou RPC côté base : la jointure PostgREST suffit.

## Suite pour #9

- `today` est calculé au montage de `App` : une page ouverte avant minuit et rechargée après demanderait un jour passé (vide). Le bandeau de #9 doit recalculer `today` (ou rediriger `?jour=` passé vers aujourd'hui).
