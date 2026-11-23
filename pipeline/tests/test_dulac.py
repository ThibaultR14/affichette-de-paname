import copy
from datetime import UTC, datetime

import pytest

from affichette.normalize import paris_date, paris_window
from affichette.sources import Cinema, SourceError
from affichette.sources.dulac import (
    API,
    DulacSource,
    dulac_version,
    parse_seance,
)
from tests.fakes import FakeResponse, FakeSession, connection_error, fixture

NOW = datetime(2026, 11, 22, 4, 0, tzinfo=UTC)
WINDOW = paris_window(NOW, 7)  # [22/11 00:00, 29/11 00:00[ Paris
REFLET = Cinema("reflet-medicis", "Reflet Médicis", "dulac", "583")
KEY = "dulac:reflet-medicis:"


def body() -> dict:
    return fixture("dulac/home-bootstrap.json")


def source(payload: dict | None = None) -> tuple[DulacSource, FakeSession]:
    session = FakeSession(FakeResponse(200, payload if payload is not None else body()))
    return DulacSource(session), session


def reflet(payload: dict | None = None) -> dict:
    src, _ = source(payload)
    return {s.source_key: s for s in src.fetch(REFLET, *WINDOW)}


def test_one_call_for_the_run():
    src, session = source()
    src.fetch(REFLET, *WINDOW)
    src.fetch(REFLET, *WINDOW)
    (call,) = session.calls
    assert call["url"] == API
    assert call["params"] == {"days": "7"}
    assert "affichette" in session.headers["User-Agent"]


def test_keeps_reflet_medicis_only():
    screenings = reflet()
    assert {s.cinema_id for s in screenings.values()} == {"reflet-medicis"}
    titles = {s.raw_title for s in screenings.values()}
    assert "En promenade" not in titles  # Majestic Bastille
    assert "Moulin" not in titles  # Majestic Passy


def test_window_cancelled_and_duplicate():
    screenings = reflet()
    # 15 Reflet seances in the fixture: 1 cancelled, 2 outside the window, 1 duplicate.
    assert len(screenings) == 11
    assert all(WINDOW[0] <= s.starts_at < WINDOW[1] for s in screenings.values())
    assert KEY + "19568" not in screenings  # 19568, is_cancelled


def test_date_without_z_is_utc():
    pola = reflet()[KEY + "19579"]  # title "...:22/11/2026 21:00:00" (Paris)
    assert pola.starts_at == datetime(2026, 11, 22, 20, 0, tzinfo=UTC)
    assert pola.starts_at.utcoffset().total_seconds() == 0


def test_late_utc_time_is_next_day_in_paris():
    late = reflet()[KEY + "19588"]  # 27/11 23:30 UTC
    assert paris_date(late.starts_at).isoformat() == "2026-11-28"


def test_screening_fields():
    s = reflet()[KEY + "19603"]
    assert s.raw_title == "L'Amérique des autres"
    assert s.version == "VOSTFR"
    assert s.format is None
    assert s.booking_url.startswith("https://www.ticketingcine.com/EMS0824/")
    assert s.director_hint == "Goran Paskaljević"
    assert s.runtime_hint == 91
    assert s.year_hint is None  # year = 0; release_date is not a production year
    assert s.event_label is None
    assert reflet()[KEY + "19577"].version == "VF"


def test_rerelease_date_is_not_a_year_hint():
    pierre = reflet()[KEY + "19599"]  # 1999 film, re-released 11/11/2026
    assert pierre.raw_title == "Pierre ou les ambiguïtés"
    assert pierre.year_hint is None


def test_year_used_when_given():
    payload = body()
    payload["films_by_id"]["18930"]["year"] = 1999
    assert reflet(payload)[KEY + "19579"].year_hint == 1999


def test_duplicate_keeps_the_complete_film():
    screenings = reflet()
    skin = [s for s in screenings.values() if s.raw_title == "Mysterious Skin"]
    assert len(skin) == 1
    assert skin[0].source_key == KEY + "18657"
    assert skin[0].runtime_hint == 105  # film 18656 (original title, release date)
    assert skin[0].event_label == "Avant-première"
    assert "/EMS0824/" in skin[0].booking_url


def test_seance_without_booking_url():
    s = reflet()[KEY + "19612"]
    assert s.booking_url is None


def test_first_session_is_not_an_event():
    # is_special and event_label "first session" (opening day), but type "standard".
    (merci,) = [s for s in reflet().values() if s.raw_title == "Merci d'être venu"]
    assert merci.event_label is None


def test_format_from_projection_formats():
    payload = body()
    payload["films_by_id"]["18930"]["projection_formats"] = ["35 mm"]
    assert reflet(payload)[KEY + "19579"].format == "35mm"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("VOST", "VOSTFR"), ("vost", "VOSTFR"), ("VF", "VF"), ("VO", "VO"), ("", None), (None, None)],
)
def test_dulac_version(raw, expected):
    assert dulac_version(raw) == expected


