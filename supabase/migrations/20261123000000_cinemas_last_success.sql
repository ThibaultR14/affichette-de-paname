-- #12: "mis à jour il y a …" dates the last successful import. last_import_at stays the
-- last attempt (written on failure too), last_success_at is only written on success.
alter table public.cinemas add column last_success_at timestamptz;
update public.cinemas set last_success_at = last_import_at where last_import_ok;
