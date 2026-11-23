# Journal des décisions

## 2026-11-23 - Routeur maison, fiche film sans filtres (#11)
- Contexte : la fiche `/film/:tmdbId` est la première vraie route. Le site en aura quatre (`/`, `/film/:id`, `/favoris`, `/connexion`).
- Décision :
  - un routeur de ~70 lignes (`lib/router.ts`) : `pushState` + `popstate` et un `Link` qui garde un vrai `href`. L'état des filtres reste dans la query string, géré par les hooks existants.
  - la fiche montre toutes les séances des 7 jours, toutes salles, sans appliquer les filtres de l'accueil (on veut tout voir d'un film précis). Le retour vers l'accueil passe par l'historique, qui garde le jour et les filtres.
  - un film absent de `films` ou un id mal formé → page 404 propre (statut HTTP 200, SPA). Tout chemin inconnu → la même page, au lieu de l'accueil.
- Alternatives écartées : react-router (une dépendance et un modèle de données pour 4 routes) ; reporter les filtres sur la fiche (un film masqué par patrimoine resterait introuvable depuis son propre lien) ; un `404.html` sur Pages (couperait le routage SPA).

## 2026-11-23 - Filtres : côté client, patrimoine écrit seulement quand il est coupé
- Contexte : issue #10, filtres salles / carte UGC / patrimoine, combinables et partageables par l'URL.
- Décision :
  - le filtrage se fait dans le navigateur, sur les cartes du jour déjà chargées : changer un filtre ne relance pas de requête (une journée tient sous les 1 000 lignes) ;
  - `?salles=champo,louxor&ugc=1&patrimoine=0` : seules les valeurs qui diffèrent du défaut sont écrites. Patrimoine étant actif par défaut, il n'apparaît que sous la forme `patrimoine=0` ;
  - écriture par `replaceState`, comme le jour ;
  - « tout effacer » coupe aussi patrimoine : on voit toute la programmation du jour ;
  - les ids de salle inconnus d'un lien partagé sont ignorés et retirés de l'URL une fois la liste des salles chargée.
- Alternatives écartées : filtrer dans la requête PostgREST (une requête par clic, et le filtre patrimoine doit garder les séances sans année) ; « tout effacer » qui remet les défauts (le bouton ne ferait rien sur une URL nue).

## 2026-11-23 - Jour dans l'URL : `replaceState`, date toujours écrite
- Contexte : issue #9, bandeau 7 jours et `?jour=` partageable.
- Décision :
  - un clic sur un jour remplace l'entrée d'historique (`replaceState`) au lieu d'en ajouter une : « retour » quitte la page au lieu de rejouer les jours cliqués ;
  - un clic écrit la date, même sur « auj. » : un lien partagé après un choix désigne un jour précis. À l'arrivée sur `/`, l'URL reste sans `jour` (on ne réécrit pas l'adresse d'une simple visite) : ce lien-là veut dire « aujourd'hui, quel que soit le jour où on l'ouvre » ;
  - un `?jour=` absent, mal formé, passé ou au-delà des 7 jours donne aujourd'hui, et il est retiré de l'URL pour qu'elle dise ce qu'on voit ;
  - `today` est recalculé à minuit Paris et au retour sur l'onglet, sinon une page laissée ouverte la nuit chercherait un jour passé.
