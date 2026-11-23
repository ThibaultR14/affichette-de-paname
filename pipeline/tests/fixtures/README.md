# Fixtures

Réponses d'API écrites à la main au format TMDB / PostgREST, réduites aux champs utiles. Les valeurs sont illustratives (pas une copie de TMDB). Les tests n'appellent jamais le réseau.

`scare/page1.json`, `scare/page2.json` : extrait réel du jeu SCARE « Programmation des cinémas indépendants » (data.gouv.fr, Licence Ouverte 2.0) téléchargé le 22/11/2026, 14 lignes parisiennes, sans `filmposter`, `filmstoryline`, `filmtrailer`, `filmcast` ni les champs internes de data-fair. Découpé en deux pages pour tester la pagination (`next`).

`dulac/home-bootstrap.json` : extrait réel de l'API Dulac (`/api/home-bootstrap?days=7`) du 22/11/2026, réduit à 15 séances du Reflet Médicis et 2 d'autres salles Dulac, avec les fiches film sans affiche, synopsis ni casting, et sans les champs d'accessibilité. Gardés tels quels : le doublon *Mysterious Skin* (séances 18652 et 18657), l'avant-première et la « first session ». Modifiés pour les tests : 19568 annulée (`is_cancelled: true`) ; 19588 déplacée au 27/11 23:30 UTC (28/11 à Paris) ; 19612 sans `booking_url` ; 19609 au 21/11 22:30 UTC et 19544 au 28/11 23:15 UTC (hors fenêtre).

`filmotheque/` : pages réelles de lafilmotheque.fr du 23/11/2026, sans `<head>`, scripts, styles, SVG, images ni cases vides des grilles. `home.html` : accueil (cartes de la semaine du 18 au 24/11 et grilles des deux semaines, 44 films). `taxi-driver.html`, `ohong-village.html`, `adieu-philippine.html` : `<main>` des fiches. On y trouve *Taxi Driver* en « numérique 4K » sur une seule salle ; *Ohong Village* sur les deux salles, avec la séance du mercredi 18 à 19H30 listée deux fois ; *Adieu Philippine* seulement en « Prochainement », le vendredi 27. Non modifiées.
