"""The count stops at the number the user said, read in the scale of the
user's language unless the user names a scale.

A count to a billion takes years, so the tests record the bound of the
counting loop and count nothing.
"""
from unittest.mock import patch

import pytest
from ovos_bus_client import Message, Session
from ovos_utils.messagebus import FakeBus

import ovos_skill_count
from ovos_skill_count import CountSkill

SKILL_ID = "ovos-skill-count.openvoiceos"


def count_bound(lang, utterance, slot):
    skill = CountSkill()
    skill._startup(FakeBus(), SKILL_ID)
    session = Session("count-target")
    session.lang = lang
    message = Message(f"{SKILL_ID}:count_to_n.intent",
                      {"utterance": utterance, "number": slot},
                      {"session": session.serialize()})
    bounds = []

    def no_count(start, stop):
        bounds.append((start, stop))
        return []

    try:
        with patch.object(ovos_skill_count, "range", no_count, create=True):
            skill.handle_how_are_you_intent(message)
    finally:
        skill.default_shutdown()
    return bounds


@pytest.mark.parametrize("lang, utterance, slot, number", [
    ("en-US", "count to one billion", "one billion", 10 ** 9),
    ("pt-BR", "conte até um bilhão", "um bilhão", 10 ** 9),
])
def test_a_billion_is_read_in_the_scale_of_the_language(lang, utterance, slot, number):
    assert count_bound(lang, utterance, slot) == [(1, number + 1)]


@pytest.mark.parametrize("lang, utterance, number", [
    ("en-US", "count from one to three", 3),
    ("pt-PT", "conta de um até três", 3),
])
def test_without_a_slot_the_count_stops_at_the_last_number(lang, utterance, number):
    assert count_bound(lang, utterance, None) == [(1, number + 1)]
