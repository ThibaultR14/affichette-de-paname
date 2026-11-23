import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from affichette.normalize import paris_window
from affichette.sources import Cinema, SourceError
from affichette.sources.scare import API, ScareSource, parse_row, scare_version
from tests.fakes import FakeResponse, FakeSession, connection_error, fixture

NOW = datetime(2026, 11, 22, 4, 0, tzinfo=UTC)
WINDOW = paris_window(NOW, 7)  # [22/11 00:00, 29/11 00:00[ Paris
SEED = Path(__file__).resolve().parents[2] / "supabase" / "seed.sql"

CHAMPO = Cinema("champo", "Le Champo", "scare", "Le Champo")
GRAND_ACTION = Cinema("grand-action", "Le Grand Action", "scare", "Le Grand Action")
LOUXOR = Cinema("louxor", "Le Louxor", "scare", "Le Louxor - Palais du cinéma")


def pages() -> FakeSession:
    return FakeSession(
        FakeResponse(200, fixture("scare/page1.json")),
        FakeResponse(200, fixture("scare/page2.json")),
    )


def test_downloads_every_page_once_for_all_cinemas():
    session = pages()
    source = ScareSource(session)
    champo = source.fetch(CHAMPO, *WINDOW)
    louxor = source.fetch(LOUXOR, *WINDOW)
    assert len(session.calls) == 2  # two pages, then shared by every cinema
    first, second = session.calls
    assert first["url"] == API
    assert first["params"]["qs"] == "cinecp:75*"
    assert second["url"].startswith(API + "?")  # `next` link, already with its query
    assert second["params"] is None
    assert "affichette" in session.headers["User-Agent"]
    assert {s.cinema_id for s in champo} == {"champo"}
    assert [s.raw_title for s in louxor] == ["SABRINA · Ciné-club Billy Wilder [7/13]"]


def test_fetch_keeps_the_window_only():
    champo = ScareSource(pages()).fetch(CHAMPO, *WINDOW)
    # 34734 (21/11) is before the window, the others are inside.
    assert sorted(s.source_key for s in champo) == [
        "scare:champo:34466",
        "scare:champo:34717",
        "scare:champo:34744",
    ]
    assert all(WINDOW[0] <= s.starts_at < WINDOW[1] for s in champo)


def test_screening_fields():
    by_key = {s.source_key: s for s in ScareSource(pages()).fetch(CHAMPO, *WINDOW)}
    lambs = by_key["scare:champo:34466"]
    assert lambs.raw_title == "LE SILENCE DES AGNEAUX"
    assert lambs.starts_at == datetime(2026, 11, 22, 10, 0, tzinfo=UTC)  # "+0100", no colon
    assert lambs.version == "VO"
    assert lambs.format is None
    assert lambs.runtime_hint == 120  # 7200 seconds
    assert lambs.director_hint == "Jonathan Demme"
    assert lambs.tmdb_hint == 274
    assert lambs.booking_url.startswith("https://pariscinemalechampo.cine.boutique/")
    assert lambs.event_label is None
    assert by_key["scare:champo:34744"].tmdb_hint is None  # no TMDB id in SCARE


def test_french_original_version_is_vf():
    (salut,) = ScareSource(pages()).fetch(GRAND_ACTION, *WINDOW)
    assert salut.raw_title == "NOTRE SALUT"
    assert salut.version == "VF"  # VERSION_ORIGINAL_LOCAL


def test_event_without_booking_url_or_version():
    (sabrina,) = ScareSource(pages()).fetch(LOUXOR, *WINDOW)
    assert sabrina.event_label == "*Ciné-Club"  # as given by SCARE
    assert sabrina.booking_url is None
    assert sabrina.version is None
    assert sabrina.director_hint is None


def test_rows_of_other_cinemas_are_ignored():
    balzac = Cinema("balzac", "Le Balzac", "scare", "Le Balzac")
    assert len(ScareSource(pages()).fetch(balzac, *WINDOW)) == 1


