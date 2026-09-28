"""No locale file may carry one sample twice under the consumer's tokenizer.

Padatious trains on the token list, not on the raw line, so two lines that
differ only in whitespace are one sample written twice. A `.voc` file loads
as the union of its lines, which absorbs a repeat silently. Both forms
arrive through a translation import, so the census that finds them must run
in the suite and not once by hand: #115 removed ten exact repeats, and four
whitespace-only twins stayed behind in the two `count_to_n.intent` files.
"""
from collections import defaultdict
from pathlib import Path

from ovos_padatious.util import tokenize

LOCALE_DIR = (Path(__file__).resolve().parent.parent.parent
              / "ovos_skill_count" / "locale")
SUFFIXES = (".voc", ".intent", ".dialog")


def _samples(path: Path) -> dict:
    """Token tuple -> the lines that produce it, blanks and comments dropped."""
    out = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        out[tuple(tokenize(stripped))].append(stripped)
    return out


def _files() -> list:
    return sorted(p for p in LOCALE_DIR.rglob("*") if p.suffix in SUFFIXES)


def test_the_census_reads_the_resource_files():
    """A stale path finds no file, and an empty sweep reports no repeat."""
    files = _files()
    assert len(files) > 100, f"{len(files)} resource files found; the path is stale"
    assert any(p.name == "count_to_n.intent" for p in files)


def test_the_tokenizer_folds_a_double_space():
    """The control for the rule: this is the defect the census must see."""
    assert tokenize("tæl til {number}  i kort skala") == \
        tokenize("tæl til {number} i kort skala")
    assert tokenize("tæl til {number} i kort skala") != \
        tokenize("tæl til {number} i lang skala")


def test_no_locale_file_repeats_a_sample():
    repeats = []
    for path in _files():
        for lines in _samples(path).values():
            if len(lines) > 1:
                repeats.append(f"{path.relative_to(LOCALE_DIR)}: {lines}")
    assert repeats == [], "one sample written twice:\n" + "\n".join(repeats)
