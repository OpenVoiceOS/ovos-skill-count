"""The count is spoken through the numtag writer.

Each row drives a real utterance through MiniCroft and asserts the spoken
words. The expected words are the standard ordinals of each language.
"""
from types import SimpleNamespace

import pytest
from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession
from ovoscope.routing import PIPELINE, get_prototype_minicroft

import ovos_skill_count

SKILL_ID = "ovos-skill-count.openvoiceos"

ORDINALS = [
    ("en-US", "count to 3 using ordinal numbers", ["first", "second", "third"]),
    ("pt-PT", "começar a contar até 3 com números ordinais", ["primeiro", "segundo", "terceiro"]),
    ("pt-BR", "conte até 3 usando números ordinais", ["primeiro", "segundo", "terceiro"]),
    ("es-ES", "cuenta hasta 3 usando números ordinales", ["primero", "segundo", "tercero"]),
    ("fr-FR", "compte jusqu'à 3 avec les nombres ordinaux", ["premier", "deuxième", "troisième"]),
    ("it-IT", "conta fino a 3 usando i numeri ordinali", ["primo", "secondo", "terzo"]),
    ("de-DE", "zähl bis 3 anhand von ordinalzahlen", ["erste", "zweite", "dritte"]),
    ("nl-NL", "tel tot 3 met behulp van rangtelwoorden", ["eerste", "tweede", "derde"]),
    ("da-DK", "tæl til 3 med ordenstal", ["første", "anden", "tredje"]),
    # numtag tests/gold/sv.jsonl: "första", "andra", "tredje"
    ("sv-SE", "räkna till 3 med ordningstal", ["första", "andra", "tredje"]),
    # numtag tests/gold/eu.jsonl, Euskaltzaindia 18. araua: "lehen", "bigarren", "hirugarren"
    ("eu-ES", "zenbatu arte 3 erabiliz zenbaki ordinalak", ["lehen", "bigarren", "hirugarren"]),
    # numtag tests/gold/pl.jsonl, CLDR RBNF pl masculine ordinals. numtag and
    # ovos-number-parser give the same words here, so the row is a guard.
    ("pl-PL", "policz do 3 liczbami porządkowymi", ["pierwszy", "drugi", "trzeci"]),
]


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(ovos_skill_count, "time", SimpleNamespace(sleep=lambda s: None))


def _spoken(lang, utterance):
    mc = get_prototype_minicroft([SKILL_ID], lang=lang)
    try:
        session = Session(f"e2e-numtag-{lang}")
        session.lang = lang
        session.pipeline = list(PIPELINE)
        session.blacklisted_intents = []
        msg = Message("recognizer_loop:utterance",
                      {"utterances": [utterance], "lang": lang},
                      {"session": session.serialize(), "source": "A", "destination": "B"})
        capture = CaptureSession(mc, eof_msgs=["mycroft.skill.handler.complete"])
        capture.capture(msg, timeout=30)
        return [m.data["utterance"].strip().lower() for m in capture.finish()
                if m.msg_type in ("speak", "ovos.utterance.speak")]
    finally:
        mc.stop()


@pytest.mark.parametrize("lang,utterance,expected", ORDINALS, ids=[r[0] for r in ORDINALS])
def test_ordinal_count_speaks_ordinals(lang, utterance, expected):
    assert _spoken(lang, utterance) == expected


# kab: numtag tests/gold/kab.jsonl (languagesandnumbers.com, "Counting in Kabyle").
KABYLE_CARDINALS = ["yiwen", "sin", "tlata"]


def test_cardinal_count_speaks_numtag_words_kab():
    assert _spoken("kab", "ḥsu alamma 3") == KABYLE_CARDINALS


def test_thousand_is_a_bare_scale_word_ru_ru():
    """1000 is "тысяча": Русская грамматика (1980) § 1378 declines the bare form
    ("И. тысяча двести восемьдесят семь"). numtag writes the CLDR form "одна тысяча"
    only as a variant, and tests/gold/ru.jsonl reads both."""
    spoken = _spoken("ru-RU", "посчитай до 1000 для меня")
    assert (len(spoken), spoken[-1]) == (1000, "тысяча")


def test_compound_cardinal_is_hyphenated_en_us():
    spoken = _spoken("en-US", "count to 22")
    assert spoken[20:] == ["twenty-one", "twenty-two"]
