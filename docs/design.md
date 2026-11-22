# Design - L'Affichette de Paname

> Reprend la direction « C · Fanzine » de Recsys_movie (`docs/design-system.md` v0.3), adaptée aux séances. Maquette de référence : `docs/reference/maquette-fanzine-recsys.html` (celle de Recsys, pas encore celle de ce site).
> TODO tranchés dans l'issue #2 (plan : `docs/plans/2-design-system.md`). Tous les composants de base sont visibles sur `/styleguide`.

## Esprit

**Une affichette de ciné-club photocopiée, scotchée à l'entrée de la salle.** Minimaliste et artisanale : on ne vend rien, on partage des séances.

- Ce qu'on veut : simple, honnête, un peu drôle. Les affiches de films sont la seule vraie couleur.
- Ce qu'on refuse : le look startup (dégradés, gros boutons marketing, compteurs d'utilisateurs), l'**orange sur fond sombre**, les emoji dans l'interface, un ton commercial ou snob.

## Couleurs (jetons)

| Jeton | Clair | Sombre | Usage |
|---|---|---|---|
| `paper` | `#FBFAF7` | `#16171B` | Fond |
| `surface` | `#FFFFFF` | `#23242A` | Cartes, champs, boutons |
| `ink` | `#1B1B1B` | `#ECE8DF` | Texte, bordures de composants |
| `muted` | `#555049` | `#ADA79C` | Texte secondaire (réalisateur, année, salle) |
| `rule` | `#B9B4AA` | `#5A574F` | Filets décoratifs seulement |
| `pen` | `#2546B8` | `#8EA6FF` | Accent unique : annotations, jour sélectionné, favori |
| `tape` | `rgba(214,208,196,.75)` | `rgba(214,208,196,.35)` | Scotch des affiches |

- Un seul accent : le stylo bleu.
- Contraste AA vérifié par un test (`contrast.test.ts`, repris de Recsys), dans les deux thèmes.
- **Thème par défaut** : celui du système (`prefers-color-scheme`), clair si le système ne dit rien. La bascule « passer en sombre » / « passer en clair » est mémorisée dans le navigateur (clé `affichette-theme`, seule donnée stockée). Un script dans `index.html` applique le thème avant le premier rendu. Jetons dans `web/src/styles/tokens.css`.
- **Pastilles de séance** (`vo`, `vf`, `35mm`, `70mm`, `4k`, `ugc`) : minuscules, 13 px gras, bordure 1,5 px encre, coins 3 px, sans fond ni couleur. `ugc` se met à côté du nom de la salle, les autres à côté de l'heure. Les pointillés restent réservés aux filtres actifs.

## Typographie

| Rôle | Police | Taille |
|---|---|---|
| Interface | Courier Prime 400/700 (auto-hébergée, `@fontsource/courier-prime`) | 13-18 px |
| Titres | Courier Prime 400, minuscules | `clamp(24px, 3.4vw, 36px)` |
| Heures de séance | Courier Prime 700, chiffres tabulaires | 16-18 px |
| Annotations | Caveat 500/700 (`@fontsource/caveat`), stylo bleu, inclinées de −1,5° à −4° | 20-24 px |

Aucune requête vers Google Fonts.

## Espacements

- Échelle : 4, 8, 12, 16, 24, 32, 48, 56 px.
- Conteneur de 1 200 px au plus, marges latérales de 16 px sur mobile et 24 px au-delà. Texte courant à ~65 caractères.
- Cibles tactiles de 44 px minimum (heures de séance, puces de filtre, jours).

## Composants de base

### Bandeau des 7 jours
- Rangée défilante de 7 puces : « auj. », « dem. », puis « mer. 25 »… Le jour courant est **souligné au stylo bleu** (trait ondulé, comme dans Recsys).
- Sous chaque jour vide : rien de spécial. La couverture est indiquée par salle (voir plus bas).

### Carte film (« photo scotchée »)
- Reprend la carte de Recsys : surface, scotch en haut, légère rotation (±1,8°), affiche 2:3.
- Dessous :
  - titre en gras ;
  - « réalisateur, année · durée » en `muted` ;
  - liste des séances du jour, groupées par salle : nom de la salle, puis les heures (« 14:00 → 16:05 »), chacune avec ses pastilles (`VO`, `35mm`). Chaque heure est un lien vers la réservation.
- Cœur favori en haut à droite, sur l'étiquette « ✱ » de Recsys.
- **Sous 640 px : ligne compacte** : vignette 2:3 de 80 px à gauche (scotch gardé, sans rotation), titre et méta à droite, séances en dessous sur toute la largeur. **À partir de 640 px : carte photo** inclinée (±1,8° au plus), dans une grille `minmax(260px, 1fr)`. Les séances prennent de la place : une affiche pleine largeur ferait défiler deux écrans par film.
- L'heure de fin n'apparaît que si la durée TMDB est connue. Les heures sont des liens vers la réservation (nouvel onglet).
- Séance sans fiche TMDB : carte sans affiche (cadre en pointillés), titre de la salle, annotation Caveat « (on n'a pas trouvé ce film, désolé) ».

### Filtres
- Puces à bascule, comme le panneau « affiner » de Recsys : enfoncée = encre pleine, texte papier.
- Filtres : salles, « carte UGC », « patrimoine (+ de 20 ans) ».
- Les filtres actifs apparaissent en puces pointillées « × louxor », avec un lien « tout effacer ».
- Le panneau se déplie sous la barre, sans modale.

### Couverture d'une salle
- Ligne en `muted` sous le nom de la salle : « programme connu jusqu'au jeu. 27 · mis à jour il y a 3 h ». Si le dernier import a échoué : annotation Caveat « (on n'a pas pu mettre à jour cette salle aujourd'hui) ».

### Boutons et liens
- Bouton principal : surface, bordure 2 px encre, coins 3 px, gras 16 px, hauteur 48 px.
- Liens soulignés, en stylo bleu au survol.

## Ton des textes

- Tutoiement, minuscules, phrases courtes, un peu d'humour, jamais snob. On parle cinéma.
- Exemples (à valider) :
  - accueil : « salut. voilà ce qui passe dans les petites salles de paname cette semaine. »
  - jour vide après filtres : « rien ce jour-là avec ces filtres. essaie sans « patrimoine » ? »
  - favoris vides : « t'attends quel film ? cherche-le, on te prévient quand il passe. »
  - email d'alerte : objet « « le mépris » passe cette semaine », puis le corps « au champo, jeudi 20:30 (vo, 35mm). »
  - connexion : « on t'envoie un lien par mail, pas de mot de passe. »
- Mentions obligatoires (ne pas reformuler) : « This product uses the TMDB API but is not endorsed or certified by TMDB. », plus le logo TMDB sur la page « à propos ».
- Pied de page : TODO. Il précisera que le site est indépendant, sans lien avec les salles ni avec le compte Instagram @movieinparis.
