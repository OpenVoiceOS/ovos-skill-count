"""Every surface this branch carries must match through ``voc_match``.

The golden rows added beside these words do NOT exercise them. A row's
utterance matches the intent on its opening ("zähle bis fünf", "compta fins a
cinc", "cuenta hasta cinco") and the trailing phrase is tolerated by the
matcher, so the row passes with the vocabulary file emptied. Measured in the
review of #105: removing all six new forms left the end2end selection at
`12 passed, 55 deselected`, unchanged.

So the vocabulary is asserted directly, against the same resource loader the
skill uses at runtime. Removing a line from a ``.voc`` file makes exactly the
case for that line fail, which is the property the rows were meant to carry.
"""
import unittest
from os.path import dirname

from ovos_utils.messagebus import FakeBus

import ovos_skill_count
from ovos_skill_count import CountSkill

#: (lang, voc name, surface) for every line this branch adds to a `.voc`.
#: The `.dialog` line is not here: a dialog is spoken, never matched.
CARRIED = [
    ("ca-ES", "cardinal", "nombre cardinal"),
    ("ca-ES", "cardinal", "nombres cardinals"),
    ("ca-ES", "ordinal", "nombre ordinal"),
    ("ca-ES", "ordinal", "nombres ordinals"),
    ("ca-ES", "ordinal", "nombre ordenat"),
    ("ca-ES", "ordinal", "nombres ordenats"),
    ("de-DE", "ordinal", "ordinale Zahl"),
    ("de-DE", "ordinal", "ordinale Zahlen"),
    ("es-ES", "ordinal", "número en orden"),
    ("es-ES", "ordinal", "números en orden"),
    ("es-ES", "infinity", "para siempre"),
    ("es-ES", "infinity", "infinidad"),
]

#: The word each new surface must NOT be confused with. `voc_match` on the
#: other file of the same locale must refuse it, so a test that passes
#: because every file matches everything is caught.
OTHER_VOC = {"cardinal": "ordinal", "ordinal": "cardinal",
             "infinity": "cardinal"}


class TestTheCarriedVocabularyMatches(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.skill_id = "ovos-skill-count.openvoiceos"
        cls.root_dir = dirname(ovos_skill_count.__file__)

    def setUp(self):
        self.bus = FakeBus()
        self.skill = CountSkill()
        self.skill._startup(self.bus, self.skill_id)
        self.addCleanup(self.skill.default_shutdown)

    def test_every_carried_surface_matches_its_own_voc(self):
        for lang, voc, surface in CARRIED:
            with self.subTest(lang=lang, voc=voc, surface=surface):
                self.assertTrue(
                    self.skill.voc_match(surface, voc, lang=lang),
                    f"{lang} {voc}.voc does not match {surface!r}; the "
                    f"surface is carried but unreachable")

    def test_a_carried_surface_is_in_the_list_for_its_lang(self):
        # `voc_match` can match on a substring of another entry, so the
        # exact line is also asserted against the loaded list.
        for lang, voc, surface in CARRIED:
            with self.subTest(lang=lang, voc=voc, surface=surface):
                entries = self.skill.voc_list(voc, lang=lang)
                self.assertIn(surface.lower(), [e.lower() for e in entries])

    def test_a_carried_surface_does_not_match_the_neighbour_voc(self):
        """Control: a file that matched everything would pass the first test."""
        for lang, voc, surface in CARRIED:
            other = OTHER_VOC[voc]
            with self.subTest(lang=lang, voc=voc, surface=surface):
                self.assertFalse(
                    self.skill.voc_match(surface, other, lang=lang),
                    f"{lang} {other}.voc matched {surface!r}, which belongs "
                    f"to {voc}.voc")

    def test_another_locale_does_not_answer_for_this_one(self):
        """Control: the lang argument really selects the file.

        Without it, en-US vocabulary would answer every call and the three
        locales above would be untested.
        """
        for lang, voc, surface in CARRIED:
            with self.subTest(lang=lang, voc=voc, surface=surface):
                self.assertFalse(
                    self.skill.voc_match(surface, voc, lang="en-US"),
                    f"en-US {voc}.voc matched the {lang} surface {surface!r}")


if __name__ == "__main__":
    unittest.main()
