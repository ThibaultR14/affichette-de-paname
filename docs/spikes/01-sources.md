# Spike #1 - Source des séances et correspondance TMDB

> 2026-11-22. Time-box d'un jour. Prototypes dans `pipeline/spikes/` (jetables). Toutes les mesures datent du dimanche 22/11/2026.

## En bref

- **Source principale : le jeu SCARE « Programmation des cinémas indépendants »** (data.gouv.fr, Licence Ouverte 2.0, API data-fair).
  - Complet pour Le Champo, Saint-André-des-Arts et Le Grand Action.
  - Partiel (événements seulement) pour Le Louxor, Sept Parnassiens et Épée de Bois.
  - Il donne déjà un `tmdb_id`, qui concorde à 100 % avec notre correspondance (107 sur 107).
- **API Dulac** pour Reflet Médicis, et **HTML des sites** pour Filmothèque, Espace Saint-Michel, Cinéma des Cinéastes et Club de l'Étoile (CGU à confirmer).
- **API Webedia** (8 salles) : propre et complète, mais alimentée par l'écosystème Allociné, et la CGU type interdit l'exploitation. **Exclue tant qu'on n'a pas l'accord écrit des salles** (voir l'annexe).
- **Sans source** : Christine Cinéma Club, Écoles Cinéma Club et L'Archipel (billetterie Cotecine bloquée par robots.txt). **MK2 Cultissime** n'est pas une salle : il sort de la liste.
- **TMDB** : 149 correspondances automatiques sur 220 titres réels (68 %). Rapporté aux seuls vrais films, cela fait environ 86 % (149 sur environ 173), avec environ 99 % de précision.

## Tableau salle × source

Légende : ✅ fourni, ◐ partiel ou en texte libre, ✗ absent, ? non vérifié. Les « jours » sont l'horizon observé le 22/11.

