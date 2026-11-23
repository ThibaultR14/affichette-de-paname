# Fixtures

Réponses d'API écrites à la main au format TMDB / PostgREST, réduites aux champs utiles. Les valeurs sont illustratives (pas une copie de TMDB). Les tests n'appellent jamais le réseau.

`scare/page1.json`, `scare/page2.json` : extrait réel du jeu SCARE « Programmation des cinémas indépendants » (data.gouv.fr, Licence Ouverte 2.0) téléchargé le 22/11/2026, 14 lignes parisiennes, sans `filmposter`, `filmstoryline`, `filmtrailer`, `filmcast` ni les champs internes de data-fair. Découpé en deux pages pour tester la pagination (`next`).
