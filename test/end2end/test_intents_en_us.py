"""End-to-end coverage for the en-US count intent definitions.

The skill speaks one utterance per counted number and "count forever" never
returns, so the utterances are matched and not dispatched.
"""
import pytest
from ovos_bus_client.message import Message
from ovoscope.routing import TALLY, get_prototype_minicroft

SKILL_ID = "ovos-skill-count.openvoiceos"
INTENT = f"{SKILL_ID}:count_to_n"
LANG = "en-US"
M2V_PROTOTYPE = "ovos-m2v-prototype-pipeline"


@pytest.fixture(scope="module")
def minicroft():
    minicroft = get_prototype_minicroft([SKILL_ID], lang=LANG)
    yield minicroft
    minicroft.stop()


def _match(minicroft, utterance):
    """The prototype engine's low-stage match for ``utterance``, or None."""
    engine = minicroft.intents.pipeline_plugins[M2V_PROTOTYPE]
    message = Message("recognizer_loop:utterance",
                      {"utterances": [utterance], "lang": LANG}, {"lang": LANG})
    return engine.match_low([utterance], LANG, message)


def _assert_routed(minicroft, utterance):
    match = _match(minicroft, utterance)
    TALLY.assert_routed(utterance, INTENT, [match.match_type] if match else [])
    return match


def test_skill_is_loaded(minicroft):
    assert SKILL_ID in minicroft.plugin_skills


# a finite "count to N" target, the scale/number-kind modifiers, and the
# unbounded "count forever"/"count infinitely" phrasings all route to the
# single count_to_n.intent; the target is captured by the portable
# "{number}" slot and parsed in-handler via ovos-number-parser, so both
# digit and word-form numbers work.
@pytest.mark.parametrize("utterance", [
    "count to 3",
    "count to five",
    "count to 3 in long scale",
    "count to 3 using short scale",
    "count to 3 using ordinal numbers",
    "count to 3 with cardinal numbers",
    "count forever",
    "count infinitely using long scale",
])
def test_en_us_count_intents(minicroft, utterance):
    _assert_routed(minicroft, utterance)


@pytest.mark.parametrize("utterance, expected", [("count to 3", 3), ("count to five", 5)])
def test_number_slot_parses_words_and_digits(minicroft, utterance, expected):
    """The "{number}" slot must resolve to the correct target for both
    digit and word-form phrasings, via extract_number in the handler."""
    from ovos_number_parser import extract_number

    match = _assert_routed(minicroft, utterance)
    number = match.match_data.get("number")
    if number is not None:
        number = number[0] if isinstance(number, list) else number
        try:
            number = int(number)
        except ValueError:
            number = extract_number(number, lang=LANG)
    else:
        number = extract_number(utterance, lang=LANG)
    assert number == expected, utterance
