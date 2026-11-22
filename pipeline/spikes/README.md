# Prototypes du spike #1 (jetables)

Ces scripts ont servi à mesurer les sources et la correspondance TMDB (voir `docs/spikes/01-sources.md`).
Ils ne sont **ni testés ni importés** par le pipeline. pytest ne les collecte pas (`testpaths = ["tests"]`), mais ruff les vérifie.

| Script | Rôle |
|---|---|
| `datagouv_probe.py` | télécharge les lignes parisiennes du jeu SCARE (data.gouv.fr) et affiche la couverture par salle |
| `tmdb_match_probe.py` | correspondance titre → TMDB sur ≥ 100 titres réels, comparée au `tmdb_id` fourni par SCARE |

```
cd pipeline
uv run python spikes/datagouv_probe.py            # --offline pour relire data/datagouv_paris.json
uv run python spikes/tmdb_match_probe.py --limit 220   # --offline-titles pour ne pas retélécharger les titres
```

- Les données téléchargées vont dans `spikes/data/`, qui n'est pas versionné. Les réponses TMDB vont dans `data/cache/spike_tmdb/`, qui n'est pas versionné non plus (CGU TMDB).
- Supprime `data/cache/spike_tmdb/` une fois le spike clos, et au plus tard 6 mois après (CGU TMDB). Rien ne le purge automatiquement.
- Le jeton `TMDB_READ_TOKEN` est lu dans `pipeline/.env` ou, à défaut, dans le `.env` de Recsys. Il n'est jamais affiché.
