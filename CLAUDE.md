# L'Affichette de Paname
Site qui centralise sur 7 jours les séances des cinémas indépendants parisiens (films de patrimoine), avec favoris et alertes email. Voir @docs/SPEC.md et @docs/architecture.md.

## Commandes
- dev : `cd web && npm run dev`
- test : `cd web && npm test` · `cd pipeline && uv run pytest`
- lint : `cd web && npm run lint && npm run typecheck` · `cd pipeline && uv run ruff check . && uv run ruff format --check .`
- format : `cd web && npm run format` · `cd pipeline && uv run ruff format .`
- schéma : `supabase/migrations/*.sql` (appliqué avec `supabase db push`)
- Windows : `npm test` passe par `web/scripts/vitest.mjs` (bug Vitest avec `c:` en minuscule). Ne pas appeler `npx vitest` directement.

## Conventions
- Monorepo : `web/` (React + Vite + TS), `pipeline/` (Python 3.12 + uv), `supabase/` (migrations SQL, Edge Functions).
- Textes de l'interface en français, tutoiement, minuscules (voir docs/design.md). Code et identifiants en anglais.
- Heures stockées en UTC (`timestamptz`), affichées et découpées en jours en Europe/Paris.
- Jamais de secret dans le front : seules `VITE_SUPABASE_URL` et `VITE_SUPABASE_ANON_KEY` sont exposées. Le jeton TMDB passe par le pipeline ou l'Edge Function.
- Ne jamais journaliser une URL TMDB ni une clé. Cache TMDB : réutilisé moins de 30 jours, purgé au-delà de 6 mois (CGU).
- Sources de séances : pas d'Allociné ni d'agrégateur dont les CGU interdisent la collecte. Tests du pipeline sans réseau (fixtures).
- Correspondances TMDB corrigées à la main dans `pipeline/manual_overrides.csv`, jamais en dur dans le code.

## Workflow
- Toute feature part d'une issue GitHub.
- Sauvegarde chaque plan dans docs/plans/<numéro-issue>-<nom>.md avant d'implémenter.
- Note toute décision importante dans docs/decisions.md.
- Toute UI respecte docs/design.md.
- Lance les tests et le lint avant de dire qu'une tâche est finie, et montre la sortie.
- Branches : feat/<numéro>-<nom>, fix/<numéro>-<nom>. PR avec "Closes #<numéro>".

## Compaction
Lors d'une compaction, garde toujours : l'issue en cours, la liste des fichiers modifiés, les commandes de test.
