"""Regression test: the infinity check must query the session's language.

``handle_how_are_you_intent`` computed
``infinite = self.voc_match(utterance, "infinity", self.lang)`` -- the
skill's own resolved default language -- while every other ``voc_match``/
``extract_number`` call in the same handler passes ``lang=sess.lang``, the
language of the session obtained from ``SessionManager.get(message)``. A
session configured for a language other than the skill's own default
matched the number guard's ``sess.lang``-based vocab correctly but the
infinity vocab was looked up in the wrong language, so an utterance like
"tael for evigt" ("count forever" in Danish) fell through to
``failed_extract_number`` instead of the infinite-count branch.

The installed ``ovos-workshop`` (9.8.0a1) has its own defect that blocks
proving this end-to-end: ``OVOSSkill.resources`` (which backs
``voc_match``/``voc_list``) resolves purely from ``self.lang`` and ignores
the explicit ``lang`` argument entirely --
``skill.voc_list("infinity", "da-DK")`` returns the English vocabulary
whenever ``self.lang`` is "en-US", regardless of the "da-DK" asked for. That
means the *value actually loaded* by any ``voc_match(..., lang=X)`` call in
this handler is unaffected by X whenever X differs from ``self.lang`` --
extract_number, and this vocab lookup, but for a reason a level below this
skill's own code (tracked upstream as an ovos-workshop resources bug, not
ovos-skill-count's). What this skill's code IS responsible for, and what
this test verifies directly, is which language it *asks* voc_match for --
``sess.lang``, matching the rest of the handler, not ``self.lang``.
"""
import unittest
from os.path import dirname
from unittest.mock import patch

from ovos_bus_client import Message, Session
from ovos_utils.messagebus import FakeBus

import ovos_skill_count
from ovos_skill_count import CountSkill


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

    def test_infinity_check_queries_session_lang_not_skill_lang(self):
        session = Session("unit-infinity-lang")
        session.lang = "da-DK"
        message = Message(
            "ovos-skill-count.openvoiceos:count_to_n.intent",
            {"utterance": "tæl for evigt", "lang": "en-US"},
            {"session": session.serialize()},
        )
        # self.lang and sess.lang genuinely diverge here: message.data["lang"]
        # ("en-US") outranks the session in OVOSSkill.lang's own resolution
        # order, while sess.lang stays "da-DK".
        self.assertEqual(self.skill.lang, "en-US")

        calls = []
        real_voc_match = self.skill.voc_match

        def _spy(utt, voc_filename, lang=None, *a, **kw):
            calls.append((voc_filename, lang))
            return real_voc_match(utt, voc_filename, lang, *a, **kw)

        # Stub the number guard out from under it: this test isolates the
        # infinity check's language argument, not the extract_number path,
        # and an unrelated speak_dialog("failed_extract_number") would spawn
        # a spoken-dialog lookup that is not what is under test here.
        with patch.object(self.skill, "voc_match", side_effect=_spy), \
             patch("ovos_skill_count.extract_number", return_value=False):
            self.skill.handle_how_are_you_intent(message)

        infinity_calls = [lang for name, lang in calls if name == "infinity"]
        self.assertTrue(infinity_calls, "expected an 'infinity' voc_match call")
        self.assertEqual(
            infinity_calls[0], session.lang,
            f"infinity check queried lang={infinity_calls[0]!r}, expected "
            f"the session's lang {session.lang!r} (got self.lang="
            f"{self.skill.lang!r} instead)",
        )


if __name__ == "__main__":
    unittest.main()
