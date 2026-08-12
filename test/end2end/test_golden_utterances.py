"""Golden-utterance end-to-end coverage for ovos-skill-count (en-US).

The golden corpus (``golden_utterances.jsonl``) is a vendored slice of the
shared ovoscope golden-utterance dataset, keyed by
``skill_id == "ovos-skill-count.openvoiceos"``. Every row in this skill's
slice is an unbounded "count forever ..." phrasing -- dispatching them
through the real bus would run the counting handler's ``time.sleep`` loop
forever (see ``test/end2end/test_stop.py``'s module docstring), so, like
this repo's own ``test_intents_en_us.py``, golden rows are checked against
the trained padacioso container directly (``container.calc_intent``) rather
than fired as a live utterance. The container registers padacioso intents
under the lowercased, extension-stripped basename of the ``.intent`` file.

Negative utterances are safe to fire for real (they route to other skills
or nowhere), so those go through a real ``CaptureSession``.
"""
import json
from pathlib import Path

import pytest
from ovoscope import CaptureSession, get_minicroft, make_session, make_utterance_message

SKILL_ID = "ovos-skill-count.openvoiceos"
LANG = "en-US"

GOLDEN_PATH = Path(__file__).parent / "golden_utterances.jsonl"

# utterances lifted verbatim from OTHER skills' golden-utterance slices,
# picked for lexical overlap with count's "count"/"forever"/"scale"
# vocabulary.
NEGATIVE_UTTERANCES = [
    ("what color is something", "ovos-skill-color-picker.openvoiceos"),
    ("take a picture", "ovos-skill-camera.openvoiceos"),
    ("what happened today in history", "ovos-skill-days-in-history.openvoiceos"),
    ("launch spotify", "ovos-skill-application-launcher.openvoiceos"),
    ("are you ready", "ovos-skill-boot-finished.openvoiceos"),
    ("set a timer for 5 minutes", "ovos-skill-alerts.openvoiceos"),
    ("what's the weather", "ovos-skill-weather.openvoiceos"),
]


def _label_to_container_name(intent_label: str) -> str:
    return intent_label.removesuffix(".intent").lower()


def _load_golden_rows():
    rows = []
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("needs_manual"):
                continue
            rows.append(row)
    return rows


GOLDEN_ROWS = [pytest.param(r, id=r["utterance"]) for r in _load_golden_rows()]


@pytest.fixture(scope="module")
def minicroft():
    mc = get_minicroft([SKILL_ID])
    yield mc
    mc.stop()


@pytest.fixture(scope="module")
def container(minicroft):
    return minicroft.intents.pipeline_plugins[
        "ovos-padacioso-pipeline-plugin"
    ].containers[LANG]


@pytest.mark.timeout(30)
@pytest.mark.parametrize("row", GOLDEN_ROWS, ids=lambda r: r["utterance"])
def test_golden_utterance(container, row):
    intent_name = _label_to_container_name(row["intent_label"])
    match = container.calc_intent(row["utterance"])
    assert match["name"] == f"{SKILL_ID}:{intent_name}", (
        f"{row['utterance']!r}: expected {SKILL_ID}:{intent_name!r}, got {match['name']!r}"
    )


@pytest.mark.timeout(30)
@pytest.mark.parametrize("negative", NEGATIVE_UTTERANCES, ids=lambda n: n[0])
def test_negative_confusable_not_claimed(minicroft, negative):
    text, source_skill = negative
    session = make_session(session_id=f"negative-{text}",
                            pipeline=["ovos-padatious-pipeline-plugin-high",
                                      "ovos-padacioso-pipeline-plugin"])
    message = make_utterance_message(text, session=session)
    cap = CaptureSession(minicroft=minicroft)
    cap.capture(message, timeout=15)
    types = [m.msg_type for m in cap.finish()]
    claimed = any(t.startswith(f"{SKILL_ID}:") for t in types)
    assert not claimed, f"{text!r} (from {source_skill}) was incorrectly claimed by {SKILL_ID}"
