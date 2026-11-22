from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from affichette.matching import (
    OVERRIDES_CSV,
    CachedMatch,
    DbTitleMatchStore,
    Match,
    Matcher,
    MatchQuery,
    TitleMatchStore,
    clean_director,
    clean_title,
    director_hint,
    load_overrides,
    same_director,
    title_only_score,
)
from affichette.tmdb import Cached

NOW = datetime(2026, 11, 22, 4, 0, tzinfo=UTC)


def film(tmdb_id, title, year, original=None):
    return {
        "id": tmdb_id,
        "title": title,
        "original_title": original or title,
        "release_date": f"{year}-01-01" if year else None,
    }


@dataclass
class FakeTmdb:
    """Hand-written TMDB: searches by query, directors by id, filmographies by person id."""

    searches: dict = field(default_factory=dict)  # query -> [film] (year searches: (query, y))
    directors: dict = field(default_factory=dict)  # tmdb_id -> [names]
    people: dict = field(default_factory=dict)  # name -> [{id, known_for_department}]
    filmographies: dict = field(default_factory=dict)  # person id -> [film]
    calls: list = field(default_factory=list)

    def search_movie(self, query, year=None):
        self.calls.append(("search", query, year))
        return self.searches.get((query, year) if year else query, [])

    def movie(self, tmdb_id):
        self.calls.append(("movie", tmdb_id))
        names = self.directors.get(tmdb_id)
        return Cached(None if names is None else {"directors": names}, NOW)

    def search_person(self, name):
        self.calls.append(("person", name))
        return self.people.get(name, [])

    def person_directing(self, person_id):
        self.calls.append(("credits", person_id))
        return self.filmographies.get(person_id, [])


def matcher(tmdb=None, overrides=None, store=None, **kw):
    return Matcher(tmdb or FakeTmdb(), overrides=overrides or {}, store=store, now=NOW, **kw)


# --- cleaning -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("SABRINA · Ciné-club Billy Wilder [7/13]", "Sabrina"),
        ("Séance spéciale - UN BON PETIT SOLDAT", "Un Bon Petit Soldat"),
        ("SOFILM CINÉ-CLUB #2 · Miami Vice de Michael Mann", "Miami Vice"),
        ("LE MÉPRIS + débat avec l'équipe", "Le Mépris"),
        ("Vertigo (VOSTFR) 4K", "Vertigo"),
        ("La Ferme, de Louis Clichy", "La Ferme"),
        ("Oslo, 31 août", "Oslo, 31 août"),
        ("Le Voleur de la ville", "Le Voleur de la ville"),
        ("Avant-première : Les Fantômes", "Les Fantômes"),
    ],
)
def test_clean_title(raw, clean):
    assert clean_title(raw) == clean


def test_director_hint_from_title():
    assert director_hint("SOFILM CINÉ-CLUB #2 · Miami Vice de Michael Mann") == "Michael Mann"
    assert director_hint("SABRINA · Ciné-club Billy Wilder [7/13]") == "Billy Wilder"
    assert director_hint("Le Voleur de la ville") is None


def test_clean_director():
    assert clean_director("LOSEY Joseph") == "Joseph Losey"
    assert clean_director("Jean Renoir, Marcel Carné") == "Jean Renoir"
    assert clean_director("Agnès Varda") == "Agnès Varda"


def test_same_director_allows_spelling_variants_only():
    assert same_director({"mikhail", "kalatazov"}, {"mikheil", "kalatozishvili"}, 0.85)
    assert not same_director({"jacques", "demy"}, {"jean", "renoir"}, 0.85)


def test_title_only_score_never_passes_with_a_wrong_director():
    assert title_only_score(1.0, 0, director_known=False) == pytest.approx(0.95)
    assert title_only_score(1.0, 0, director_known=True) < 0.9
    assert title_only_score(1.0, 1, director_known=False) < 0.9


# --- resolution order ---------------------------------------------------------------------------


def test_override_wins_and_skips_tmdb():
    tmdb = FakeTmdb()
    m = matcher(tmdb, overrides={("eva", None): 111})
    assert m.match(MatchQuery("EVA", "champo", tmdb_hint=999)) == Match(
        111, "override", 1.0, "override"
    )
    assert tmdb.calls == []


def test_cinema_override_beats_global_override():
    m = matcher(overrides={("sabrina", None): 1, ("sabrina", "louxor"): 2})
    assert m.match(MatchQuery("Sabrina", "louxor")).tmdb_id == 2
    assert m.match(MatchQuery("Sabrina", "champo")).tmdb_id == 1


