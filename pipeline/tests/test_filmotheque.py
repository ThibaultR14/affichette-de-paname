from datetime import UTC, date, datetime

import pytest

from affichette.normalize import paris_window
from affichette.sources import Cinema, SourceError
from affichette.sources.filmotheque import (
    HOME,
    FilmothequeSource,
    film_links,
    film_slug,
    parse_duration,
    parse_film_page,
    resolve_day,
)
from tests.fakes import FIXTURES, FakeResponse, FakeSession, connection_error

NOW = datetime(2026, 11, 23, 4, 0, tzinfo=UTC)
WINDOW = paris_window(NOW, 7)  # [23/11 00:00, 30/11 00:00[ Paris
TODAY = date(2026, 11, 23)
FILMO = Cinema("filmotheque", "Filmothèque du Quartier Latin", "filmotheque", None)
BASE = "https://lafilmotheque.fr/films/"
OHONG = BASE + "ohong-village-%e8%9a%b5%e8%b1%90%e6%9d%91/"


def page(name: str) -> str:
    return (FIXTURES / "filmotheque" / f"{name}.html").read_text(encoding="utf-8")


def mini_home(*urls: str) -> str:
    links = "".join(f'<a href="{u}" class="more-link for-desktop">Voir</a>' for u in urls)
    return (
        '<html><body><section id="front-this_week">'
        f'{links}<a href="https://lafilmotheque.fr/la-filmo-plus/x/">événement</a>'
        "</section></body></html>"
    )


def film_page(days: str, generic: str = "<li>1960</li><li>01H30</li>", title="Film") -> str:
    return (
        f'<main><div class="movie-infos large"><div class="titles"><h1>{title}</h1>'
        f'<h3 class="director">Quelqu’un</h3><ul class="generic">{generic}</ul></div></div>'
        '<h3 class="title">Cette semaine</h3><div class="movie-programmation">'
        '<span class="h4 programmation-title R">Salle Marilyn</span>'
        f'<div class="movie-timetable R">{days}</div></div></main>'
    )


def day(label: str, *hours: str) -> str:
    hs = "".join(f"<div>{h}</div>" for h in hours)
    return (
        f'<div class="day"> <span class="day-title">{label}</span>'
        f'<div class="day-hours">{hs}</div></div>'
    )


def three_films_source() -> tuple[FilmothequeSource, FakeSession, list[float]]:
    urls = [BASE + "taxi-driver/", OHONG, BASE + "adieu-philippine-2/"]
    session = FakeSession(
        FakeResponse(200, mini_home(*urls)),
        FakeResponse(200, page("taxi-driver")),
        FakeResponse(200, page("ohong-village")),
        FakeResponse(200, page("adieu-philippine")),
    )
    sleeps: list[float] = []
    return FilmothequeSource(session, delay_s=1.0, sleep=sleeps.append), session, sleeps


# --- home page ----------------------------------------------------------------------------------


def test_film_links_both_weeks_deduplicated():
    links = film_links(page("home"))
    assert len(links) == len(set(links)) == 44
    assert all(u.startswith(BASE) for u in links)
    slugs = {film_slug(u) for u in links}
    assert {"taxi-driver", "ohong-village-蚵豐村"} <= slugs  # this week
    assert {"adieu-philippine-2", "house"} <= slugs  # next week grid only


def test_film_links_ignores_other_pages():
    home = mini_home(BASE + "a/", BASE + "a/#x", "https://lafilmotheque.fr/evenements/b/")
    home += '<a href="https://lafilmotheque.fr/films/hors-liste/">header</a>'
    assert film_links(home) == [BASE + "a/"]
    assert film_links("<html><body>maintenance</body></html>") == []


