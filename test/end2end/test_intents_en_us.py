"""End-to-end coverage for the en-US count intent definitions.

A MiniCroft loads the real skill plugin, so the assertions exercise the same
resource loading and intent registration path used at runtime. Utterance
matching is checked against the trained Padacioso container the skill registers
its ``count_to_N.intent`` samples into, which yields the intent name
deterministically.

The container registers padacioso intents under the lowercased, extension-
stripped basename of the ``.intent`` file (``count_to_N.intent`` ->
``count_to_n``), not the literal file name — mirror that here instead of
hardcoding the on-disk spelling, so this stays correct if padacioso's naming
convention shifts again.

The skill speaks one utterance per counted number, so full message-routing
assertions would be slow and non-deterministic; matching the intent at the
container level keeps this focused on routing and fast.
"""
from unittest import TestCase

from ovoscope import get_minicroft

SKILL_ID = "ovos-skill-count.openvoiceos"
INTENT = f"{SKILL_ID}:count_to_n"
LANG = "en-US"


class TestCountIntents(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.minicroft = get_minicroft([SKILL_ID])
        cls.container = cls.minicroft.intents.pipeline_plugins[
            "ovos-padacioso-pipeline-plugin"
        ].containers[LANG]

    @classmethod
    def tearDownClass(cls):
        if cls.minicroft:
            cls.minicroft.stop()

    def test_en_us_count_intents(self):
        self.assertIn(SKILL_ID, self.minicroft.plugin_skills)
        self.assertIn(INTENT, self.container.intent_samples)

        # a finite "count to N" target, the scale/number-kind modifiers, and the
        # unbounded "count forever"/"count infinitely" phrasings all route to the
        # single count_to_N.intent; the target is captured by the portable
        # "{number}" slot and parsed in-handler via ovos-number-parser, so both
        # digit and word-form numbers work.
        utterances = [
            "count to 3",
            "count to five",
            "count to 3 in long scale",
            "count to 3 using short scale",
            "count to 3 using ordinal numbers",
            "count to 3 with cardinal numbers",
            "count forever",
            "count infinitely using long scale",
        ]
        for utterance in utterances:
            match = self.container.calc_intent(utterance)
            self.assertEqual(match["name"], INTENT, utterance)

    def test_number_slot_parses_words_and_digits(self):
        """The "{number}" slot must resolve to the correct target for both
        digit and word-form phrasings, via extract_number in the handler."""
        from ovos_number_parser import extract_number

        for utterance, expected in [("count to 3", 3), ("count to five", 5)]:
            match = self.container.calc_intent(utterance)
            self.assertEqual(match["name"], INTENT, utterance)
            number = match["entities"].get("number")
            if number is not None:
                number = number[0] if isinstance(number, list) else number
                try:
                    number = int(number)
                except ValueError:
                    number = extract_number(number, lang=LANG)
            else:
                number = extract_number(utterance, lang=LANG)
            self.assertEqual(number, expected, utterance)