def test_override_matches_raw_or_cleaned_title():
    m = matcher(overrides={("paranoid park", None): 8337})
    assert m.match(MatchQuery("PARANOID PARK + rencontre", "louxor")).tmdb_id == 8337


def test_empty_override_forces_no_match():
    tmdb = FakeTmdb(searches={"Le Ciné-Quiz": [film(5, "Le Ciné-Quiz", 2020)]})
    result = matcher(tmdb, overrides={("le cine quiz", None): None}).match(
        MatchQuery("Le Ciné-Quiz")
    )
    assert result.tmdb_id is None and result.reason == "override"
    assert tmdb.calls == []


def test_source_hint_before_cache_and_search():
    tmdb = FakeTmdb()
    store = TitleMatchStore({("eva", "champo", None): CachedMatch(1, "title", 0.95, NOW)})
    result = matcher(tmdb, store=store).match(MatchQuery("EVA", "champo", tmdb_hint=94655))
    assert result == Match(94655, "source", 1.0)
    assert tmdb.calls == [] and store.pending == {}


# --- search rules -------------------------------------------------------------------------------


def test_director_match_accepted():
    tmdb = FakeTmdb(
        searches={"Les Damnés": [film(1, "Les Damnés", 1969), film(71701, "Les Damnés", 1962)]},
        directors={1: ["Luchino Visconti"], 71701: ["Joseph Losey"]},
    )
    result = matcher(tmdb).match(MatchQuery("LES DAMNÉS", "champo", "LOSEY Joseph"))
    assert result.tmdb_id == 71701 and result.method == "director"
    assert result.score == pytest.approx(1.0)


def test_same_director_but_different_title_refused():
    tmdb = FakeTmdb(
        searches={"Gruffalo, de père en fils": [film(20, "Le Gruffalo", 2009)]},
        directors={20: ["Jakob Schuh", "Max Lang"]},
    )
    result = matcher(tmdb).match(MatchQuery("Gruffalo, de père en fils", None, "Max Lang"))
    assert result.tmdb_id is None and result.reason == "low_score"


def test_homonyms_without_director_are_ambiguous():
    tmdb = FakeTmdb(
        searches={"Sabrina": [film(11860, "Sabrina", 1995), film(6620, "Sabrina", 1954)]}
    )
    result = matcher(tmdb).match(MatchQuery("SABRINA"))
    assert result.tmdb_id is None and result.reason == "ambiguous"


def test_year_hint_resolves_homonyms_and_drops_far_candidates():
    tmdb = FakeTmdb(
        searches={"Sabrina": [film(11860, "Sabrina", 1995), film(6620, "Sabrina", 1954)]}
    )
    assert matcher(tmdb).match(MatchQuery("SABRINA", year_hint=1955)).tmdb_id == 6620
    tmdb = FakeTmdb(searches={"Sabrina": [film(11860, "Sabrina", 1995)]})
    assert matcher(tmdb).match(MatchQuery("SABRINA", year_hint=1954)).tmdb_id is None


def test_year_hint_searches_again_with_the_year():
    tmdb = FakeTmdb(
        searches={
            "Rio Bravo": [film(1, "Rio Bravo", 2030)],
            ("Rio Bravo", 1959): [film(301, "Rio Bravo", 1959)],
        }
    )
    assert matcher(tmdb).match(MatchQuery("Rio Bravo", year_hint=1959)).tmdb_id == 301
    assert ("search", "Rio Bravo", 1959) in tmdb.calls


def test_title_alone_needs_a_close_first_result():
    tmdb = FakeTmdb(searches={"Le Mépris": [film(266, "Le Mépris", 1963)]})
    assert matcher(tmdb).match(MatchQuery("LE MÉPRIS")) == Match(266, "title", pytest.approx(0.95))
    tmdb = FakeTmdb(searches={"Le Mépris": [film(1, "Autre", 1990), film(266, "Le Mépris", 1963)]})
    assert matcher(tmdb).match(MatchQuery("LE MÉPRIS")).reason == "low_score"


def test_original_title_counts():
    tmdb = FakeTmdb(searches={"Vertigo": [film(426, "Sueurs froides", 1958, original="Vertigo")]})
    assert matcher(tmdb).match(MatchQuery("VERTIGO")).tmdb_id == 426


