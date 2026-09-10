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

    The test asserts membership, not the content of the two ``cardinal.voc``
    files. A translation change to either file is not a defect in
    ``voc_list``, so it must not make this test red.
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

        # Both directions are asserted. A release that ignores ``lang``
        # returns the en-US list for the da-DK call, and the da-DK pair
        # alone would pass if the two files ever shared a string.
        self.assertIn("kardinaltal", da_cardinal,
                      "voc_list ignored lang='da-DK'")
        self.assertNotIn("kardinaltal", en_cardinal,
                         "the en-US list holds a Danish string")
        self.assertIn("cardinal number", en_cardinal,
                      "voc_list ignored lang='en-US'")
        self.assertNotIn("cardinal number", da_cardinal,
                         "the da-DK list holds an English string")

        self.assertNotEqual(sorted(da_cardinal), sorted(en_cardinal))


if __name__ == "__main__":
    unittest.main()
