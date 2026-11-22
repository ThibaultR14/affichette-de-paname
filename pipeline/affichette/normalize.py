"""Normalization of raw screening fields coming from any source adapter."""

from __future__ import annotations

import re
import unicodedata

_VERSION_PATTERNS = (
    ("VOSTFR", re.compile(r"\bvo\s*st\s*fr?\b|\bvost\b|\bvostf\b")),
    ("VF", re.compile(r"\bvf\b|version\s+fran[cç]aise")),
    ("VO", re.compile(r"\bvo\b|version\s+originale")),
)

_FORMAT_PATTERNS = (
    ("70mm", re.compile(r"\b70\s*mm\b")),
    ("35mm", re.compile(r"\b35\s*mm\b")),
    ("16mm", re.compile(r"\b16\s*mm\b")),
    ("4K", re.compile(r"\b4\s*k\b")),
    ("DCP", re.compile(r"\bdcp\b|num[eé]rique")),
)


def _fold(text: str) -> str:
    return text.strip().lower()


def normalize_version(raw: str | None) -> str | None:
    """'VOSTF', 'v.o.st.fr', 'Version originale' -> 'VOSTFR' | 'VO' | 'VF'; unknown -> None."""
    if not raw:
        return None
    text = _fold(raw).replace(".", "")
    for value, pattern in _VERSION_PATTERNS:
        if pattern.search(text):
            return value
    return None


def normalize_format(raw: str | None) -> str | None:
    """'copie 35 mm', '4k restauré' -> '35mm' | '4K' ...; unknown -> None."""
    if not raw:
        return None
    text = _fold(raw)
    for value, pattern in _FORMAT_PATTERNS:
        if pattern.search(text):
            return value
    return None


def normalize_title(title: str | None) -> str:
    """Matching key: lowercase, no accents, no punctuation, leading article kept."""
    if not title:
        return ""
    text = unicodedata.normalize("NFKD", title)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = text.replace("œ", "oe").replace("æ", "ae")
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()
