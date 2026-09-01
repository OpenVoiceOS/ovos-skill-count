import unittest
from os.path import dirname

from ovos_workshop.resource_files import find_resource

import ovos_skill_count


class TestIntentResourceLocale(unittest.TestCase):
    """
    The ``count_to_n.intent`` handler decorator name must match the on-disk
    filename exactly: resource resolution is case-sensitive, so a locale
    whose file is named with a different case never loads its intent.
    """

    def setUp(self):
        self.root_dir = dirname(ovos_skill_count.__file__)

    def test_it_it_count_to_n_intent_resolves_to_italian_file(self):
        found = find_resource("count_to_n.intent", self.root_dir,
                               res_dirname="locale", lang="it-IT")
        self.assertIsNotNone(
            found, "it-IT count_to_n.intent was not found by exact-case "
                   "resource lookup")
        # the case-sensitive lang-directory match must win; a case mismatch
        # falls through to the language-agnostic walk fallback and silently
        # returns a *different* locale's file (e.g. en-US), training the
        # it-IT skill on English utterances instead of Italian ones.
        self.assertIn("it-IT", str(found),
                       f"resolved {found} instead of the it-IT resource")
