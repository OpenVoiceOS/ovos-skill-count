"""Every locale resource must carry a name the skill actually looks up.

A dialog whose basename does not match the name in ``speak_dialog`` is never
found and silently falls back to en-US, so the locale looks translated while
the user hears English. The same holds for an intent file no
``@intent_handler`` names: it never registers.
"""
import re
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent.parent / "ovos_skill_count"
LOCALE_DIR = PKG / "locale"
SOURCE = (PKG / "__init__.py").read_text(encoding="utf-8")

REGISTERED_INTENTS = set(re.findall(r'@intent_handler\("([^"]+)"\)', SOURCE))
SPOKEN_DIALOGS = {f"{name}.dialog"
                  for name in re.findall(r'speak_dialog\(\s*"([^"]+)"', SOURCE)}


def test_the_source_registers_the_names_this_test_checks():
    assert REGISTERED_INTENTS, "no @intent_handler found; the regex is stale"
    assert SPOKEN_DIALOGS, "no speak_dialog found; the regex is stale"


def test_every_shipped_intent_file_is_registered():
    orphans = sorted(str(p.relative_to(LOCALE_DIR))
                     for p in LOCALE_DIR.rglob("*.intent")
                     if p.name not in REGISTERED_INTENTS)
    assert orphans == [], "no @intent_handler names these files"


def test_every_shipped_dialog_file_is_spoken():
    orphans = sorted(str(p.relative_to(LOCALE_DIR))
                     for p in LOCALE_DIR.rglob("*.dialog")
                     if p.name not in SPOKEN_DIALOGS)
    assert orphans == [], "no speak_dialog names these files"
