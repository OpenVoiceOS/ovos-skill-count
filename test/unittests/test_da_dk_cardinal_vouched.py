"""``da-DK/cardinal.voc`` holds the two lines a Danish speaker wrote.

The Danish count resources came from andlo in #44, whose ``cardinal.voc`` is
``kardinaltal`` and ``grundtal``. A later union carried a third line,
``kardinaltal er``, that no Danish speaker wrote. In Danish that line is the
start of a sentence ("cardinal numbers are"), not a name for the counting
mode, so no user says it to ask for cardinals.

The line was also unreachable. ``voc_match`` tests each entry as
``.*\\bentry\\b.*``, so an utterance holding "kardinaltal er" holds
"kardinaltal" and matches on the first line already.
"""
import unittest
from os.path import dirname

from ovos_utils.messagebus import FakeBus

import ovos_skill_count
from ovos_skill_count import CountSkill

#: The lines andlo wrote in #44, and the whole file.
VOUCHED = ["kardinaltal", "grundtal"]


class TestDaDkCardinalIsVouched(unittest.TestCase):

    def setUp(self):
        self.skill = CountSkill()
        self.skill._startup(FakeBus(), "ovos-skill-count.openvoiceos")
        self.addCleanup(self.skill.default_shutdown)

    def test_the_file_holds_the_vouched_lines_and_nothing_else(self):
        entries = [e.lower() for e in self.skill.voc_list("cardinal", lang="da-DK")]
        self.assertEqual(sorted(entries), sorted(VOUCHED))

    def test_each_vouched_line_matches_its_own_voc(self):
        for surface in VOUCHED:
            with self.subTest(surface=surface):
                self.assertTrue(
                    self.skill.voc_match(surface, "cardinal", lang="da-DK"))

    def test_a_vouched_line_does_not_match_the_ordinal_voc(self):
        """Control: a file that matched everything would pass the test above."""
        for surface in VOUCHED:
            with self.subTest(surface=surface):
                self.assertFalse(
                    self.skill.voc_match(surface, "ordinal", lang="da-DK"))


if __name__ == "__main__":
    unittest.main()