# --- dates and fields ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Mercredi 18", date(2026, 11, 18)),
        ("lundi 23", date(2026, 11, 23)),
        ("mardi 01", date(2026, 12, 1)),
        ("Vendredi 27", date(2026, 11, 27)),
        ("Jeudi 18", None),  # 18/11 is a Wednesday
        ("Funday 18", None),
        ("", None),
    ],
)
def test_resolve_day(label, expected):
    assert resolve_day(label, TODAY) == expected


def test_resolve_day_across_new_year():
    assert resolve_day("vendredi 01", date(2026, 12, 28)) == date(2027, 1, 1)


def test_parse_duration():
    assert parse_duration("01H55") == 115
    assert parse_duration("02h01") == 121
    assert parse_duration("Couleurs") is None
    assert parse_duration("1976") is None


def test_taxi_driver_page():
    screenings = parse_film_page(page("taxi-driver"), "taxi-driver", "filmotheque", TODAY)
    assert len(screenings) == 16
    s = next(s for s in screenings if s.source_key == "filmotheque:taxi-driver:B:2026-11-23T17:20")
    assert s.starts_at == datetime(2026, 11, 23, 16, 20, tzinfo=UTC)  # 17:20 Paris (UTC+1)
    assert s.raw_title == "Taxi Driver"
    assert (s.year_hint, s.runtime_hint, s.director_hint) == (1976, 115, "Martin Scorsese")
    assert s.format == "4K"  # "numérique 4K"
    assert s.version is None
    assert s.booking_url is None  # the front falls back to the cinema website
    assert s.cinema_id == "filmotheque"


def test_two_rooms_duplicate_and_entities():
    screenings = parse_film_page(page("ohong-village"), "ohong-village", "filmotheque", TODAY)
    # 15 listed times, "Mercredi 18" and "mercredi 18" both at 19H30.
    assert len(screenings) == 14
    assert {s.source_key.split(":")[2] for s in screenings} == {"R", "B"}
    assert screenings[0].raw_title == "OHONG VILLAGE – 蚵豐村"  # &#8211; decoded
    assert screenings[0].format == "DCP"  # "numérique 2K"


def test_coming_soon_block():
    (s,) = parse_film_page(page("adieu-philippine"), "adieu-philippine-2", "f", TODAY)
    assert s.starts_at == datetime(2026, 11, 27, 18, 15, tzinfo=UTC)  # vendredi 27, 19H15


def test_summer_time_and_after_midnight():
    html = film_page(day("samedi 27", "21H00", "00H30"), generic="<li>35mm</li><li>VOSTF</li>")
    screenings = parse_film_page(html, "x", "f", date(2026, 6, 25))
    starts = sorted(s.starts_at for s in screenings)
    assert starts == [
        datetime(2026, 6, 27, 19, 0, tzinfo=UTC),  # 21:00 Paris (UTC+2)
        datetime(2026, 6, 27, 22, 30, tzinfo=UTC),  # night of the 27th to the 28th
    ]
    assert {(s.format, s.version, s.year_hint) for s in screenings} == {("35mm", "VOSTFR", None)}


@pytest.mark.parametrize(
    ("days", "message"),
    [
        (day("Jeudi 18", "13H30"), "jour illisible 'Jeudi 18'"),
        (day("Mer. 25", "13H30"), "jour illisible"),
        (day("lundi 23", "13H30", "19H30 + débat"), r"horaire illisible '19H30 \+ débat'"),
    ],
)
def test_unreadable_day_or_time_fails(days, message):
    # Skipping it would cancel the screenings already imported for that block.
    with pytest.raises(SourceError, match=message):
        parse_film_page(film_page(days), "x", "f", TODAY)


def test_unknown_room_fails():
    html = film_page(day("lundi 23", "13H30")).replace("movie-timetable R", "movie-timetable C")
    with pytest.raises(SourceError, match="salle inconnue"):
        parse_film_page(html, "x", "f", TODAY)


