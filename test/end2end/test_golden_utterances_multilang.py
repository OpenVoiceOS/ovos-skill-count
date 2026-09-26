"""Multilingual golden-utterance end-to-end coverage for ovos-skill-count.

ovos-skill-count registers one padatious/padacioso intent per locale,
``count_to_n.intent``. Several golden phrasings mean "count without a
limit" ("count forever" and its per-locale translations); dispatching
those through a live bus utterance would run the handler's ``time.sleep``
counting loop forever (see ``test/end2end/test_stop.py``), so, like this
repo's original ``test_golden_utterances.py``, every row is checked
against the trained padacioso container directly
(``container.calc_intent``) instead of a live captured utterance. The
container registers padacioso intents under the lowercased,
extension-stripped basename of the ``.intent`` file, i.e. ``count_to_n``.

Booting one shared MiniCroft with every locale as a secondary_lang hits
an open ovoscope harness bug in get_minicroft's secondary-lang path (see
ovos-skill-alerts' own multilang suite, skipped for the same reason), so
this suite boots one MiniCroft per locale instead
(``get_minicroft([SKILL_ID], max_wait=150, lang=LANG)``, the same
per-locale pattern ovos-skill-date-time's ``test_intents_it_it.py`` uses)
and tears it down before moving to the next locale. Golden rows are
grouped by locale so each locale's MiniCroft only boots once.
"""
import json
from pathlib import Path

import pytest
from ovoscope import get_minicroft

SKILL_ID = "ovos-skill-count.openvoiceos"
INTENT_NAME = "count_to_n"

END2END_DIR = Path(__file__).parent

LANGS = [
    "en-US", "ca-ES", "da-DK", "de-DE", "es-ES", "eu-ES", "fa-IR", "fr-FR",
    "gl-ES", "it-IT", "kab", "nl-NL", "oc-FR", "pt-BR", "pt-PT", "sv-SE",
]


def _load_rows(lang):
    path = END2END_DIR / f"golden_utterances_{lang}.jsonl"
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("needs_manual"):
                continue
            rows.append(row)
    return rows


ALL_ROWS = []
for _lang in LANGS:
    for _row in _load_rows(_lang):
        ALL_ROWS.append(_row)


def _golden_id(row):
    return f"{row['lang']}-{row['intent_label']}-{row['utterance']}"


GOLDEN_ROWS = [pytest.param(r, id=_golden_id(r)) for r in ALL_ROWS]

# Real locale-content defects found and fixed in-place during this pass
# (red-before/green-after verified), keyed by (lang, utterance):
KNOWN_BUGS = {}


@pytest.fixture(scope="module")
def minicroft_factory():
    cache = {"lang": None, "mc": None}

    def _get(lang):
        if cache["lang"] != lang:
            if cache["mc"] is not None:
                cache["mc"].stop()
            cache["mc"] = get_minicroft([SKILL_ID], max_wait=150, lang=lang)
            cache["lang"] = lang
        return cache["mc"]

    yield _get
    if cache["mc"] is not None:
        cache["mc"].stop()


def _container(mc, lang):
    plugin = mc.intents.pipeline_plugins["ovos-padacioso-pipeline-plugin"]
    return plugin.containers[lang]


@pytest.mark.timeout(300)
@pytest.mark.parametrize("row", GOLDEN_ROWS, ids=_golden_id)
def test_golden_utterance_multilang(minicroft_factory, row):
    mc = minicroft_factory(row["lang"])
    container = _container(mc, row["lang"])
    match = container.calc_intent(row["utterance"])
    matched_name = match["name"] if match else None
    expected = f"{SKILL_ID}:{INTENT_NAME}"
    bug_key = (row["lang"], row["utterance"])
    if bug_key in KNOWN_BUGS and matched_name != expected:
        pytest.xfail(reason=f"known-bug: {KNOWN_BUGS[bug_key]}")
    assert matched_name == expected, (
        f"[{row['lang']}] {row['utterance']!r}: expected {expected!r}, got {matched_name!r}"
    )
