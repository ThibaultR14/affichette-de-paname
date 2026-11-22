# Plan #3 - Supabase : projet, migration, salles

Issue : #3. Branche : `feat/3-supabase-setup` (depuis `main`).

## Écarts avec l'issue

- **19 salles, pas 20** : MK2 Cultissime est retiré (décision du 2026-11-22, SPEC v0.2). Je corrige le critère de l'issue dans la PR.
- **Création du projet cloud** : elle demande ton compte Supabase (`supabase login`, choix de la région, mot de passe de la base). Je prépare tout en local et je te donne les 3 commandes à lancer. Le `db push` distant reste coché par toi.

## Étapes

1. `npx supabase init` → `supabase/config.toml` (versionné). Ports par défaut, `seed.sql` activé, auth email activée (magic link en #10, pas ici).
2. **Stack locale** (`npx supabase start`, Docker) : on applique la migration et le seed pour la première fois, on corrige ce qui casse.
3. **`supabase/seed.sql`** : 19 `insert` dans `cinemas`, idempotents (`on conflict (id) do update`). Pour chaque salle :
   - `id` (slug), `name`, `address`, `arrondissement`, `website_url`, `booking_base_url` (page programme de la salle, le lien de repli de la SPEC) ;
   - `source` / `source_ref` d'après le spike : `scare` (+ `cinenom` SCARE), `dulac`, `html`, `webedia` (en attente d'accord), `none` ;
   - `accepts_ugc` + `ugc_verified_at = 2026-11-22`, vérifiés sur la liste des salles partenaires du site UGC (pas l'hypothèse de la SPEC) ;
   - `lat` / `lng` laissés à `null` (V2).
   - Sources pour les adresses : site de chaque salle, recoupé avec cip-paris.fr. Je les récupère en lecture simple des pages publiques.
4. **Test RLS** en pgTAP, `supabase/tests/rls.test.sql`, lancé par `npx supabase test db` :
   - en rôle `anon` : `select` sur `cinemas`, `films`, `screenings` OK, et les 19 salles sont présentes ;
   - en rôle `anon` : 0 ligne visible dans `favorites` et `profiles` (on insère d'abord un utilisateur et un favori en `postgres`), et `insert` refusé partout ;
   - en rôle `authenticated` (claim `sub` = utilisateur A) : A voit son profil et son favori, pas ceux de B ;
   - en `anon` : `title_matches` et `import_runs` illisibles.
5. **CI** : job `supabase` dans `ci.yml` (`supabase/setup-cli`, `supabase db start`, `supabase test db`). Il vérifie à chaque PR que la migration et le seed s'appliquent sur une base vierge.
6. **Doc** : section « Base de données » dans `architecture.md` (commandes locales, lien cloud), mise à jour de la SPEC si la vérification UGC contredit l'hypothèse, `decisions.md` si un choix tombe (par ex. tests pgTAP).
7. **Projet cloud** (toi) : `npx supabase login`, `npx supabase link --project-ref <ref>`, `npx supabase db push`, puis `psql`/éditeur SQL pour le seed (`db push` n'applique pas `seed.sql` en distant) ou `npx supabase db push --include-seed`.

## Fichiers touchés

- `supabase/config.toml` (nouveau), `supabase/seed.sql` (nouveau), `supabase/tests/rls.test.sql` (nouveau)
- `supabase/migrations/20261122000000_init.sql` : seulement si l'application locale révèle un bug
- `.github/workflows/ci.yml`, `docs/architecture.md`, `docs/SPEC.md` (UGC), `docs/decisions.md`, `CLAUDE.md` (commande `supabase test db`)

## Hors scope

- Auth magic link et emails (#10), Edge Function `tmdb-search`, suppression de compte.
- Coordonnées GPS (V2). Écriture du pipeline dans la base (#7).
- `web/.env.local` : tu y mets l'URL et la clé anon une fois le projet créé.