def test_filmography_fallback_finds_drowned_homonym():
    tmdb = FakeTmdb(
        searches={"Eva": [film(i, "Eva", 2000 + i) for i in range(1, 9)]},
        directors={i: ["Someone Else"] for i in range(1, 9)},
        people={"Joseph Losey": [{"id": 7, "known_for_department": "Directing"}]},
        filmographies={7: [film(94655, "Eva", 1962), film(71701, "Les Damnés", 1962)]},
    )
    result = matcher(tmdb).match(MatchQuery("EVA", "champo", "LOSEY Joseph"))
    assert result.tmdb_id == 94655 and result.method == "director"


def test_filmography_ignores_actors():
    tmdb = FakeTmdb(people={"Joseph Losey": [{"id": 7, "known_for_department": "Acting"}]})
    assert matcher(tmdb).match(MatchQuery("EVA", None, "Joseph Losey")).tmdb_id is None
    assert ("credits", 7) not in tmdb.calls


def test_empty_and_unknown_titles():
    assert matcher().match(MatchQuery("[1/3]")).reason == "empty"
    assert matcher().match(MatchQuery("Croissant et Cinéma !")).reason == "no_result"


def test_same_query_resolved_once():
    tmdb = FakeTmdb(searches={"Le Mépris": [film(266, "Le Mépris", 1963)]})
    m = matcher(tmdb)
    for _ in range(3):
        m.match(MatchQuery("LE MÉPRIS", "champo"))
    assert tmdb.calls.count(("search", "Le Mépris", None)) == 1
    assert m.report.screenings["title"] == 3


# --- cache --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tmdb_id", "age_days", "reused"),
    [(266, 29, True), (266, 31, False), (None, 6, True), (None, 8, False)],
)
def test_cache_reuse_window(tmdb_id, age_days, reused):
    tmdb = FakeTmdb(searches={"Le Mépris": [film(999, "Le Mépris", 1963)]})
    entry = CachedMatch(tmdb_id, "title" if tmdb_id else "none", 0.95, NOW - timedelta(age_days))
    store = TitleMatchStore({("le mepris", "champo", None): entry})
    result = matcher(tmdb, store=store).match(MatchQuery("LE MÉPRIS", "champo"))
    if reused:
        assert result.tmdb_id == tmdb_id and tmdb.calls == []
        assert store.pending == {}
    else:
        assert result.tmdb_id == 999 and ("le mepris", "champo", None) in store.pending


def test_new_result_is_queued_for_title_matches():
    tmdb = FakeTmdb(searches={"Le Mépris": [film(266, "Le Mépris", 1963)]})
    store = TitleMatchStore()
    matcher(tmdb, store=store).match(MatchQuery("LE MÉPRIS", "champo", year_hint=1963))
    assert store.pending_rows() == [
        {
            "normalized_title": "le mepris",
            "cinema_id": "champo",
            "year_hint": 1963,
            "tmdb_id": 266,
            "method": "title",
            "score": 0.95,
            "matched_at": NOW.isoformat(),
            "reason": None,
        }
    ]


class FakeDb:
    """PostgREST stand-in: honours limit/offset like Supabase's `max_rows` paging."""

    def __init__(self, rows):
        self.rows, self.selects, self.upserts = rows, [], []

    def select(self, table, params):
        self.selects.append((table, params))
        offset, limit = int(params["offset"]), int(params["limit"])
        return self.rows[offset : offset + limit]

    def upsert(self, table, rows, on_conflict):
        self.upserts.append((table, rows, on_conflict))


def test_db_store_loads_once_per_cinema_and_flushes():
    db = FakeDb(
        [
            {
                "normalized_title": "eva",
                "cinema_id": "champo",
                "year_hint": None,
                "tmdb_id": 94655,
                "method": "director",
                "score": 1.0,
                "matched_at": (NOW - timedelta(days=1)).isoformat(),
            }
        ]
    )
    store = DbTitleMatchStore(db)
    tmdb = FakeTmdb(searches={"Le Mépris": [film(266, "Le Mépris", 1963)]})
    m = matcher(tmdb, store=store)
    assert m.match(MatchQuery("EVA", "champo")).tmdb_id == 94655
    m.match(MatchQuery("LE MÉPRIS", "champo"))
    assert db.selects == [
        (
            "title_matches",
            {
                "select": "normalized_title,cinema_id,year_hint,tmdb_id,method,score,"
                "matched_at,reason",
                "cinema_id": "eq.champo",
                "order": "id",
                "limit": "1000",
                "offset": "0",
            },
        )
    ]
    store.flush()
    ((table, rows, on_conflict),) = db.upserts
    assert table == "title_matches" and on_conflict == "normalized_title,cinema_id,year_hint"
    assert [r["tmdb_id"] for r in rows] == [266] and store.pending == {}


