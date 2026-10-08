"""Effect-checking end-to-end coverage for ovos-skill-count.

``test_intents_en_us.py`` only checks that ``count_to_n`` is registered in
the padacioso container's intent samples -- it never drives an utterance
through the bus at all, so a handler that matched and spoke nothing (or the
wrong numbers) would still pass. This suite boots a real MiniCroft, fires a
real "count to 3" utterance, and asserts the actual spoken sequence: three
``speak`` messages, in order, pronouncing "one", "two", "three".

Also boots with it-IT active and drives "conta fino a 3" ("count to 3" in
Italian, from ``count_to_n.intent``'s ``locale/it-IT`` translation), since a
default en-US boot only registers en-US intents.
"""
from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovoscope import CaptureSession, get_minicroft

SKILL_ID = "ovos-skill-count.openvoiceos"

_PIPELINE = [
    "ovos-adapt-pipeline-plugin-high",
    "ovos-padatious-pipeline-plugin-high",
    "ovos-padacioso-pipeline-plugin-high",
    "ovos-adapt-pipeline-plugin-medium",
    "ovos-padacioso-pipeline-plugin-medium",
    "ovos-adapt-pipeline-plugin-low",
]


def _spoken_sequence(mc, utterance, lang, session_id):
    session = Session(session_id)
    session.lang = lang
    session.pipeline = list(_PIPELINE)
    session.blacklisted_intents = []
    msg = Message(
        "recognizer_loop:utterance",
        {"utterances": [utterance], "lang": lang},
        {"session": session.serialize(), "source": "A", "destination": "B"},
    )
    capture = CaptureSession(mc, eof_msgs=["mycroft.skill.handler.complete"])
    capture.capture(msg, timeout=20)
    messages = capture.finish()
    speaks = [m for m in messages if m.msg_type in ("speak", "ovos.utterance.speak")]
    return [s.data["utterance"].strip().lower() for s in speaks]


def test_count_to_3_speaks_one_two_three_in_order_en_us():
    mc = get_minicroft([SKILL_ID])
    try:
        spoken = _spoken_sequence(mc, "count to 3", "en-US", "e2e-count-en")
        assert spoken == ["one", "two", "three"], (
            f"expected ['one', 'two', 'three'], got {spoken!r}"
        )
    finally:
        mc.stop()


def test_count_to_3_speaks_correct_sequence_it_it():
    mc = get_minicroft([SKILL_ID], lang="it-IT")
    try:
        spoken = _spoken_sequence(mc, "conta fino a 3", "it-IT", "e2e-count-it")
        assert spoken == ["uno", "due", "tre"], (
            f"expected ['uno', 'due', 'tre'], got {spoken!r}"
        )
    finally:
        mc.stop()
