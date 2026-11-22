-- Initial schema. See docs/SPEC.md (Modèle de données) and docs/architecture.md.

create table public.cinemas (
  id               text primary key,          -- slug: 'champo', 'louxor'...
  name             text not null,
  address          text,
  arrondissement   smallint,
  lat              double precision,          -- V2 (travel times)
  lng              double precision,
  website_url      text,
  booking_base_url text,
  accepts_ugc      boolean not null default false,
  ugc_verified_at  date,
  source           text,                      -- chosen in spike #1
  source_ref       text,
  last_import_at   timestamptz,
  last_import_ok   boolean,
  coverage_until   date
);

create table public.films (
  tmdb_id         integer primary key,
  title           text not null,
  original_title  text,
  year            smallint,
  runtime_min     smallint,
  directors       text[] not null default '{}',
  overview        text,
  poster_path     text,
  tmdb_fetched_at timestamptz not null default now()
);

create table public.screenings (
  id            bigint generated always as identity primary key,
  cinema_id     text not null references public.cinemas (id),
  tmdb_id       integer references public.films (tmdb_id),
  raw_title     text not null,
  starts_at     timestamptz not null,
  version       text check (version in ('VO', 'VOSTFR', 'VF')),
  format        text,
  booking_url   text,
  source_key    text not null unique,
  first_seen_at timestamptz not null default now(),
  last_seen_at  timestamptz not null default now(),
  cancelled_at  timestamptz
);
create index screenings_starts_at_idx on public.screenings (starts_at);
create index screenings_tmdb_starts_idx on public.screenings (tmdb_id, starts_at);
create index screenings_cinema_starts_idx on public.screenings (cinema_id, starts_at);

create table public.title_matches (
  id               bigint generated always as identity primary key,
  normalized_title text not null,
  cinema_id        text references public.cinemas (id),
  year_hint        smallint,
  tmdb_id          integer,
  method           text not null check (method in ('exact', 'fuzzy', 'override', 'none')),
  score            real,
  matched_at       timestamptz not null default now(),
  unique nulls not distinct (normalized_title, cinema_id, year_hint)
);

create table public.profiles (
  user_id           uuid primary key references auth.users (id) on delete cascade,
  alerts_enabled    boolean not null default true,
  unsubscribe_token uuid not null default gen_random_uuid() unique,
  created_at        timestamptz not null default now()
);

create table public.favorites (
  user_id         uuid not null references auth.users (id) on delete cascade,
  tmdb_id         integer not null,
  created_at      timestamptz not null default now(),
  last_alerted_at timestamptz,
  primary key (user_id, tmdb_id)
);
create index favorites_tmdb_idx on public.favorites (tmdb_id);

create table public.import_runs (
  id           bigint generated always as identity primary key,
  started_at   timestamptz not null default now(),
  finished_at  timestamptz,
  cinema_id    text references public.cinemas (id),
  status       text not null check (status in ('running', 'ok', 'error')),
  n_screenings integer,
  n_unmatched  integer,
  error        text
);

-- Row Level Security: screenings data is public, user data is private, the pipeline uses
-- service_role (bypasses RLS).
alter table public.cinemas enable row level security;
alter table public.films enable row level security;
alter table public.screenings enable row level security;
alter table public.title_matches enable row level security;
alter table public.profiles enable row level security;
alter table public.favorites enable row level security;
alter table public.import_runs enable row level security;

create policy "cinemas are public" on public.cinemas for select using (true);
create policy "films are public" on public.films for select using (true);
create policy "screenings are public" on public.screenings for select using (true);

create policy "own profile: read" on public.profiles
  for select using ((select auth.uid()) = user_id);
create policy "own profile: update" on public.profiles
  for update using ((select auth.uid()) = user_id);

create policy "own favorites: read" on public.favorites
  for select using ((select auth.uid()) = user_id);
create policy "own favorites: insert" on public.favorites
  for insert with check ((select auth.uid()) = user_id);
create policy "own favorites: delete" on public.favorites
  for delete using ((select auth.uid()) = user_id);

-- A profile row for every new auth user.
create function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (user_id) values (new.id);
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
