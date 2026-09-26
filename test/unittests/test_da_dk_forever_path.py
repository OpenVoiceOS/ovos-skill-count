"""The Danish forever phrasing must reach the infinity vocabulary.

`da-DK/count_to_n.intent` carries `tæl for evigt`, and the handler decides
forever mode with `voc_match(utterance, "infinity")`, not with the intent
name. `extract_number("tæl for evigt", lang="da-DK")` returns `False`, so
the utterance brings no number: if `da-DK/infinity.voc` loses `for evigt`,
the handler speaks `failed_extract_number` and the user never counts, while
the intent still matches and every golden row still passes. #62 deletes
that line, so the line needs an assertion of its own.
"""
import unittest

from ovos_number_parser import extract_number
from ovos_utils.messagebus import FakeBus

from ovos_skill_count import CountSkill

#: The Danish surfaces `count_to_n.intent` carries for the forever path.
FOREVER = ["tæl for evigt", "for evigt", "uendeligt"]


class TestTheDanishForeverPathResolves(unittest.TestCase):

    def setUp(self):
        self.skill = CountSkill()
        self.skill._startup(FakeBus(), "ovos-skill-count.openvoiceos")
        self.addCleanup(self.skill.default_shutdown)

    def test_the_forever_utterance_carries_no_number(self):
        """The reason the vocabulary decides this path and not the parser."""
        self.assertIn(extract_number("tæl for evigt", lang="da-DK"),
                      (False, None))

    def test_every_forever_surface_matches_the_infinity_voc(self):
        for surface in FOREVER:
            with self.subTest(surface=surface):
                self.assertTrue(
                    self.skill.voc_match(surface, "infinity", lang="da-DK"),
                    f"da-DK infinity.voc does not match {surface!r}; the "
                    f"forever path speaks failed_extract_number instead")

    def test_the_intent_file_ships_the_forever_template(self):
        from pathlib import Path
        import ovos_skill_count
        path = (Path(ovos_skill_count.__file__).parent / "locale" / "da-DK"
                / "count_to_n.intent")
        lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines()]
        self.assertIn("tæl for evigt", lines)

    def test_a_number_utterance_does_not_match_the_infinity_voc(self):
        """Control: a file that matched everything would pass the test above."""
        self.assertFalse(
            self.skill.voc_match("tæl til fem", "infinity", lang="da-DK"))

    def test_english_does_not_answer_for_danish(self):
        """Control: the lang argument selects the file."""
        self.assertFalse(
            self.skill.voc_match("for evigt", "infinity", lang="en-US"))


if __name__ == "__main__":
    unittest.main()