def test_cinema_missing_from_the_dataset_is_an_error():
    """Renamed `cinenom`: an error, so its screenings are not all cancelled."""
    renamed = Cinema("epee-de-bois", "Épée de Bois", "scare", "Épée de Bois")
    with pytest.raises(SourceError, match="absente du jeu SCARE"):
        ScareSource(pages()).fetch(renamed, *WINDOW)


def test_cinema_listed_without_screening_this_week_is_ok():
    # Saint-André is in the dataset; a window with nothing scheduled gives [] (a success).
    sa = Cinema("saint-andre-des-arts", "Saint-André", "scare", "Saint-André des Arts")
    empty_window = (datetime(2027, 1, 1, tzinfo=UTC), datetime(2027, 1, 8, tzinfo=UTC))
    assert ScareSource(pages()).fetch(sa, *empty_window) == []


def test_seed_source_refs_exist_in_the_dataset():
    """Every `scare` cinema of the seed matches a real `cinenom` (exact spelling)."""
    refs = re.findall(r"'scare',\s*'((?:[^']|'')+)'", SEED.read_text(encoding="utf-8"))
    names = {
        r["cinenom"]
        for page in ("scare/page1.json", "scare/page2.json")
        for r in fixture(page)["results"]
    }
    assert len(refs) == 6
    assert {ref.replace("''", "'") for ref in refs} <= names


@pytest.mark.parametrize(
    ("version", "audio", "expected"),
    [
        ("VERSION_ORIGINAL", "7.1", "VO"),
        ("VERSION_ORIGINAL", "ST", "VOSTFR"),
        ("VOST", "ST", "VOSTFR"),
        ("VO", None, "VO"),
        ("VF", None, "VF"),
        ("VF", "ST,OCAP", "VF"),  # subtitles for the deaf
        ("VERSION_LOCAL", "5.1", "VF"),
        ("VERSION_ORIGINAL_LOCAL", "7.1 OCAP", "VF"),
        (None, None, None),
        ("null", "null", None),
    ],
)
def test_scare_version(version, audio, expected):
    assert scare_version(version, audio) == expected


def base_row(**extra):
    return {
        "showid": "1",
        "showstart": "2026-11-23T20:00:00+01:00",
        "filmtitle": "PARANOID PARK",
        **extra,
    }


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        ({"description": "Projection 35mm"}, "35mm"),
        ({"filmtitle": "LA DOLCE VITA 4K"}, "4K"),
        ({"description": "rencontre avec l'équipe"}, None),
    ],
)
def test_format_from_title_or_description(extra, expected):
    assert parse_row(base_row(**extra), "x").format == expected


@pytest.mark.parametrize(
    "extra",
    [{"showstart": None}, {"showid": ""}, {"filmtitle": " "}, {"showstart": "2026-11-23T20:00"}],
)
def test_unusable_rows_are_skipped(extra):
    assert parse_row(base_row(**extra), "x") is None


def test_http_error_fails_every_cinema_once():
    session = FakeSession(FakeResponse(503, "Service Unavailable"))
    source = ScareSource(session)
    with pytest.raises(SourceError, match="HTTP 503"):
        source.fetch(CHAMPO, *WINDOW)
    with pytest.raises(SourceError, match="HTTP 503"):
        source.fetch(LOUXOR, *WINDOW)
    assert len(session.calls) == 1  # the failure is remembered, no retry per cinema


def test_network_error_message_has_no_url():
    source = ScareSource(FakeSession(connection_error()))
    with pytest.raises(SourceError) as err:
        source.fetch(CHAMPO, *WINDOW)
    assert "ConnectionError" in str(err.value)
    assert "http" not in str(err.value)
    assert err.value.__cause__ is None


def test_empty_dataset_is_an_outage():
    source = ScareSource(FakeSession(FakeResponse(200, {"total": 0, "results": []})))
    with pytest.raises(SourceError, match="aucune séance"):
        source.fetch(CHAMPO, *WINDOW)


def test_unreadable_body():
    source = ScareSource(FakeSession(FakeResponse(200, "<html>maintenance</html>")))
    with pytest.raises(SourceError, match="illisible"):
        source.fetch(CHAMPO, *WINDOW)
