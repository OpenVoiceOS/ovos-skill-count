"""No locale ships a resource that en-US lacks.

OVOS-INTENT-2 section 2.3: a (role, base name) pair present in one language
directory MUST be present in every other, except for the ``.blacklist`` and
``.prompt`` roles. This test checks one direction only: every locale's pairs
are a subset of the en-US pairs. Resources that a translated locale lacks are
not checked here.
"""
from pathlib import Path

import pytest

LOCALE_DIR = Path(__file__).resolve().parent.parent.parent / "ovos_skill_count" / "locale"
EXEMPT_ROLES = {".blacklist", ".prompt"}


def _pairs(lang_dir: Path) -> set:
    return {(p.suffix, p.stem) for p in lang_dir.rglob("*")
            if p.is_file() and p.suffix and p.suffix not in EXEMPT_ROLES}


LANGS = sorted(d.name for d in LOCALE_DIR.iterdir()
               if d.is_dir() and d.name != "en-US")


def test_en_us_is_shipped():
    assert (LOCALE_DIR / "en-US").is_dir()


@pytest.mark.parametrize("lang", LANGS)
def test_locale_has_no_resource_en_us_lacks(lang):
    extra = _pairs(LOCALE_DIR / lang) - _pairs(LOCALE_DIR / "en-US")
    assert extra == set(), f"{lang} ships resources en-US lacks: {sorted(extra)}"