| Salle | Source retenue | Jours couverts | VO/VF | Format | Lien résa | CGU / robots | Statut |
|---|---|---|---|---|---|---|---|
| Le Champo | SCARE (cine.boutique non retenu, voir 1 bis) | 7 j et plus (jusqu'au 17/12) | ✅ | ✗ (son seulement) | ✅ `cine.boutique` | Licence Ouverte 2.0 | **V1 (#7)** |
| Saint-André-des-Arts | SCARE | 7 j et plus (jusqu'en juin) | ✅ | ✗ | ✅ `cine.boutique` | Licence Ouverte 2.0 | **V1 (#7)** |
| Le Grand Action | SCARE | 7 j et plus (jusqu'au 03/01) | ✅ | ✗ | ✅ `cine.boutique` | Licence Ouverte 2.0 | **V1 (#7)** |
| Le Louxor | SCARE (événements) · Webedia en attente | ◐ événements · ~13 j via Webedia | ✗ · ✅ | ✗ · ✅ | ✗ · ✅ | Licence Ouverte · CGU Webedia : exploitation interdite sans accord | V1 partiel, accord demandé |
| Sept Parnassiens | SCARE (événements) · Webedia en attente | ◐ · ~18 j | ✗ · ✅ | ✗ · ✅ | ◐ · ✅ | idem | V1 partiel, accord demandé |
| Épée de Bois | SCARE (événements) · Webedia en attente | ◐ · ~18 j | ✗ · ✅ | ✗ · ✅ | ◐ · ✅ | idem | V1 partiel, accord demandé |
| Reflet Médicis | API Dulac `/api/home-bootstrap` | dense jusqu'au mardi, puis quelques séances | ✅ VF/VOST | ✗ (champ vide) | ✅ ticketingcine | robots `Allow: /`, CGU ? | #14, après lecture des CGU |
| Filmothèque du Quartier Latin | HTML (grille de la semaine) | semaine en cours (mer. → mar.) | ? | ◐ texte (« numérique 4K ») | ✗ (lien générique) | robots vide, mentions légales sans clause | #14 |
| Espace Saint-Michel | HTML (fiches film) | semaine en cours | ? | ◐ texte | ✗ (générique) | robots WP classique, CGU ? | #14 |
| Cinéma des Cinéastes | HTML (sélecteur de jours) | 7 j | ◐ | ? | ? | robots vide, CGU ? | #14 (à creuser : séances absentes du HTML serveur) |
| Club de l'Étoile | HTML `/programmation/` | ciné-clubs ponctuels (~10 dates) | ✅ (dans l'URL) | ✗ | ✅ Cotecine | robots `Allow: /` | #14 |
| Le Brady | Webedia, en attente d'accord | ~7 j denses | ✅ | ✅ 4K, Laser | ✅ | CGU Webedia | accord demandé |
| Mac-Mahon | Webedia, en attente d'accord | ~20 j | ✅ | ◐ | ◐ relais Webedia | CGU Webedia | accord demandé |
| Le Saint-Germain-des-Prés | Webedia, en attente d'accord | ~20 j | ✅ | ◐ | ✅ | CGU Webedia | accord demandé |
| Nouvel Odéon | Webedia, en attente d'accord | ~20 j | ✅ | ◐ | ⚠ `tickets.allocine.fr` | CGU Webedia | accord demandé |
| Publicis Cinémas | Webedia, en attente d'accord | ~14 j | ✅ | ✅ 4K, **35mm** | ✅ | CGU Webedia | accord demandé |
| L'Archipel | aucune (site vitrine Cotecine) | ? | ◐ | ? | Cotecine | Cotecine : `Disallow: /*` | sans source, accord demandé |
| Christine Cinéma Club | aucune (iframe Cotecine) | ? | ? | ✗ | Cotecine | Cotecine : `Disallow: /*` | sans source, accord demandé |
| Écoles Cinéma Club | aucune (iframe Cotecine) | ? | ? | ✗ | Cotecine | idem | sans source, accord demandé |
| ~~MK2 Cultissime~~ | - | - | - | - | - | CGU mk2 : réutilisation interdite | retirée : label de ciné-club joué dans plusieurs salles mk2, pas une salle |

Couverture V1 sans accord : **3 salles complètes, 3 partielles, puis 5 de plus via #14**, soit 11 salles sur 19 avec au moins une partie de leur programme.

## Sources étudiées

### 1. SCARE / data.gouv.fr (retenue)
- Jeu « Programmation des cinémas indépendants » du Syndicat des Cinémas d'Art, de Répertoire et d'Essai. Licence Ouverte 2.0, mis à jour chaque jour, alimenté par les systèmes de caisse des salles.
- Accès : API data-fair `https://datacinesindes.fr/data-fair/api/v1/datasets/programmation-cinemas/lines` (filtre `qs=cinecp:75*`, pagination par `next`). Environ 21 000 lignes pour toute la France, 440 pour Paris. Pas de clé.
- Champs utiles : `filmtitle`, `filmdirector`, `filmduration` (min), `showstart`/`showend` (ISO avec décalage), `filmversion` (`VERSION_ORIGINAL`, `VOST`, `VF`, `VERSION_ORIGINAL_LOCAL`…), `filmaudio` (5.1, 7.1, `ST` pour sous-titré), `showurl` (réservation), `showid`, `cinenom`, `evenement`, `_donnees_imdb.id` (**c'est un id TMDB** malgré son nom).
- Mise à jour : `dataUpdatedAt` vers 01 h 15 UTC, soit environ 02 h 15 à Paris.
- Limites :
  - pas de format de projection (35mm, 4K…) ;
  - pas d'année ;
  - Louxor, Sept Parnassiens et Épée de Bois n'y publient que leurs événements ;
  - les séances sans `showstart` existent (Luminor), donc à ignorer.
- Clé de séance : `scare:<cinema_id>:<showid>`. Dans #7 (22/11), `showid` est unique sur les 440 lignes, et les 440 séances d'un second téléchargement ont les mêmes `showid`, titres et horaires. Les deux appels datent du même jour : la stabilité d'un jour sur l'autre se verra aux premiers imports (une clé qui change donnerait une annulation plus une nouvelle séance au même horaire).
- Autres salles parisiennes présentes, hors de notre liste : Le Balzac, L'Entrepôt, Studio des Ursulines, Chaplin Saint-Lambert, Cinq Caumartin, Cinéma du Panthéon, Élysées Lincoln, Luminor. À garder en tête si la liste s'élargit un jour.

### 1 bis. cine.boutique / Ciné Digital (Champo, Saint-André-des-Arts, Grand Action) : non retenu
- La page de réservation charge une SPA. Son API est sur `https://<salle>.cineoffice.fr/vad/` (`shows`, `media/<id>`…), avec un `api_token` publié dans `<meta name="api_token">`.
- Le `robots.txt` de `cineoffice.fr` interdit tout (`User-agent: *` / `Disallow: /`). La seule exception utile est `/public/agenda/agendaexport.php`. C'est un export d'agenda Dolibarr, qui répond « Access denied » sans clé.
- On ne l'utilise donc pas. Ce n'est pas gênant : le SCARE couvre déjà ces trois salles, avec les liens `cine.boutique` par séance.

### 2. cip-paris.fr
Une fiche par salle (adresse, historique, lien vers le site), mais **aucune séance**. Pas d'API. Non retenu, sauf pour vérifier les adresses dans `seed.sql`.

### 3. API Dulac (Reflet Médicis)
- Accès : `GET https://www.dulaccinemas.com/api/home-bootstrap?days=7`. Elle renvoie les 5 salles Dulac (Reflet Médicis, Majestic Passy, Majestic Bastille, L'Arlequin, Escurial) : 220 séances, `truncated: false`.
- Champs : `seances_week[]` (`date` **en UTC sans « Z »**, `version`, `booking_url`, `is_cancelled`, `film_id`), `films_by_id` (`title`, `original_title`, `duration`, `directors`). `year` vaut souvent 0.
- robots.txt : `Allow: /` pour `*`. Les CGU restent à lire avant #14.

### 4. Webedia / BoxOffice (8 salles, en attente d'accord)
- Sites Gatsby, une API sur le domaine de chaque salle :
  - `/api/gatsby-source-boxofficeapi/schedule?theaters={"id":"C0023","timeZone":"Europe/Paris"}&from=…&to=…` ;
  - `/api/gatsby-source-boxofficeapi/movies?ids=…`.
- Données complètes : réalisateur, année, durée, tags de version et de format (`Format.Projection.35mm`…), lien de réservation. Heures locales sans décalage.
- **Pourquoi on attend :**
  - les identifiants de salle sont les codes Allociné, les affiches viennent du CDN Allociné et le Nouvel Odéon réserve via `tickets.allocine.fr` ;
  - la CGU type (lue sur le site du Louxor) n'autorise que l'usage privé non commercial et interdit d'« exploiter quelconque élément du Site » sans autorisation expresse.
- Un seul adaptateur couvrirait les 8 salles. Il ne sera écrit qu'après un accord écrit.

### 5. Sites en HTML
- **Filmothèque** : WordPress, grille de la semaine. **Espace Saint-Michel** : WordPress, fiches film (« Horaires du 18 au 24 Novembre »). Sur le site d'Espace Saint-Michel, j'ai vu un lien de spam dans le pied de page : il faut parser défensivement.
- **Cinéma des Cinéastes** : PHP, sélecteur de 7 jours, mais le détail des séances n'est pas dans le HTML rendu par le serveur. Le chargement est à identifier dans #14.
- **Club de l'Étoile** : Next.js SSR, liens Cotecine qui portent la date et la version (`/reserver/F<film>/D<epoch>/<VO|VF>/<séance>/`). On ne relit que ces liens publiés sur le site de la salle, sans appeler Cotecine.
- **Cotecine** (billetterie de Christine, Écoles, Archipel…) : `robots.txt` = `Disallow: /*`. On ne le collecte pas.

## Correspondance TMDB

Prototype : `pipeline/spikes/tmdb_match_probe.py`.
- **Échantillon** : 220 titres distincts du jeu SCARE (198 parisiens, 22 tirés au hasard ailleurs en France).
- **Référence** : le `tmdb_id` fourni par SCARE pour 108 de ces titres.

### Stratégie testée
1. **Nettoyage du titre.**
   - Retirer :
     - les entités HTML ;
     - `[7/13]` ;
     - les suffixes après ` · `, ` – ` ou ` • ` (« SABRINA · Ciné-club Billy Wilder ») ;
     - `+ débat` ;
     - `4K`, `35mm`, « version restaurée », « avant-première » ;
     - les dates seules.
   - Après un préfixe générique, garder la partie de droite : « Séance spéciale - UN BON PETIT SOLDAT » → « Un bon petit soldat ».
2. **Indice de réalisateur.** Il vient du champ source (« LOSEY Joseph » → « Joseph Losey ») ou, à défaut, du titre lui-même (« … de Michael Mann », « Ciné-club Billy Wilder »).
3. **Recherche** `search/movie` en `language=fr-FR`, sur les 8 premiers résultats. Pour chacun :
   - on calcule une similarité de titre (fr et original, normalisés comme dans `titles.py` de Recsys) ;
   - sur les 5 premiers résultats, on vérifie le réalisateur via `credits`.
4. **Acceptation.**
   - On accepte si le réalisateur concorde avec une similarité de titre ≥ 0,7 (score ≥ 0,75).
   - Sans réalisateur, on accepte avec une similarité ≥ 0,9 sur le premier résultat, **sauf si plusieurs résultats ont exactement le même titre** (remakes, homonymes) : dans ce cas, pas de correspondance.
5. **Repli par réalisateur.** Si aucun candidat n'a été validé par le réalisateur alors qu'on en a un : on cherche `search/person`, puis on parcourt sa filmographie (`movie_credits`, job Director) avec une similarité de titre ≥ 0,8. C'est ce qui trouve *Eva* et *Les Damnés* de Losey, noyés sous les homonymes.

### Résultats

| Mesure | Valeur |
|---|---|
| Titres testés | 220 (198 à Paris) |
| Correspondances automatiques | **149 / 220 = 68 %** (137 validées par le réalisateur, 12 par le titre seul) |
| Titres non trouvés qui ne sont pas des films (ciné-clubs, cycles, concerts, opéra, quiz…) | environ 47 |
| Taux sur les seuls films | environ **86 %** (149 / ~173) |
| Accord avec l'id SCARE quand les deux existent | **107 / 107** |
| Erreurs repérées en relisant les 42 correspondances sans référence SCARE | 2 douteuses, toutes par titre seul (« Tribute to Miles Davis », « L'Homme allumette », qui sont des concerts ou performances) |

### Échecs typiques
- **Événements qui ne sont pas des films** (environ 2/3 des échecs) : « Ciné-club PSYNEMA », « Expositions sur grand écran », « Croissant et Cinéma ! », « Le Ciné-Quiz », retransmissions d'opéra et de ballet, concerts. C'est **le comportement voulu** : ils s'affichent avec le titre de la salle et sans fiche.
- **Homonymes et remakes sans réalisateur** : *Sabrina* (1954 ou 1995), *Tous en scène* (1953 ou 2016). La règle d'ambiguïté refuse de deviner : il faut un override, ou un réalisateur dans la source.
- **Même réalisateur, films voisins** : *Gruffalo, de père en fils* (2026) contre *Le Gruffalo* (2009). Le seuil de similarité à 0,7 corrige ce cas.
- **Films rares absents de TMDB ou sans titre français** : festival grec (*Âmes ciselées*, *Zakros*…), documentaires récents, *Bully* (G. Wetzel).
- **Titre caché dans un intitulé d'événement** : « Ven 20 : ciné bar spleen 2000 : PARANOID PARK, carte blanche à… ». Ce cas passe par un override.
- **Doubles programmes** : « FREDA + BOAT PEOPLE » donne seulement le premier film. C'est acceptable en V1.
- **Pièges de normalisation corrigés pendant le spike** :
  - le point médian `·` et la puce `•` comme séparateurs ;
  - « de la ville » qui ne doit pas être lu comme « de <Réalisateur> » ;
  - les dates dans les titres (« Oslo, 31 août » doit rester intact).

### Stratégie retenue pour `matching.py`
1. `manual_overrides.csv` (toujours prioritaire).
2. **`tmdb_id` fourni par la source** (SCARE `_donnees_imdb.id`), qui concorde à 100 % sur l'échantillon.
3. Cache `title_matches`.
4. Recherche TMDB selon les règles ci-dessus, avec le réalisateur comme signal principal. On ajoute l'année ±1 quand la source la donne (Webedia, Dulac).
5. Sinon `tmdb_id = null`. Le rapport d'import liste ces titres, en séparant ceux qui ressemblent à des événements (sans réalisateur, `evenement` renseigné) pour réduire le bruit.

Les correspondances par titre seul (`method = title`) sont marquées dans le rapport pour une relecture rapide.

## Recommandation et découpage

### #7 - premier adaptateur : `sources/scare.py`
- Couvre Champo, Saint-André-des-Arts et Grand Action, plus les événements de Louxor, Sept Parnassiens et Épée de Bois, d'un seul coup.
- Contenu :
  - `fetch` paginé sur `cinecp:75*` ;
  - table de correspondance `cinenom` → `cinemas.id` dans le seed ;
  - normalisation de `filmversion` + `filmaudio` (`VOST`/`ST` → VOSTFR, `VERSION_ORIGINAL` → VO, `VF`) ;
  - `source_key = scare:<cinema_id>:<showid>` ;
  - `director_hint` ;
  - `tmdb_hint` depuis `_donnees_imdb.id`.
- Fixtures : un extrait réel des lignes parisiennes (sans `filmposter` ni `filmstoryline`, inutiles).
- Ajout au contrat `RawScreening` : `tmdb_hint?` et `event_label?`.
- Dépendance ajoutée pendant le spike : `tzdata` (Windows n'a pas de base de fuseaux, et `Europe/Paris` en a besoin).

### #14 - salles restantes : sous-issues créées
1. **#24 Adaptateur Dulac** (Reflet Médicis) : lire les CGU de dulaccinemas.com avant la mise en service, et gérer la conversion UTC sans « Z ».
2. **#25 Adaptateur HTML Filmothèque** (grille de la semaine, format en texte libre).
3. **#26 Adaptateur HTML Espace Saint-Michel** (fiches film, parsing défensif).
4. **#27 Cinéma des Cinéastes** : trouver d'où viennent les séances, puis écrire l'adaptateur.
5. **#28 Club de l'Étoile** : lire les liens Cotecine publiés sur le site (date et version dans l'URL).
6. **#29 Demande d'accord aux salles** (email en annexe), pour les 8 salles Webedia ainsi que Christine, Écoles et Archipel. À faire quand le site sera public.
7. **#30 Adaptateur Webedia** (8 salles, un seul adaptateur), **bloqué** par #29.
8. **#31 Salles sans source** : badge « programme non disponible, voir le site de la salle » plutôt qu'une salle vide.

### #13 - heure du cron
- SCARE est mis à jour vers 02 h 15 à Paris. Cron quotidien `0 4 * * *` (UTC), soit 05 h en hiver et 06 h en été à Paris.
- Second passage le mercredi `0 13 * * 3` (UTC), soit 14 h ou 15 h à Paris, pour les salles HTML qui publient la nouvelle semaine le mercredi.
- Limite connue : les salles qui ne publient que « la semaine en cours » n'offrent que 3 à 4 jours de visibilité le dimanche. Le badge « programme connu jusqu'au » de la SPEC le montre déjà.

## Annexe - email de demande d'accord (modèle)

> Objet : L'Affichette de Paname - reprise de vos horaires de séances
>
> Bonjour,
>
> Je développe à titre personnel et non commercial « L'Affichette de Paname », un site gratuit qui rassemble sur 7 jours les séances des salles indépendantes parisiennes, en particulier les films de patrimoine. Chaque séance renvoie vers votre site pour la réservation.
>
> Vos conditions d'utilisation demandent une autorisation pour réutiliser les informations de votre site. Accepteriez-vous que le site lise une fois par jour vos horaires de séances (titre, horaire, version, lien de réservation) depuis votre site ? Si vous préférez, une participation au jeu de données ouvert du SCARE (« Programmation des cinémas indépendants », data.gouv.fr) nous conviendrait tout aussi bien.
>
> Merci d'avance,
> [prénom nom] - [lien du site]
