# Plan #4 - Déploiement front sur Cloudflare Pages

Issue : #4. Branche : `feat/4-cloudflare-pages` (depuis `main`).

## Écarts avec l'issue

- **19 salles, pas 20** : MK2 Cultissime est retiré (décision du 2026-11-22). Je corrige le critère dans le corps de l'issue.
- **Projet Cloudflare** : il se crée depuis ton compte Cloudflare (dashboard). Je prépare le repo et je te donne les réglages exacts à saisir. Les deux premiers critères se cochent une fois ces réglages faits.

## Choix : intégration Git de Cloudflare Pages (pas de GitHub Action)

- Cloudflare build lui-même à chaque push sur `main` (production) et crée une preview par PR, avec un commentaire sur la PR. C'est le premier critère, sans rien écrire.
- Aucun secret Cloudflare dans GitHub. Les deux variables `VITE_*`, publiques par nature, sont saisies dans le dashboard (Production et Preview).
- Écarté : `wrangler pages deploy` dans une Action (il faut un `CLOUDFLARE_API_TOKEN` dans les secrets et un workflow à maintenir pour faire la même chose).
- Routage SPA : sans `404.html`, Pages renvoie `index.html` pour les chemins inconnus, donc `/styleguide` (et plus tard `/film/:id`) marche sans `_redirects`.

Réglages à saisir (Workers & Pages → Create → Pages → Connect to Git) :
| Réglage | Valeur |
|---|---|
| Production branch | `main` |
| Root directory | `web` |
| Build command | `npm run build` |
| Output directory | `dist` |
| Variables (Production + Preview) | `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` |

Version de Node : fixée par `web/.nvmrc` (`24`, comme la CI), que lit l'image de build Cloudflare.

## Étapes

1. **Client Supabase** `web/src/lib/supabase.ts` : `createClient` à partir de `import.meta.env.VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY`. Si une des deux manque, on exporte `null` au lieu de planter (preview mal configurée, tests). Typage de `import.meta.env` dans `vite-env.d.ts`.
2. **Lecture des salles** `web/src/lib/cinemas.ts` : `fetchCinemas()` → `select id, name, arrondissement, accepts_ugc` trié par nom, type `Cinema`. Erreur Supabase → exception.
3. **Composant** `web/src/components/CinemaList.tsx` (+ `.css`) : liste de noms, arrondissement en `muted` (« 5e »), pastille `ugc` à côté du nom (design.md). États :
   - chargement : « on déplie l'affichette… » ;
   - erreur ou client absent : annotation Caveat « (on n'arrive pas à joindre la base, réessaie plus tard) » ;
   - liste : titre « les 19 salles » (nombre calculé).
4. **Accueil** `App.tsx` : garde le titre et la phrase d'accueil, ajoute `CinemaList`. Le reste de la vue (par film, par jour) viendra avec son issue.
5. **Docs** : section « Déploiement » dans `architecture.md` (réglages ci-dessus, URL `*.pages.dev`), entrée dans `decisions.md` (intégration Git plutôt qu'Action).

## Tests (écrits d'abord)

- `cinemas.test.ts` : `fetchCinemas` avec un client simulé : renvoie les lignes, lève une erreur si Supabase en renvoie une, renvoie une erreur claire si le client est `null`.
- `CinemaList.test.tsx` (avec un `fetchCinemas` injecté) : état de chargement, liste de 19 salles avec la pastille `ugc` sauf pour le Club de l'Étoile, message d'erreur.
- `App.test.tsx` : toujours le titre, plus la présence de la liste (module simulé).
- Vérif manuelle : `npm run dev` avec `web/.env.local`, les 19 salles s'affichent depuis le projet cloud (si le seed y a été poussé).

## Fichiers touchés

- Nouveaux : `web/.nvmrc`, `web/src/vite-env.d.ts` (si absent), `web/src/lib/supabase.ts`, `web/src/lib/cinemas.ts`, `web/src/lib/cinemas.test.ts`, `web/src/components/CinemaList.tsx`, `web/src/components/CinemaList.css`, `web/src/components/CinemaList.test.tsx`
- Modifiés : `web/src/App.tsx`, `web/src/App.test.tsx`, `docs/architecture.md`, `docs/decisions.md`

## Hors scope

- Routeur, vue par film et par jour, filtres.
- Nom de domaine (question ouverte de la SPEC) : on reste sur `*.pages.dev`.
- En-têtes de sécurité (`_headers`, CSP) : à faire avant la mise en public.