def test_parse_seance_skips_unreadable_date():
    seance = copy.deepcopy(body()["seances_week"][0])
    seance["date"] = "demain"
    assert parse_seance(seance, {"title": "X"}, "reflet-medicis") is None


def test_parse_seance_keeps_an_explicit_offset():
    seance = copy.deepcopy(body()["seances_week"][0])
    seance["date"] = "2026-11-22T11:00:00+01:00"
    s = parse_seance(seance, {"title": "X"}, "reflet-medicis")
    assert s.starts_at == datetime(2026, 11, 22, 10, 0, tzinfo=UTC)


def test_seance_without_film_title_is_skipped():
    payload = body()
    payload["films_by_id"]["16627"]["title"] = ""
    assert not any(s.raw_title == "L'Amérique des autres" for s in reflet(payload).values())
    assert len(reflet(payload)) == 10  # its one seance in the window is gone


def test_duplicate_without_booking_url_is_merged():
    # Same room, same time, one record with a ticketing link and one without.
    payload = body()
    copy_ = copy.deepcopy(next(s for s in payload["seances_week"] if s["id"] == "19579"))
    copy_.update(id="99999", booking_url="")
    payload["seances_week"].append(copy_)
    screenings = reflet(payload)
    assert len(screenings) == 11
    assert screenings[KEY + "19579"].booking_url  # the one with the link is kept


def test_key_does_not_depend_on_the_booking_url():
    payload = body()
    for s in payload["seances_week"]:
        s["booking_url"] = ""
    assert set(reflet(payload)) == set(reflet())


def test_missing_film_record_is_skipped(caplog):
    payload = body()
    del payload["films_by_id"]["16627"]
    assert KEY + "19603" not in reflet(payload)
    assert "sans fiche film" in caplog.text


def test_no_film_record_at_all_is_an_error():
    payload = body()
    payload["films_by_id"] = {}
    with pytest.raises(SourceError, match="aucune fiche film"):
        failing(FakeResponse(200, payload)).fetch(REFLET, *WINDOW)


def test_no_room_linked_to_the_cinema_is_an_error():
    payload = body()
    for salle in payload["salles_by_id"].values():
        salle["cinema"] = salle.pop("cinema_id")  # renamed field
    with pytest.raises(SourceError, match="aucune salle"):
        failing(FakeResponse(200, payload)).fetch(REFLET, *WINDOW)


def test_cinema_without_seance_in_the_window_is_ok():
    payload = body()
    payload["seances_week"] = [s for s in payload["seances_week"] if s["salle_id"] == "171"]
    assert reflet(payload) == {}


# --- failures ---------------------------------------------------------------------------------


def failing(*responses) -> DulacSource:
    return DulacSource(FakeSession(*responses))


def test_network_error_has_no_url():
    with pytest.raises(SourceError) as err:
        failing(connection_error()).fetch(REFLET, *WINDOW)
    assert "http" not in str(err.value).lower()
    assert "ConnectionError" in str(err.value)


def test_failure_is_remembered():
    src = failing(FakeResponse(500, {}))
    with pytest.raises(SourceError, match="HTTP 500"):
        src.fetch(REFLET, *WINDOW)
    with pytest.raises(SourceError, match="HTTP 500"):
        src.fetch(REFLET, *WINDOW)  # no second call (FakeSession would raise AssertionError)


@pytest.mark.parametrize("payload", ["<html>", {"meta": {}}, {"seances_week": "x"}])
def test_unreadable_body(payload):
    with pytest.raises(SourceError, match="illisible"):
        failing(FakeResponse(200, payload)).fetch(REFLET, *WINDOW)


def test_truncated_response_is_an_error():
    payload = body()
    payload["meta"]["truncated"] = True
    with pytest.raises(SourceError, match="tronquée"):
        failing(FakeResponse(200, payload)).fetch(REFLET, *WINDOW)


def test_no_seance_at_all_is_an_outage():
    payload = body()
    payload["seances_week"] = []
    with pytest.raises(SourceError, match="aucune séance"):
        failing(FakeResponse(200, payload)).fetch(REFLET, *WINDOW)


def test_unknown_cinema_is_an_error():
    other = Cinema("reflet-medicis", "Reflet Médicis", "dulac", "9999")
    with pytest.raises(SourceError, match="absente"):
        source()[0].fetch(other, *WINDOW)


def test_missing_source_ref():
    with pytest.raises(SourceError, match="source_ref"):
        source()[0].fetch(Cinema("reflet-medicis", "Reflet", "dulac", None), *WINDOW)
