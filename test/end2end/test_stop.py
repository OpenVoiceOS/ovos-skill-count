"""End-to-end stop / counting coverage for ovos-skill-count.

These assertions are deliberately *drift-immune*. Pinning an exact, ordered
``expected_messages`` list is brittle here for two reasons:

* the bus vocabulary drifts (``speak`` -> ``ovos.utterance.speak``,
  ``complete_intent_failure`` -> ``ovos.intent.unmatched``), and under the
  opt-in dual-send migration every renamed message is emitted twice, doubling
  the totals; and
* the counting handler runs a real ``time.sleep`` loop in a daemon thread, so
  the number and interleaving of ``speak`` messages is non-deterministic.

So instead of counting messages, each test asserts only the load-bearing facts:
the intent that matched, whether a stop actually happened, and — for the
counting skill — the skill's own ``active_sessions`` state, which is the ground
truth of whether counting is still running.
"""
import threading
import time
from unittest import TestCase

from ovoscope import CaptureSession, get_minicroft, make_session, make_utterance_message

SKILL_ID = "ovos-skill-count.openvoiceos"

# "the skill spoke", either spelling (legacy / ovos.* namespace)
SPOKE = {"speak", "ovos.utterance.speak"}
# "nothing matched", either spelling (legacy / renamed)
NO_MATCH = {"complete_intent_failure", "ovos.intent.unmatched"}
# "a stop actually happened" — the broadcast every stoppable component obeys
STOPPED = {"mycroft.stop", "ovos.stop"}


def _capture(minicroft, message, timeout=15):
    """Emit ``message`` and return the set of message types seen until the
    utterance is handled (or ``timeout``)."""
    cap = CaptureSession(minicroft=minicroft)
    cap.capture(message, timeout=timeout)
    return {m.msg_type for m in cap.finish()}


class TestStopNoSkills(TestCase):

    def setUp(self):
        self.minicroft = get_minicroft([])

    def tearDown(self):
        if self.minicroft:
            self.minicroft.stop()

    def test_exact_stop_triggers_global_stop(self):
        session = make_session(session_id="123",
                               pipeline=["ovos-stop-pipeline-plugin-high"])
        message = make_utterance_message("stop", session=session)
        types = _capture(self.minicroft, message)
        self.assertTrue(STOPPED.intersection(types),
                        f"exact 'stop' did not trigger a global stop ({types})")

    def test_fuzzy_stop_high_does_not_match(self):
        # at high confidence only an exact "stop" matches; a fuzzy phrase must
        # fall through without stopping anything
        session = make_session(session_id="123",
                               pipeline=["ovos-stop-pipeline-plugin-high"])
        message = make_utterance_message("could you stop that", session=session)
        types = _capture(self.minicroft, message)
        self.assertFalse(STOPPED.intersection(types),
                         f"fuzzy phrase should not stop at high confidence ({types})")
        self.assertTrue(NO_MATCH.intersection(types),
                        f"expected an unmatched signal ({types})")

    def test_fuzzy_stop_medium_matches(self):
        # the medium stage fuzzy-matches "stop", so a global stop should fire
        session = make_session(session_id="123",
                               pipeline=["ovos-stop-pipeline-plugin-medium"])
        message = make_utterance_message("could you stop that", session=session)
        types = _capture(self.minicroft, message)
        self.assertTrue(STOPPED.intersection(types),
                        f"fuzzy 'stop' did not match at medium confidence ({types})")


class TestCountSkills(TestCase):

    PIPELINE = ["ovos-stop-pipeline-plugin-high",
                "ovos-padatious-pipeline-plugin-high"]

    def setUp(self):
        self.minicroft = get_minicroft([SKILL_ID])
        self.skill = self.minicroft.plugin_skills[SKILL_ID].instance
        self._count_threads = []

    def tearDown(self):
        # `_start_infinite_count` runs the handler's `while True` loop on a
        # daemon thread that only re-checks `active_sessions` once per
        # second (after its `time.sleep(1)`). Setting the flag False (via
        # `stop_session`) does not mean that thread has *observed* it yet,
        # so join it first -- clearing the dict out from under a thread
        # still mid-iteration turns its next `active_sessions[sess.session_id]`
        # read into a KeyError, logged as "Error handling event ... :
        # '<session_id>'" and leaking into the next test's minicroft/bus.
        for thread in self._count_threads:
            thread.join(timeout=5)
            self.assertFalse(
                thread.is_alive(),
                "counting thread did not stop within 5s of its session "
                "being marked inactive -- active_sessions was not cleared "
                "to avoid a KeyError race in the still-running handler",
            )
        self.skill.active_sessions.clear()
        if self.minicroft:
            self.minicroft.stop()

    def test_count_to_n_routes_and_speaks(self):
        session = make_session(session_id="count-3", pipeline=self.PIPELINE)
        message = make_utterance_message("count to 3", session=session)
        types = _capture(self.minicroft, message)
        self.assertIn(f"{SKILL_ID}:count_to_n", types,
                      f"'count to 3' did not route to the count intent ({types})")
        self.assertTrue(SPOKE.intersection(types),
                        f"counting produced no spoken output ({types})")

    def _start_infinite_count(self, session):
        """Kick off an unbounded count in the background and wait until it is
        actually running (its session is marked active).

        ``FakeBus.emit`` runs handlers synchronously in the caller's thread, and
        the infinite-count handler never returns, so the emit has to happen on a
        daemon thread or it would block the test forever.
        """
        message = make_utterance_message("count to infinity", session=session)
        thread = threading.Thread(target=self.minicroft.bus.emit, args=(message,),
                                  daemon=True)
        thread.start()
        self._count_threads.append(thread)
        deadline = time.time() + 10
        while time.time() < deadline:
            if self.skill.active_sessions.get(session.session_id):
                return
            time.sleep(0.1)
        self.fail("infinite count never started")

    def test_stop_active_skill_halts_counting(self):
        # skill is in the session's active list -> a bare "stop" targets it
        session = make_session(session_id="123", pipeline=self.PIPELINE)
        session.activate_skill(SKILL_ID)
        self._start_infinite_count(session)

        stop = make_utterance_message("stop", session=session)
        types = _capture(self.minicroft, stop)

        self.assertTrue(
            f"{SKILL_ID}.stop.response" in types or "stop:skill" in types,
            f"stop did not reach the counting skill ({types})",
        )
        self.assertFalse(self.skill.active_sessions.get(session.session_id),
                         "counting kept running after stop")

    def test_global_stop_halts_counting(self):
        # skill NOT in the active list -> a bare "stop" falls back to a global
        # stop, which still halts the running count via mycroft.stop
        session = make_session(session_id="456", pipeline=self.PIPELINE)
        self._start_infinite_count(session)

        stop = make_utterance_message("stop", session=session)
        types = _capture(self.minicroft, stop)

        self.assertTrue(STOPPED.intersection(types),
                        f"global stop was not broadcast ({types})")
        self.assertFalse(self.skill.active_sessions.get(session.session_id),
                         "counting kept running after global stop")
