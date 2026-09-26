"""Regression test: the infinity check must query the session's language.

``handle_how_are_you_intent`` computed
``infinite = self.voc_match(utterance, "infinity", self.lang)`` while every
other ``voc_match``/``extract_number`` call in the same handler passes
``lang=sess.lang``, the language of the session from
``SessionManager.get(message)``.

``OVOSSkill.lang`` returns the language of the message being handled, so
in normal use, where the message language and the session language agree,
the two are the same and the old line already read the right vocabulary.
The change is a consistency fix, not a user-visible fix, on ovos-workshop
9.8.1a1. This test builds the one case where the two genuinely differ:
``message.data["lang"]`` is "en-US", which outranks the session in
``OVOSSkill.lang``, while ``sess.lang`` stays "da-DK".

On ovos-workshop 9.8.1a1 the ``lang`` argument of ``voc_match`` is
honoured, so the outcome is testable and not only the argument. The test
asserts both: the infinity lookup asks for the session language, and the
handler then counts in Danish instead of speaking
``failed_extract_number``.

The utterance "tæl for evigt" is in da-DK/infinity.voc, so the handler
enters the unbounded count. The test stops it from inside: ``speak`` is
spied, and the spy calls ``stop_session`` once enough numbers are spoken,
which the loop reads on its next turn. ``time.sleep`` is a no-op for the
duration, so the test takes no wall-clock time. Without both, this test
never returns.
"""
import unittest
from os.path import dirname
from unittest.mock import patch

from ovos_bus_client import Message, Session
from ovos_utils.messagebus import FakeBus

import ovos_skill_count
from ovos_skill_count import CountSkill

# Danish for 1, 2, 3. The count is spoken through pronounce_number, so
# these are the words a da-DK session must hear.
DANISH_FIRST_THREE = ["en", "to", "tre"]


class TestInfinityUsesSessionLang(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill_id = "ovos-skill-count.openvoiceos"
        cls.path = dirname(ovos_skill_count.__file__)

    def setUp(self):
        self.bus = FakeBus()
        self.skill = CountSkill()
        self.skill._startup(self.bus, self.skill_id)

    def tearDown(self):
        self.skill.default_shutdown()

    def _run_handler(self, session, utterance, message_lang, stop_after=3):
        """Drive the handler and give back (infinity langs, spoken text).

        The count is stopped from inside the ``speak`` spy after
        ``stop_after`` utterances, so an unbounded count ends instead of
        hanging the suite.
        """
        message = Message(
            "ovos-skill-count.openvoiceos:count_to_n.intent",
            {"utterance": utterance, "lang": message_lang},
            {"session": session.serialize()},
        )
        calls, spoken = [], []
        real_voc_match = self.skill.voc_match

        def _voc_spy(utt, voc_filename, lang=None, *a, **kw):
            calls.append((voc_filename, lang))
            return real_voc_match(utt, voc_filename, lang, *a, **kw)

        def _speak_spy(utt, *a, **kw):
            spoken.append(utt)
            if len(spoken) >= stop_after:
                self.skill.stop_session(session)

        with patch.object(self.skill, "voc_match", side_effect=_voc_spy), \
             patch.object(self.skill, "speak", side_effect=_speak_spy), \
             patch.object(ovos_skill_count.time, "sleep"):
            self.skill.handle_how_are_you_intent(message)

        return [lang for name, lang in calls if name == "infinity"], spoken

    def test_infinity_check_queries_session_lang_not_skill_lang(self):
        session = Session("unit-infinity-lang")
        session.lang = "da-DK"
        message = Message("test", {"lang": "en-US"})
        infinity_calls, spoken = self._run_handler(
            session, "tæl for evigt", message.data["lang"])

        self.assertTrue(infinity_calls, "expected an 'infinity' voc_match call")
        self.assertEqual(
            infinity_calls[0], session.lang,
            f"infinity check queried lang={infinity_calls[0]!r}, expected "
            f"the session's lang {session.lang!r}",
        )
        # the outcome, not only the argument: the count runs in Danish
        self.assertEqual(spoken[:3], DANISH_FIRST_THREE)

    def test_the_failure_dialog_is_not_spoken_for_an_infinity_utterance(self):
        """The guard must not claim the utterance carries no number.

        ``extract_number("tæl for evigt")`` really does give False, so this
        fails the moment the infinity path stops being exempt from the
        guard, or stops reading the session language.
        """
        session = Session("unit-infinity-dialog")
        session.lang = "da-DK"
        dialogs = []
        with patch.object(self.skill, "speak_dialog",
                          side_effect=lambda name, *a, **kw: dialogs.append(name)):
            _, spoken = self._run_handler(session, "tæl for evigt", "en-US")
        self.assertNotIn("failed_extract_number", dialogs)
        self.assertEqual(spoken[:3], DANISH_FIRST_THREE)

    def test_a_da_dk_session_with_no_number_still_fails_the_guard(self):
        """Positive control for the guard itself.

        An utterance that is neither a number nor an infinity phrase must
        still reach ``failed_extract_number``. Without this, the two tests
        above would also pass if the guard never fired at all.
        """
        session = Session("unit-guard-control")
        session.lang = "da-DK"
        dialogs = []
        with patch.object(self.skill, "speak_dialog",
                          side_effect=lambda name, *a, **kw: dialogs.append(name)):
            _, spoken = self._run_handler(session, "tæl til banan", "en-US")
        self.assertEqual(dialogs, ["failed_extract_number"])
        self.assertEqual(spoken, [])


if __name__ == "__main__":
    unittest.main()