def test_format_from_presentation_text_when_not_in_the_list():
    html = film_page(day("lundi 23", "13H30")).replace(
        "</div></div><h3", '</div><div class="presentation"><p>Copie 35 mm.</p></div></div><h3'
    )
    (s,) = parse_film_page(html, "x", "f", TODAY)
    assert s.format == "35mm"
    (s,) = parse_film_page(film_page(day("lundi 23", "13H30")), "x", "f", TODAY)
    assert s.format is None


def test_page_without_title_is_an_error():
    with pytest.raises(SourceError, match="sans titre"):
        parse_film_page(film_page(day("lundi 23", "13H30"), title=""), "x", "f", TODAY)


# --- fetch --------------------------------------------------------------------------------------


def test_fetch_home_then_each_film_page():
    src, session, sleeps = three_films_source()
    screenings = src.fetch(FILMO, *WINDOW)
    assert [c["url"] for c in session.calls] == [
        HOME,
        BASE + "taxi-driver/",
        OHONG,
        BASE + "adieu-philippine-2/",
    ]
    assert all(c["timeout"] for c in session.calls)
    assert "affichette" in session.headers["User-Agent"]
    assert sleeps == [1.0, 1.0]  # between film pages only
    # In [23/11, 30/11[: Taxi Driver 4, Ohong Village 4, Adieu Philippine 1.
    assert len(screenings) == 9
    assert all(WINDOW[0] <= s.starts_at < WINDOW[1] for s in screenings)
    assert len({s.source_key for s in screenings}) == 9


def test_idempotent_keys():
    first = {s.source_key for s in three_films_source()[0].fetch(FILMO, *WINDOW)}
    second = {s.source_key for s in three_films_source()[0].fetch(FILMO, *WINDOW)}
    assert first == second


def test_home_http_error():
    src = FilmothequeSource(FakeSession(FakeResponse(500, "oops")), sleep=lambda _: None)
    with pytest.raises(SourceError, match="HTTP 500"):
        src.fetch(FILMO, *WINDOW)


def test_network_error_message_has_no_url():
    src = FilmothequeSource(FakeSession(connection_error()), sleep=lambda _: None)
    with pytest.raises(SourceError) as exc:
        src.fetch(FILMO, *WINDOW)
    assert "http" not in str(exc.value).lower().replace("https", "")
    assert "://" not in str(exc.value)


def test_no_film_on_home():
    src = FilmothequeSource(FakeSession(FakeResponse(200, "<html></html>")), sleep=lambda _: None)
    with pytest.raises(SourceError, match="aucun film"):
        src.fetch(FILMO, *WINDOW)


def test_too_many_films():
    home = mini_home(*(f"{BASE}f{i}/" for i in range(121)))
    src = FilmothequeSource(FakeSession(FakeResponse(200, home)), sleep=lambda _: None)
    with pytest.raises(SourceError, match="page inattendue"):
        src.fetch(FILMO, *WINDOW)


def test_one_missing_film_page_fails_the_cinema():
    session = FakeSession(
        FakeResponse(200, mini_home(BASE + "taxi-driver/", BASE + "gone/")),
        FakeResponse(200, page("taxi-driver")),
        FakeResponse(404, "not found"),
    )
    with pytest.raises(SourceError, match=r"HTTP 404 \(fiche gone\)"):
        FilmothequeSource(session, sleep=lambda _: None).fetch(FILMO, *WINDOW)


def test_no_screening_at_all():
    session = FakeSession(
        FakeResponse(200, mini_home(BASE + "a/")),
        FakeResponse(200, film_page("")),
    )
    with pytest.raises(SourceError, match="aucune séance"):
        FilmothequeSource(session, sleep=lambda _: None).fetch(FILMO, *WINDOW)


def test_screenings_outside_window_only_is_a_success():
    session = FakeSession(
        FakeResponse(200, mini_home(BASE + "a/")),
        FakeResponse(200, film_page(day("mercredi 18", "13H30"))),
    )
    assert FilmothequeSource(session, sleep=lambda _: None).fetch(FILMO, *WINDOW) == []
