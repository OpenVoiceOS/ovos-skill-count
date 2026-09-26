import unittest
from os.path import dirname

from ovos_workshop.resource_files import MustacheDialogRenderer, find_resource

import ovos_skill_count

IT_IT_FAILED_EXTRACT_NUMBER = {
    "Non ho capito fino a che numero volevi che contassi",
    "Non ho capito quale numero hai indicato come limite",
}


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

    def test_it_it_failed_extract_number_dialog_renders_italian_text(self):
        found = find_resource("failed_extract_number.dialog", self.root_dir,
                               res_dirname="locale", lang="it-IT")
        self.assertIsNotNone(
            found, "it-IT failed_extract_number.dialog was not found")
        self.assertIn("it-IT", str(found),
                       f"resolved {found} instead of the it-IT resource")

        renderer = MustacheDialogRenderer()
        renderer.load_template_file("failed_extract_number", str(found))
        rendered = renderer.render("failed_extract_number", {})
        self.assertIn(
            rendered, IT_IT_FAILED_EXTRACT_NUMBER,
            f"rendered {rendered!r} is not one of the known Italian "
            "failed_extract_number variants")
