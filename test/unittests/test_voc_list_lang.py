import unittest
from os.path import dirname

from ovos_utils.messagebus import FakeBus

import ovos_skill_count
from ovos_skill_count import CountSkill


class TestVocListLang(unittest.TestCase):
    """
    ``voc_list`` must honour the ``lang`` argument it is given instead of
    always resolving vocabulary through the skill's own default language.
    A skill asking for da-DK vocabulary while its default is en-US must get
    back da-DK strings, not en-US ones.

    The test asserts that the two lists are non-empty and differ, never
    that either holds a particular string. A translation change to either
    ``cardinal.voc`` is not a defect in ``voc_list``, so it must not make
    this test red; three such changes did, and the message sent the reader
    to ``voc_list`` when the file had changed.
    """

    @classmethod
    def setUpClass(cls):
        cls.skill_id = "ovos-skill-count.openvoiceos"
        cls.root_dir = dirname(ovos_skill_count.__file__)

    def setUp(self):
        self.bus = FakeBus()
        self.skill = CountSkill()
        self.skill._startup(self.bus, self.skill_id)
        self.addCleanup(self.skill.default_shutdown)

    def test_voc_list_returns_requested_lang_vocab(self):
        self.assertEqual(self.skill.lang, "en-US")

        da_cardinal = self.skill.voc_list("cardinal", lang="da-DK")
        en_cardinal = self.skill.voc_list("cardinal", lang="en-US")

        self.assertTrue(da_cardinal, "da-DK cardinal vocabulary is empty")
        self.assertTrue(en_cardinal, "en-US cardinal vocabulary is empty")

        # A release that ignores ``lang`` returns the en-US list for the
        # da-DK call; then the two lists are the same set. The assertion is
        # on the two lists as sets, never on a particular translation: a
        # da-DK file that says "grundtal" instead of "kardinaltal" is not a
        # defect in ``voc_list`` and must not make this test red. Nor is a
        # loanword the two files share: 10 of the 105 locale pairs in this
        # skill share a cardinal string today, so disjointness is stricter
        # than the property under test, which is only that lang is honoured.
        self.assertNotEqual(set(da_cardinal), set(en_cardinal),
                            "voc_list returned the same strings for lang='da-DK' "
                            "and lang='en-US'; the lang argument was ignored")


if __name__ == "__main__":
    unittest.main()