- Alternatives écartées : `pushState` (sept entrées d'historique pour parcourir la semaine) ; omettre `jour` quand on clique sur « auj. » (un lien envoyé le soir montrerait un autre jour le lendemain) ; écrire `jour` dès l'arrivée (l'adresse change sans action de l'utilisateur) ; un routeur dès maintenant (il arrive avec la fiche film, #11).

## 2026-11-23 - Vue du jour : séances commencées masquées, regroupement côté client
- Contexte : issue #8, accueil par film pour un jour donné.
- Décision :
  - pour aujourd'hui, on ne montre que les séances qui n'ont pas commencé (le site sert surtout dans la rue) ;
  - une requête PostgREST avec jointures, regroupée par film dans le navigateur ; les séances sans fiche TMDB sont regroupées par titre brut (casse et espaces ignorés), jamais fusionnées avec un film trouvé ;
  - si la requête renvoie 1 000 lignes (`max_rows` de Supabase), on affiche une erreur plutôt qu'un jour tronqué sans le dire ;
  - cartes triées par titre, inclinaison dérivée de la clé du film (stable d'un rendu à l'autre) ;
  - sans `booking_url` ni `website_url`, l'heure s'affiche sans lien.
- Alternatives écartées : garder toutes les séances du jour (il faut faire défiler les séances passées) ; une vue SQL ou une RPC par film (une migration de plus pour un regroupement de quelques centaines de lignes) ; trier par première séance (l'ordre change au fil de la journée, plus dur à parcourir).

## 2026-11-22 - Import SCARE : fenêtre de 7 jours, VF pour les films français, 0 ligne = panne
- Contexte : issue #7, premier import de bout en bout (`sources/scare.py`, `upsert.py`, `main.py`).
- Décision :
  - on importe seulement `[aujourd'hui 00:00 Paris, +7 jours[`, comme la SPEC. Les annulations ne visent que la partie future de cette fenêtre, et `coverage_until` = date de la dernière séance importée (inchangée pour une salle sans séance cette semaine) ;
  - `VERSION_ORIGINAL_LOCAL` (films français dans leur langue : *Huit femmes*, *Intouchables*) et `VERSION_LOCAL` → `VF`. `ST` dans `filmaudio` fait passer une VO en VOSTFR, mais pas une VF (`VF` + `ST,OCAP` = sous-titres pour sourds) ;
  - un jeu SCARE sans aucune ligne parisienne est une panne : toutes les salles SCARE passent en échec et rien n'est annulé ;
  - une salle dont le `cinenom` a disparu du jeu (renommée, retirée) est en échec, pour la même raison ;
  - pas de transaction : upsert, annulations et état de la salle sont trois appels PostgREST. Un échec après l'upsert est signalé « écriture partielle » dans `import_runs.error`, et l'import suivant complète (étapes idempotentes). Une fonction SQL `rpc` transactionnelle reste possible si ce cas se produit vraiment ;
  - pas de `showurl` → `booking_url = null`, le front retombe sur `website_url` de la salle ;
  - un `tmdb_id` fourni par la source mais inconnu de TMDB (404) n'est pas écrit sur la séance (clé étrangère vers `films`) ;
  - `--dry-run` lit la vraie base et n'écrit rien (`DryRunDb`), pour voir l'effet d'un import sans risque ;
  - `import_runs` : une ligne par salle, écrite en fin de traitement de la salle.
- Alternatives écartées : importer tout l'horizon SCARE (jusqu'en juin pour Saint-André : des centaines de recherches TMDB pour des séances que personne ne verra avant des semaines) ; `VERSION_ORIGINAL_LOCAL` en VO (exact mais trompeur à côté des films étrangers en VO) ; recopier `website_url` dans `booking_url` (donnée dupliquée qu'il faudrait corriger à deux endroits) ; un `--dry-run` sans base (il faudrait reconstruire salles et séances existantes, et le calcul des annulations ne serait plus le vrai).

## 2026-11-22 - Correspondance TMDB : seuils du spike, réalisateur tolérant, cache par salle
- Contexte : issue #6, `matching.py`. Le seuil devait être réglé sur l'échantillon du spike (220 titres SCARE), avec un taux au moins égal à celui mesuré (149/220).
- Décision :
  - seuils du spike conservés : réalisateur + similarité de titre ≥ 0,7, titre seul ≥ 0,9 sur le premier résultat, refus si plusieurs homonymes à ≥ 0,95, repli par filmographie à ≥ 0,8 ;
  - nom de réalisateur comparé mot à mot avec une similarité ≥ 0,85 : TMDB écrit maintenant « Mikheil Kalatozishvili » là où SCARE donne « Mikhail Kalatazov ». On tient compte de tous les réalisateurs listés par la source, pas seulement du premier ;
  - mesure (`scripts/eval_matching.py`, sans l'id SCARE ni overrides) : **149/220 (67,7 %), accord SCARE 107/107**, mêmes films que le spike sur les 220 titres. Un titre seul à 0,85 donnerait 151/220 (deux films justes de plus : *Shaun le mouton*, *Les Zazous*), mais il accepterait un premier résultat dont le réalisateur ne concorde pas, ce qui est le cas d'un remake. On garde 0,9 et on corrige ces cas par override ;
  - cache `title_matches` par (titre normalisé, salle, année), car le réalisateur fourni change d'une source à l'autre. Trouvé réutilisé 30 jours, non trouvé 7 jours. Ni les overrides ni l'id de la source n'y sont écrits ;
  - `title_matches.method` passe de `exact/fuzzy/override/none` à `override/source/director/title/none`, et une colonne `reason` garde la cause d'un « non trouvé » pour le rapport des imports suivants (migration, table vide) ;
  - `manual_overrides.csv` : `title,cinema_id,tmdb_id,note`, titre brut accepté (normalisé au chargement), salle vide = toutes, `tmdb_id` vide = « pas un film ».
- Alternatives écartées : seuil à 0,85 (voir plus haut) ; cache partagé entre salles (un même titre sans réalisateur dans une salle et avec réalisateur dans une autre donnerait le même résultat) ; recherche TMDB filtrée par année dès le premier appel (le paramètre `year` est strict, et l'année d'une copie restaurée diffère souvent d'un an).

## 2026-11-22 - Client TMDB : Bearer seul, écriture en base par PostgREST
- Contexte : issue #5, portage du client TMDB de Recsys et remplissage de `films`.
- Décision :
  - jeton Bearer `TMDB_READ_TOKEN` uniquement : le repli de Recsys sur la clé v3 `api_key` est retiré, car elle passe dans l'URL et finirait dans un log ou une trace d'exception ;
  - les erreurs `requests` ne sont jamais recopiées (leur message contient l'URL) : on garde le type et le chemin d'API ;
  - écriture par un client PostgREST minimal (`affichette/db.py`, `requests`, `Prefer: resolution=merge-duplicates`) ;
  - `films.tmdb_fetched_at` = date de l'appel TMDB (celle du cache), pour que le refresh à 30 jours et la purge à 6 mois en base reposent sur l'âge réel de la donnée.
- Alternatives écartées : le paquet `supabase` (dépendances lourdes pour quelques upserts) ; `tmdb_fetched_at = now()` à l'écriture (une donnée tirée d'un cache de 29 jours paraîtrait neuve).

## 2026-11-22 - Front : Cloudflare Pages par l'intégration Git
- Contexte : issue #4. Il faut un déploiement auto depuis `main` et une preview par PR.
- Décision : projet Pages connecté au repo GitHub (build par Cloudflare, root `web`, sortie `dist`). Les deux variables publiques `VITE_*` sont saisies dans le dashboard. Node fixé par `web/.nvmrc`. Le client Supabase vaut `null` sans variables, pour qu'une preview mal configurée affiche une erreur au lieu d'une page blanche.
- Alternatives écartées : `wrangler pages deploy` dans une GitHub Action (il faut un jeton Cloudflare dans les secrets et un workflow à maintenir pour le même résultat).

## 2026-11-22 - Base : tests RLS en pgTAP, UGC vérifié, seed idempotent
- Contexte : issue #3. La migration n'avait jamais tourné, et il fallait prouver la RLS.
- Décision :
  - tests pgTAP dans `supabase/tests/`, joués par `supabase test db` sur la stack locale et dans un job CI `supabase` qui part d'une base vierge ;
  - UGC Illimité : la liste officielle UGC (22/11/2026) inclut toutes nos salles sauf le Club de l'Étoile. L'hypothèse de la SPEC (4 salles exclues) était fausse ;
  - `seed.sql` en `on conflict do update`, qu'on peut rejouer sur le projet cloud ; les adresses trouvées seulement sur cip-paris.fr ou un annuaire sont marquées dans le fichier.
- Alternatives écartées : un test RLS en Python avec la clé anon (il faut une base qui tourne et des clés dans les tests du pipeline, qui doivent rester sans réseau) ; un seed par `insert` simple (casse au second passage).

## 2026-11-22 - Design system : thème du système, CSS sans Tailwind
- Contexte : issue #2, TODO de `docs/design.md`.
- Décision :
  - thème par défaut = préférence du système, clair à défaut, avec une bascule mémorisée (`affichette-theme`) ;
  - pastilles sans couleur (bordure encre), `ugc` à côté du nom de la salle ;
  - carte film en ligne compacte sous 640 px, carte photo au-delà ;
  - CSS classique : jetons en propriétés CSS (`web/src/styles/tokens.css`) et un `.css` par composant ;
  - polices auto-hébergées via `@fontsource`, vérifiées par `fonts.test.ts` ; contraste AA vérifié par `contrast.test.ts` ;
  - `/styleguide` servi aussi en production, chargé à la demande, sans routeur pour l'instant.
- Alternatives écartées : clair forcé (éblouit le soir) ; sombre par défaut comme Recsys (usage en extérieur) ; Tailwind comme Recsys (une dépendance et une config de plus pour une dizaine de composants) ; carte photo sur mobile (trop haute).

## 2026-11-22 - Sources des séances : SCARE d'abord, une source par salle ensuite
- Contexte : spike #1 (`docs/spikes/01-sources.md`). Aucune source unique ne couvre les salles, et cip-paris.fr ne publie pas de séances.
- Décision :
  - Source principale : le jeu ouvert SCARE « Programmation des cinémas indépendants » (data.gouv.fr, Licence Ouverte 2.0). Il couvre complètement Champo, Saint-André-des-Arts et Grand Action, et les événements de Louxor, Sept Parnassiens et Épée de Bois. C'est le premier adaptateur (#7).
  - Ensuite, une source par salle : API Dulac (Reflet Médicis), HTML des sites de Filmothèque, Espace Saint-Michel, Cinéma des Cinéastes et Club de l'Étoile. Les CGU sont à confirmer dans #14.
  - Le `tmdb_id` fourni par SCARE sert d'indice de correspondance, juste après `manual_overrides.csv` (accord de 107 sur 107 avec notre recherche).
- Alternatives écartées : cip-paris.fr (pas de séances) ; billetterie Cotecine (robots.txt `Disallow: /*`).

## 2026-11-22 - API Webedia exclue sans accord écrit des salles
- Contexte : 8 salles (Louxor, Brady, Mac-Mahon, Épée de Bois, Saint-Germain-des-Prés, Nouvel Odéon, Publicis, Sept Parnassiens) exposent une API JSON complète sur leur domaine. Elle est fournie par Webedia et liée à Allociné (codes salle Allociné, CDN acsta.net, réservation via tickets.allocine.fr pour le Nouvel Odéon). La CGU type interdit d'exploiter le site sans autorisation expresse.
- Décision : on ne la collecte pas tant qu'on n'a pas l'accord écrit de la salle. Un email de demande est préparé (annexe du spike) et propose aussi de rejoindre le jeu SCARE. L'adaptateur Webedia est une sous-issue bloquée de #14.
- Alternatives écartées : l'utiliser en « usage prudent » (zone grise vis-à-vis des CGU et de la règle « pas d'Allociné ») ; l'exclure définitivement (on perdrait la meilleure source si les salles acceptent).

## 2026-11-22 - MK2 Cultissime retiré, salles sans source documentées
- Contexte : « MK2 Cultissime » est un label de ciné-club mk2 joué dans plusieurs salles mk2, pas une salle, et les CGU mk2 interdisent la réutilisation. Christine Cinéma Club, Écoles Cinéma Club et L'Archipel n'ont pas d'autre source que la billetterie Cotecine, bloquée par robots.txt.
- Décision : MK2 Cultissime sort de la liste (19 salles). Christine, Écoles et Archipel restent dans la liste, marquées sans source, et sont incluses dans la demande d'accord.
- Alternatives écartées : les garder sans séances et sans explication.

## 2026-11-22 - Cron : 04 h UTC chaque jour, plus 13 h UTC le mercredi
- Contexte : SCARE est mis à jour vers 02 h 15 à Paris. Les salles en HTML publient leur nouvelle semaine le mercredi.
- Décision : `0 4 * * *` et `0 13 * * 3` (UTC) pour #13.
- Alternatives écartées : un horaire fixe à l'heure de Paris (le cron GitHub ne connaît que l'UTC, et une heure d'écart l'été ne change rien ici).

## 2026-11-22 - Lint front : oxlint plutôt qu'ESLint
- Contexte : le template Vite actuel (Vite 8) génère une config oxlint et non plus ESLint.
- Décision : garder oxlint, avec les plugins react, typescript et oxc, plus Prettier pour le format. `npm run lint` lance les deux, et `npm run typecheck` lance `tsc -b`.
- Alternatives écartées : remettre ESLint (plus lent, config à maintenir, rien de nécessaire en plus).

## 2026-11-22 - Vitest lancé via un script wrapper (Windows)
- Contexte : quand le dossier est ouvert en `c:\…` (lettre de lecteur en minuscule, ce que fait VS Code), Vitest 5.1 charge deux copies de son runner. Toutes les suites échouent alors avec `Cannot read properties of undefined (reading 'config')`. Un projet vide lancé depuis `C:\` passe.
- Décision : `npm test` lance `web/scripts/vitest.mjs`, qui relance Vitest depuis le même chemin avec la lettre de lecteur en majuscule. Sans effet sur Linux (CI).
- Alternatives écartées : `root` ou `process.chdir` dans `vite.config.ts` (testé, sans effet, car le cwd est lu avant la config).

## 2026-11-22 - Nom : « L'Affichette de Paname »
- Contexte : « movieinparis » est le nom d'un compte Instagram existant, que je ne gère pas, et le reprendre prêterait à confusion.
- Décision : le site s'appelle « L'Affichette de Paname ». Le repo s'appelle `affichette-de-paname`.
- Alternatives écartées : « movieinparis » (confusion avec le compte Insta).

## 2026-11-22 - Design repris de Recsys_movie (direction « fanzine »)
- Contexte : il faut une direction visuelle, et Recsys_movie en a déjà une, validée.
- Décision : reprendre les jetons (couleurs, typo Courier Prime + Caveat), le ton et les principes de la direction « C · Fanzine », adaptés aux séances. Voir `docs/design.md`.
- Alternatives écartées : une nouvelle direction (plus de temps de design) ; s'inspirer du compte Insta (risque de copier une identité qui n'est pas la mienne).

## 2026-11-22 - Correspondance TMDB : affichage brut + overrides CSV
- Contexte : des titres de séance ne trouveront pas de film TMDB (cycles, courts, titres ambigus).
- Décision : la séance est affichée avec le titre de la salle, sans fiche. Un `pipeline/manual_overrides.csv` versionné corrige à la main, et un rapport des non-correspondances est produit à chaque import.
- Alternatives écartées : une page admin (trop d'UI et de droits pour la V1) ; masquer ces séances (perte d'information).

## 2026-11-22 - Alertes : dès détection, re-alerte après 30 jours d'absence
- Contexte : l'alerte doit être utile sans spammer.
- Décision : l'email part dès qu'un import trouve une séance d'un favori, groupé par utilisateur. Une nouvelle alerte ne part que si le film revient après 30 jours sans séance.
- Alternatives écartées : un récap hebdo (rate les films ajoutés en cours de semaine) ; une alerte par nouvelle salle (trop d'emails) ; un favori consommé après l'alerte.

## 2026-11-22 - Toute la programmation importée, filtre patrimoine par défaut (plus de 20 ans)
- Contexte : plusieurs salles passent aussi des films récents.
- Décision : on importe tout. Le filtre « patrimoine » (année TMDB ≤ année courante − 20) est actif par défaut, et les séances sans année restent visibles.
- Alternatives écartées : patrimoine uniquement à l'import (perte d'info, dilemme pour les films sans année) ; un seuil de 30 ans ; un curseur réglable.

## 2026-11-22 - Historique des séances conservé
- Contexte : la règle de re-alerte a besoin de savoir quand un film est passé pour la dernière fois, et la V3 pourra exploiter les données.
- Décision : les séances passées restent en base (faible volume). Les annulations sont marquées par `cancelled_at`.
- Alternatives écartées : purger après la date (il faudrait une table de dernière programmation par film).

## 2026-11-22 - Favoris = n'importe quel film TMDB
- Contexte : l'alerte apporte surtout quelque chose pour un film qu'on attend et qui n'est pas encore programmé.
- Décision : recherche TMDB intégrée au site, via une Edge Function Supabase pour que le jeton ne soit pas exposé.
- Alternatives écartées : favoris limités aux films programmés.

## 2026-11-22 - Auth par magic link
- Contexte : on envoie des emails, donc l'adresse doit être vérifiée, et je veux éviter de gérer des mots de passe.
- Décision : Supabase Auth en magic link uniquement.
- Alternatives écartées : email + mot de passe (réinitialisation, vérification) ; Google OAuth (configuration en plus, pas nécessaire en V1).

## 2026-11-22 - Stack : Supabase + React/Vite + job Python sur GitHub Actions
- Contexte : projet perso avec un budget d'hébergement minimal, mais il faut des comptes, des favoris et des emails, donc un site 100 % statique ne suffit pas. Le client TMDB existe déjà en Python (Recsys_movie).
- Décision :
  - front React + Vite + TS sur Cloudflare Pages ;
  - Supabase (Postgres, PostgREST, RLS, Auth) en free tier ;
  - job d'import Python 3.12 + uv, en cron sur GitHub Actions (repo public, minutes illimitées) ;
  - emails via Resend (free tier).
  - Coût : 0 €.
- Alternatives écartées : FastAPI + Postgres sur un VPS (~4 €/mois, serveur et auth à maintenir) ; séances en JSON statique + Supabase pour les comptes seulement (deux sources de vérité).
