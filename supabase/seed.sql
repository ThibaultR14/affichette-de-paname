-- The 19 cinemas (docs/SPEC.md). Idempotent: re-running updates the rows in place.
--
-- accepts_ugc: checked on 2026-11-22 against https://www.ugc.fr/cinemas-acceptant-ui.html
--   ("Paris > Cinémas partenaires"). Every cinema is listed except Club de l'Étoile.
-- Addresses: official site of the cinema, cross-checked with cip-paris.fr or the SCARE
--   dataset (cineadresse). "[cip]" = only found on cip-paris.fr, "[listing]" = only found
--   on third-party listings: to re-check by hand.
-- booking_base_url: programme page of the cinema, the fallback link when a screening has
--   no booking URL of its own.
-- source / source_ref: see docs/spikes/01-sources.md.
--   scare   -> source_ref = exact `cinenom` in the SCARE dataset
--   dulac   -> source_ref = cinema node id in the Dulac API (`cinemas_by_id`)
--   html    -> scraped from the cinema website (#14)
--   webedia -> blocked until written consent (#29, #30)
--   none    -> no usable source yet
-- lat / lng: left null until V2.

insert into public.cinemas
  (id, name, address, arrondissement, website_url, booking_base_url,
   accepts_ugc, ugc_verified_at, source, source_ref)
values
  ('filmotheque', 'Filmothèque du Quartier Latin', '9 rue Champollion, 75005 Paris', 5,
   'https://lafilmotheque.fr/', 'https://lafilmotheque.fr/',
   true, '2026-11-22', 'html', null),
  ('champo', 'Le Champo', '51 rue des Écoles, 75005 Paris', 5,
   'https://www.cinema-lechampo.com/', 'https://www.cinema-lechampo.com/films/horaires.html',
   true, '2026-11-22', 'scare', 'Le Champo'),
  -- [listing] address and site (pariscinemaclub.com, shared with Écoles Cinéma Club)
  ('christine', 'Christine Cinéma Club', '4 rue Christine, 75006 Paris', 6,
   'https://pariscinemaclub.com/christine-cinema-club/', 'https://pariscinemaclub.com/christine-cinema-club/',
   true, '2026-11-22', 'none', null),
  -- [listing] address and site
  ('ecoles', 'Écoles Cinéma Club', '23 rue des Écoles, 75005 Paris', 5,
   'https://pariscinemaclub.com/', 'https://pariscinemaclub.com/',
   true, '2026-11-22', 'none', null),
  -- [cip] address
  ('brady', 'Le Brady', '39 boulevard de Strasbourg, 75010 Paris', 10,
   'https://www.lebrady.fr/', 'https://www.lebrady.fr/horaires/',
   true, '2026-11-22', 'webedia', null),
  -- [listing] site; address from SCARE. SCARE only carries its events (#7), the full
  -- programme is on Webedia, pending consent.
  ('sept-parnassiens', 'Sept Parnassiens', '98 boulevard du Montparnasse, 75014 Paris', 14,
   'https://www.parnassiens.com/', 'https://www.parnassiens.com/',
   true, '2026-11-22', 'scare', 'Sept Parnassiens'),
  ('saint-andre-des-arts', 'Saint-André-des-Arts', '30 rue Saint-André-des-Arts, 75006 Paris', 6,
   'https://cinemasaintandre.com/', 'https://parisstandredesarts.cine.boutique/?tab=media',
   true, '2026-11-22', 'scare', 'Saint-André des Arts'),
  -- [cip] address
  ('publicis', 'Publicis Cinémas', '129 avenue des Champs-Élysées, 75008 Paris', 8,
   'https://www.publiciscinemas.com/', 'https://www.publiciscinemas.com/horaires/',
   true, '2026-11-22', 'webedia', null),
  -- SCARE only carries its events, full programme on Webedia pending consent.
  ('louxor', 'Le Louxor', '170 boulevard de Magenta, 75010 Paris', 10,
   'https://www.cinemalouxor.fr/', 'https://www.cinemalouxor.fr/films/',
   true, '2026-11-22', 'scare', 'Le Louxor - Palais du cinéma'),
  ('cineastes', 'Cinéma des Cinéastes', '7 avenue de Clichy, 75017 Paris', 17,
   'https://www.cinema-des-cineastes.fr/', 'https://www.cinema-des-cineastes.fr/',
   true, '2026-11-22', 'html', null),
  ('saint-germain-des-pres', 'Le Saint-Germain-des-Prés', '22 rue Guillaume Apollinaire, 75006 Paris', 6,
   'https://www.lesaintgermaindespres.com/', 'https://www.lesaintgermaindespres.com/programme/',
   true, '2026-11-22', 'webedia', null),
  ('club-etoile', 'Club de l''Étoile', '14 rue Troyon, 75017 Paris', 17,
   'https://clubdeletoile.fr/', 'https://clubdeletoile.fr/programmation/',
   false, '2026-11-22', 'html', null),
  ('archipel', 'L''Archipel', '17 boulevard de Strasbourg, 75010 Paris', 10,
   'https://www.larchipelcinema.com/', 'https://www.larchipelcinema.com/horaires/',
   true, '2026-11-22', 'none', null),
  ('grand-action', 'Le Grand Action', '5 rue des Écoles, 75005 Paris', 5,
   'https://www.legrandaction.com/', 'https://www.legrandaction.com/',
   true, '2026-11-22', 'scare', 'Le Grand Action'),
  ('reflet-medicis', 'Reflet Médicis', '3 rue Champollion, 75005 Paris', 5,
   'https://www.dulaccinemas.com/cinema/reflet-medicis', 'https://www.dulaccinemas.com/cinema/reflet-medicis',
   true, '2026-11-22', 'dulac', '583'),
  -- [cip] address
  ('nouvel-odeon', 'Nouvel Odéon', '6 rue de l''École de Médecine, 75006 Paris', 6,
   'https://www.nouvelodeon.com/', 'https://www.nouvelodeon.com/horaires/',
   true, '2026-11-22', 'webedia', null),
  -- SCARE only carries its events, full programme on Webedia pending consent.
  ('epee-de-bois', 'Épée de Bois', '100 rue Mouffetard, 75005 Paris', 5,
   'https://www.cine-epeedebois.fr/', 'https://www.cine-epeedebois.fr/horaires/',
   true, '2026-11-22', 'scare', 'Epée de bois'),
  -- [listing] address (5 avenue Mac-Mahon) and site; Webedia per the spike
  ('mac-mahon', 'Mac-Mahon', '5 avenue Mac-Mahon, 75017 Paris', 17,
   'https://www.cinemamacmahon1938.com/', 'https://www.cinemamacmahon1938.com/',
   true, '2026-11-22', 'webedia', null),
  ('espace-saint-michel', 'Espace Saint-Michel', '7 place Saint-Michel, 75005 Paris', 5,
   'https://www.espacesaintmichel.com/', 'https://espacesaintmichel.com/a-laffiche-2/',
   true, '2026-11-22', 'html', null)
on conflict (id) do update set
  name             = excluded.name,
  address          = excluded.address,
  arrondissement   = excluded.arrondissement,
  website_url      = excluded.website_url,
  booking_base_url = excluded.booking_base_url,
  accepts_ugc      = excluded.accepts_ugc,
  ugc_verified_at  = excluded.ugc_verified_at,
  source           = excluded.source,
  source_ref       = excluded.source_ref;
