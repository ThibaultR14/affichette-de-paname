-- RLS and seed checks. Run with `npx supabase test db` (local stack) or in CI.
begin;
create extension if not exists pgtap with schema extensions;

select plan(26);

-- Fixtures, as the superuser: two users (the trigger creates their profiles), one
-- favorite each, one film and one screening, one title match and one import run.
insert into auth.users (id, email, aud, role)
values
  ('00000000-0000-0000-0000-00000000000a', 'a@example.com', 'authenticated', 'authenticated'),
  ('00000000-0000-0000-0000-00000000000b', 'b@example.com', 'authenticated', 'authenticated');
insert into public.favorites (user_id, tmdb_id)
values
  ('00000000-0000-0000-0000-00000000000a', 11),
  ('00000000-0000-0000-0000-00000000000b', 22);
insert into public.films (tmdb_id, title, year) values (11, 'le mépris', 1963);
insert into public.screenings (cinema_id, tmdb_id, raw_title, starts_at, source_key)
values ('champo', 11, 'Le Mépris', '2026-11-24 19:30+00', 'test:1');
insert into public.title_matches (normalized_title, tmdb_id, method)
values ('le mepris', 11, 'title');
insert into public.import_runs (cinema_id, status) values ('champo', 'ok');

-- Seed
select is((select count(*)::int from public.cinemas), 19, 'seed: 19 cinemas');
select is(
  (select count(*)::int from public.cinemas where ugc_verified_at is null), 0,
  'seed: every cinema has ugc_verified_at');
select is(
  (select array_agg(id order by id) from public.cinemas where not accepts_ugc),
  array['club-etoile'],
  'seed: only Club de l''Étoile refuses the UGC card');
select is(
  (select count(*)::int from public.cinemas
   where address is null or arrondissement is null or website_url is null
      or booking_base_url is null or source is null),
  0, 'seed: no missing address, arrondissement, site, programme link or source');
select is(
  (select count(*)::int from public.cinemas
   where source in ('scare', 'dulac') and source_ref is null),
  0, 'seed: scare and dulac cinemas have a source_ref');
select is(
  (select count(*)::int from public.profiles), 2, 'trigger: one profile per new user');
select throws_ok(
  $$insert into public.title_matches (normalized_title, tmdb_id, method) values ('x', 1, 'exact')$$,
  '23514', null, 'title_matches: method limited to the matching strategy (#6)');

-- anon: public data is readable
set local role anon;
select is((select count(*)::int from public.cinemas), 19, 'anon reads cinemas');
select lives_ok(
  'select coverage_until, last_import_ok, last_success_at from public.cinemas',
  'anon reads the coverage of each cinema (#12)');
select is((select count(*)::int from public.films), 1, 'anon reads films');
select is((select count(*)::int from public.screenings), 1, 'anon reads screenings');

-- anon: private and pipeline data is not
select is_empty('select * from public.favorites', 'anon sees no favorites');
select is_empty('select * from public.profiles', 'anon sees no profiles');
select is_empty('select * from public.title_matches', 'anon sees no title_matches');
select is_empty('select * from public.import_runs', 'anon sees no import_runs');

-- anon: no writes
select throws_ok(
  $$insert into public.cinemas (id, name) values ('x', 'x')$$,
  '42501', null, 'anon cannot insert cinemas');
select throws_ok(
  $$insert into public.favorites (user_id, tmdb_id)
    values ('00000000-0000-0000-0000-00000000000a', 33)$$,
  '42501', null, 'anon cannot insert favorites');
select is_empty(
  $$update public.cinemas set name = 'x' returning id$$, 'anon cannot update cinemas');
reset role;

-- authenticated as user A: only A's rows
set local role authenticated;
set local request.jwt.claims = '{"sub": "00000000-0000-0000-0000-00000000000a", "role": "authenticated"}';
select results_eq(
  'select tmdb_id from public.favorites', array[11], 'A sees only their favorite');
select results_eq(
  'select user_id from public.profiles',
  array['00000000-0000-0000-0000-00000000000a'::uuid], 'A sees only their profile');
select lives_ok(
  $$insert into public.favorites (user_id, tmdb_id)
    values ('00000000-0000-0000-0000-00000000000a', 33)$$,
  'A can add a favorite');
select throws_ok(
  $$insert into public.favorites (user_id, tmdb_id)
    values ('00000000-0000-0000-0000-00000000000b', 33)$$,
  '42501', null, 'A cannot add a favorite for B');
select is_empty(
  $$delete from public.favorites
    where user_id = '00000000-0000-0000-0000-00000000000b' returning tmdb_id$$,
  'A cannot delete B''s favorites');
select is_empty(
  $$update public.profiles set alerts_enabled = false
    where user_id = '00000000-0000-0000-0000-00000000000b' returning user_id$$,
  'A cannot update B''s profile');
select is_empty(
  'select * from public.import_runs', 'authenticated sees no import_runs');
select throws_ok(
  $$insert into public.screenings (cinema_id, raw_title, starts_at, source_key)
    values ('champo', 'x', now(), 'test:2')$$,
  '42501', null, 'authenticated cannot insert screenings');
reset role;

select * from finish();
rollback;
