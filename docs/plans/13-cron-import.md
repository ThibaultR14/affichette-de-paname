# Plan #13 - Job planifié GitHub Actions

Issue : #13. Branche : `feat/13-cron-import`, depuis `main`. Dépend de #7 (fait : `affichette.main`).

## Ce qui existe déjà

- `uv run python -m affichette.main [--dry-run] [--cinema <id>]…` : import complet, rapport texte sur la sortie standard (`RunReport.summary()` + `MatchReport.summary()`), code 0 / 1 (une salle en échec) / 2 (config).
- `error_message()` garantit des messages d'erreur sans URL ni clé.
- Horaires décidés (docs/decisions.md, 2026-11-22) : `0 4 * * *` et `0 13 * * 3` (UTC).
- `.github/workflows/ci.yml` : modèle pour `setup-uv` + `uv sync --locked`.

## Fichiers touchés

| Fichier | Changement |
|---|---|
| `.github/workflows/import.yml` | nouveau : cron + `workflow_dispatch` (entrées `dry_run`, `cinemas`) |
| `pipeline/affichette/report.py` | nouveau : résumé Actions + issues GitHub |
| `pipeline/affichette/main.py` | appelle `report.py` après `run()` |
| `pipeline/tests/test_report.py` | nouveau, sans réseau (`FakeSession`) |
| `pipeline/tests/fakes.py` | `FakeSession.post` si absent |
| `docs/architecture.md`, `docs/decisions.md`, `README` éventuel | doc du workflow, des secrets et de la règle d'issue |

## Workflow `import.yml`

- `on.schedule` : les deux crons ; `workflow_dispatch` avec `dry_run` (booléen, défaut false) et `cinemas` (texte, ids séparés par des espaces, vide = toutes).
- `permissions: { contents: read, issues: write }`, `concurrency: import` (pas deux imports en parallèle, sans annuler celui en cours), `timeout-minutes: 30`.
- Étapes : checkout, `astral-sh/setup-uv`, `uv sync --locked --no-dev`, puis `uv run python -m affichette.main`.
- Secrets passés en `env` : `TMDB_READ_TOKEN`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `RESEND_API_KEY` (pas encore lu : les alertes arrivent avec #14), plus `GITHUB_TOKEN`.
- Les entrées manuelles passent par des variables d'environnement, jamais `${{ }}` dans le script (injection).
- Code 1 (salle en échec) → job rouge : GitHub prévient aussi par email.

## `report.py`

1. **Résumé** : `write_step_summary(text)` ajoute le rapport (bloc de code) à `$GITHUB_STEP_SUMMARY` si la variable existe. Le texte reste aussi imprimé dans le log (déjà le cas).
2. **Issues** : `open_failure_issues(report, gh, run_url)`.
   - Une issue **par salle en échec**, titre `import en échec : <cinema_id>`, label `import`. Corps : erreur (`error_message`, déjà sûre), date, lien du run.
   - Sans doublon : on liste les issues ouvertes du label (`GET /repos/{repo}/issues?state=open&labels=import`) ; si une issue a déjà ce titre, on ne crée rien et on logge son numéro.
   - Client `GithubIssues(repo, token, session)` sur `requests` (même style que `Db`), token seulement en en-tête, jamais loggé.
   - Une erreur GitHub ne change pas le code de sortie et n'arrête rien : elle est loggée.
3. Dans `main()` : seulement hors `--dry-run` et si `GITHUB_TOKEN` + `GITHUB_REPOSITORY` sont présents (en local : rien).

### Ajouts après la review

- Run en échec complet (`DbError`/`TmdbError` avant les salles, code 2) : issue `import en échec : global`, sans doublon (`--cinema` invalide : aucune issue).
- Réponses GitHub inattendues (non JSON, champ manquant) et erreur d'écriture du résumé : loggées, jamais levées.
- Étape « Keepalive » (`actions: write`) : contre la désactivation du cron après 60 jours sans commit.

## Tests (`test_report.py`)

- résumé écrit dans le fichier pointé par `GITHUB_STEP_SUMMARY`, rien sans la variable ;
- aucune salle en échec → aucun appel HTTP ;
- salle en échec, pas d'issue ouverte → un POST avec le bon titre, label, corps sans URL ;
- issue déjà ouverte pour la salle → pas de POST ; issue ouverte pour une autre salle → POST ;
- erreur HTTP GitHub → loggée, pas d'exception ;
- `main()` en `--dry-run` n'appelle pas GitHub.

## Hors scope

- Fermer l'issue automatiquement quand la salle repasse (à faire à la main pour l'instant).
- Persister le cache fichier TMDB entre deux runs (`actions/cache`) : `films` et `title_matches` servent déjà de cache en base.
- Envoi des alertes favoris (#14) et canal email admin (question ouverte 4 : on choisit l'issue).
- Créer les secrets dans le repo : à faire à la main (`gh secret set`).
