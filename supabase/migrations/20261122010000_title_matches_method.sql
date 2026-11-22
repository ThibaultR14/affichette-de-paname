-- #6: title_matches follows the matching strategy of spike #1 (docs/spikes/01-sources.md).
-- The old method values (exact, fuzzy) were never written: the table is empty.
alter table public.title_matches drop constraint title_matches_method_check;
alter table public.title_matches add constraint title_matches_method_check
  check (method in ('override', 'source', 'director', 'title', 'none'));
-- Why a cached "none" failed (empty, no_result, ambiguous, low_score), for the import report.
alter table public.title_matches add column reason text;
