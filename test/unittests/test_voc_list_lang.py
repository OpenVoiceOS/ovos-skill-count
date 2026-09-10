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
        self.assertEqual(sorted(da_cardinal),
                          sorted(["kardinaltal", "kardinaltal er"]))

        en_cardinal = self.skill.voc_list("cardinal", lang="en-US")
        self.assertEqual(sorted(en_cardinal),
                          sorted(["cardinal number", "cardinal numbers"]))

        self.assertNotEqual(sorted(da_cardinal), sorted(en_cardinal))


if __name__ == "__main__":
    unittest.main()
