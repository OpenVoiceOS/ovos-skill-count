"""Golden rows route to their intent on the m2v prototype pipeline, and
negative rows reach no intent of this skill."""
import json
from pathlib import Path

import pytest
from ovos_bus_client.message import Message
from ovoscope.routing import TALLY, get_prototype_minicroft

SKILL_ID = "ovos-skill-count.openvoiceos"
END2END_DIR = Path(__file__).parent
LOCALE_DIR = END2END_DIR.parents[1] / "ovos_skill_count" / "locale"


def _rows(prefix):
    rows = []
    for path in sorted(END2END_DIR.glob(f"{prefix}*.jsonl")):
        rows += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                 if line.strip()]
    return rows


GOLDEN = _rows("golden_utterances_")
NEGATIVE = _rows("negative_utterances_")
_booted = {}


@pytest.fixture(scope="module")
def engine_for():
    def engine(lang):
        if lang not in _booted:
            for minicroft in _booted.values():
                minicroft.stop()
            _booted.clear()
            _booted[lang] = get_prototype_minicroft([SKILL_ID], lang=lang)
        return _booted[lang].intents.pipeline_plugins["ovos-m2v-prototype-pipeline"]
    yield engine
    for minicroft in _booted.values():
        minicroft.stop()


def _routed(engine, utterance, lang):
    message = Message("recognizer_loop:utterance",
                      {"utterances": [utterance], "lang": lang}, {"lang": lang})
    match = engine.match_low([utterance], lang, message)
    return [match.match_type] if match else []


def _row_id(row):
    return f"{row['lang']}:{row['utterance']}"


@pytest.mark.parametrize("row", GOLDEN, ids=_row_id)
def test_golden_row_routes_to_its_intent(engine_for, row):
    fired = _routed(engine_for(row["lang"]), row["utterance"], row["lang"])
    TALLY.assert_routed(row["utterance"], f"{SKILL_ID}:{row['intent_label']}", fired)


@pytest.mark.parametrize("row", NEGATIVE, ids=_row_id)
def test_negative_row_reaches_no_intent_of_the_skill(engine_for, row):
    fired = _routed(engine_for(row["lang"]), row["utterance"], row["lang"])
    TALLY.assert_not_routed(row["utterance"],
                            [t for t in fired if t.startswith(f"{SKILL_ID}:")], fired)


def test_every_negative_file_has_a_golden_file():
    negative, golden = {row["lang"] for row in NEGATIVE}, {row["lang"] for row in GOLDEN}
    assert negative <= golden, sorted(negative - golden)


def test_every_shipping_locale_has_a_golden_file():
    golden = {row["lang"] for row in GOLDEN}
    shipping = {d.name for d in LOCALE_DIR.iterdir() if d.is_dir() and any(d.rglob("*.intent"))}
    assert golden == shipping, f"golden files {sorted(golden ^ shipping)} differ from shipping locales"


def test_every_locale_ships_every_en_us_intent():
    """A deleted .intent file fails here, whatever the golden rows say."""
    reference = {p.name for p in (LOCALE_DIR / "en-US").glob("*.intent")}
    assert reference, "en-US ships no .intent file"
    missing = {d.name: sorted(reference - {p.name for p in d.glob("*.intent")})
               for d in LOCALE_DIR.iterdir() if d.is_dir()}
    missing = {lang: names for lang, names in missing.items() if names}
    assert not missing, f"locales missing en-US intents: {missing}"


def test_every_golden_label_is_a_shipped_intent():
    for lang in sorted({row["lang"] for row in GOLDEN}):
        shipped = {p.stem for p in (LOCALE_DIR / lang).glob("*.intent")}
        unknown = sorted({row["intent_label"] for row in GOLDEN if row["lang"] == lang} - shipped)
        assert not unknown, f"[{lang}] rows name intents the locale does not ship: {unknown}"

