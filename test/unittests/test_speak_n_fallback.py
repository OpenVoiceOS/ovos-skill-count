from types import SimpleNamespace

from ovos_number_parser import pronounce_number

from ovos_skill_count import CountSkill


def _spoken(lang, n, **kw):
    said = []
    CountSkill.speak_n(SimpleNamespace(speak=said.append), n, lang, **kw)
    return said


def test_language_without_numtag_writer_falls_back_to_number_parser():
    assert _spoken("fa-IR", 3) == [pronounce_number(3, lang="fa-IR")]


def test_numtag_writer_reads_long_scale():
    assert _spoken("en-US", 10**9, short_scale=False) == ["one thousand million"]
