"""Effect-checking end-to-end coverage for the failed-extraction path.

``ovos_number_parser.extract_number`` returns ``False`` (not ``None``) when it
finds no number in the utterance. ``handle_how_are_you_intent`` only guarded
against ``None``, so a non-number utterance like "conta fino a banana" fell
through the guard and the handler counted with ``number=False`` instead of
speaking ``failed_extract_number`` -- the skill spoke nothing. This suite
boots a real MiniCroft with it-IT active, drives that utterance, and asserts
the dialog is actually spoken.
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


def _spoken(mc, utterance, lang, session_id):
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
    return [
        m.data.get("meta", {}).get("dialog")
        for m in messages
        if m.msg_type in ("speak", "ovos.utterance.speak")
    ]


def test_non_number_utterance_speaks_failed_extract_number_dialog_it_it():
    mc = get_minicroft([SKILL_ID], lang="it-IT")
    try:
        dialogs = _spoken(mc, "conta fino a banana", "it-IT", "e2e-count-it-banana")
        assert dialogs == ["failed_extract_number"], (
            f"expected the skill to speak 'failed_extract_number', got {dialogs!r}"
        )
    finally:
        mc.stop()
