from datetime import UTC, datetime

import pytest

from affichette.normalize import (
    PARIS,
    normalize_format,
    normalize_title,
    normalize_version,
    paris_date,
    paris_window,
    to_utc,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("VOSTF", "VOSTFR"),
        ("v.o.st.fr", "VOSTFR"),
        ("VO", "VO"),
        ("Version originale", "VO"),
        ("VF", "VF"),
        ("version française", "VF"),
        ("", None),
        (None, None),
        ("avant-première", None),
    ],
)
def test_normalize_version(raw, expected):
    assert normalize_version(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("copie 35 mm", "35mm"),
        ("35MM", "35mm"),
        ("70mm", "70mm"),
        ("4K restauré", "4K"),
        ("numérique", "DCP"),
        ("rencontre", None),
        (None, None),
    ],
)
def test_normalize_format(raw, expected):
    assert normalize_format(raw) == expected


def test_normalize_title_strips_accents_and_punctuation():
    assert normalize_title("  Le Mépris ") == "le mepris"
    assert normalize_title("À bout de souffle !") == "a bout de souffle"
    assert normalize_title("L'Œil du diable") == "l oeil du diable"
    assert normalize_title(None) == ""


def test_to_utc_refuses_naive_datetimes():
    assert to_utc(datetime(2026, 11, 22, 20, 0, tzinfo=PARIS)) == datetime(
        2026, 11, 22, 19, 0, tzinfo=UTC
    )
    with pytest.raises(ValueError, match="sans fuseau"):
        to_utc(datetime(2026, 11, 22, 20, 0))


def test_paris_window_starts_at_midnight_in_paris():
    # 23:30 UTC on 21/11 is already 22/11 in Paris.
    start, end = paris_window(datetime(2026, 11, 21, 23, 30, tzinfo=UTC), 7)
    assert start == datetime(2026, 11, 22, 0, 0, tzinfo=PARIS)
    assert end == datetime(2026, 11, 29, 0, 0, tzinfo=PARIS)
    assert to_utc(start) == datetime(2026, 11, 21, 23, 0, tzinfo=UTC)


def test_paris_window_across_the_dst_change():
    # Clocks go back on 25/10/2026: the window is 7 calendar days, not 7 × 24 h.
    start, end = paris_window(datetime(2026, 10, 22, 12, 0, tzinfo=UTC), 7)
    assert to_utc(start) == datetime(2026, 10, 21, 22, 0, tzinfo=UTC)  # UTC+2
    assert to_utc(end) == datetime(2026, 10, 28, 23, 0, tzinfo=UTC)  # UTC+1


def test_paris_date():
    assert paris_date(datetime(2026, 11, 28, 23, 30, tzinfo=UTC)).isoformat() == "2026-11-29"