def cached_row(title, tmdb_id=1, reason=None):
    return {
        "normalized_title": title,
        "cinema_id": None,
        "year_hint": None,
        "tmdb_id": tmdb_id,
        "method": "title" if tmdb_id else "none",
        "score": 0.95,
        "matched_at": "2026-11-21T04:00:00.12345+00:00",
        "reason": reason,
    }


def test_db_store_pages_past_max_rows():
    db = FakeDb([cached_row(f"film {i}") for i in range(2500)])
    store = DbTitleMatchStore(db)
    assert store.get(("film 2499", None, None)).tmdb_id == 1
    assert [p["offset"] for _, p in db.selects] == ["0", "1000", "2000"]
    assert db.selects[0][1]["cinema_id"] == "is.null"


def test_cached_not_found_keeps_its_reason_in_the_report():
    db = FakeDb([cached_row("sabrina", tmdb_id=None, reason="ambiguous")])
    tmdb = FakeTmdb()
    m = matcher(tmdb, store=DbTitleMatchStore(db))
    assert m.match(MatchQuery("SABRINA")).reason == "ambiguous"
    assert tmdb.calls == []
    assert "SABRINA (ambiguous, 1 séance(s))" in m.report.summary()


# --- overrides file -----------------------------------------------------------------------------


def write_csv(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "overrides.csv"
    path.write_text("title,cinema_id,tmdb_id,note\n" + body, encoding="utf-8")
    return path


def test_load_overrides_normalizes_titles(tmp_path):
    path = write_csv(
        tmp_path,
        "SABRINA · Ciné-club Billy Wilder [7/13],louxor,6620,Wilder 1954\n"
        "Le Ciné-Quiz,,,pas un film\n"
        "# commentaire,,,\n"
        "\n",
    )
    assert load_overrides(path) == {
        ("sabrina cine club billy wilder 7 13", "louxor"): 6620,
        ("le cine quiz", None): None,
    }


@pytest.mark.parametrize(
    ("body", "error"),
    [
        ("Eva,,abc,\n", "ligne 2 : tmdb_id invalide"),
        ("Eva,,0,\n", "ligne 2 : tmdb_id invalide"),
        ("Eva,,1,\nEVA,,2,\n", "ligne 3 : doublon"),
    ],
)
def test_load_overrides_rejects_bad_lines(tmp_path, body, error):
    with pytest.raises(ValueError, match=error):
        load_overrides(write_csv(tmp_path, body))


def test_load_overrides_requires_columns(tmp_path):
    path = tmp_path / "overrides.csv"
    path.write_text("title,tmdb\nEva,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="colonnes manquantes"):
        load_overrides(path)


def test_versioned_overrides_file_is_valid():
    assert OVERRIDES_CSV.exists()
    load_overrides(OVERRIDES_CSV)


# --- report -------------------------------------------------------------------------------------


def test_report_separates_events_and_lists_title_only_matches():
    tmdb = FakeTmdb(searches={"Le Mépris": [film(266, "Le Mépris", 1963)]})
    m = matcher(tmdb)
    m.match(MatchQuery("LE MÉPRIS", "champo"))
    m.match(MatchQuery("EVA", "champo", tmdb_hint=94655))
    for _ in range(2):
        m.match(MatchQuery("Le Ciné-Quiz", "louxor", event_label="Ciné-Club"))
    m.match(MatchQuery("Âmes ciselées", "louxor", "Yannis Smaragdis"))
    m.overrides[("croissant et cinema", None)] = None  # "not a film" on purpose: not listed
    m.match(MatchQuery("Croissant et Cinéma !", "louxor"))
    report = m.report
    assert report.screenings == {"title": 1, "source": 1, "none": 4}
    text = report.summary()
    assert text.splitlines()[0] == "correspondance TMDB : 2/6 séance(s), source 1, title 1, none 4"
    assert (
        "films sans correspondance (1) :\n  - [louxor] Âmes ciselées (no_result, 1 séance(s))"
        in text
    )
    assert "événements (1) :\n  - [louxor] Le Ciné-Quiz (no_result, 2 séance(s))" in text
    assert "titre seul, à relire (1) :\n  - [champo] LE MÉPRIS → 266 (0.95)" in text
    assert "Croissant" not in text
    assert "http" not in text and "themoviedb" not in text
