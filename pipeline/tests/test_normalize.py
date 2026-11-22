import pytest

from affichette.normalize import normalize_format, normalize_title, normalize_version


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
