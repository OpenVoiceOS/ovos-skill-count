import time
from unittest import TestCase

from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovos_utils import create_daemon
from ovos_utils.log import LOG

from ovoscope import End2EndTest, get_minicroft

# the stop pipeline pings every stop-capable component in parallel, so these
# `*.stop.response` messages arrive in a non-deterministic order (and the exact
# set varies with the installed plugins); ignore them in sequence assertions
STOP_RESPONSES = [
    "ovos.common_play.stop.response",
    "common_query.openvoiceos.stop.response",
    "persona.openvoiceos.stop.response",
    "stop.openvoiceos.stop.response",
]


class TestStopNoSkills(TestCase):

    def setUp(self):
        LOG.set_level("DEBUG")
        self.minicroft = get_minicroft([])  # reuse for speed, but beware if skills keeping internal state

    def tearDown(self):
        if self.minicroft:
            self.minicroft.stop()
        LOG.set_level("CRITICAL")

    def test_exact(self):
        session = Session("123")
        session.pipeline = ['ovos-stop-pipeline-plugin-high']
        message = Message("recognizer_loop:utterance",
                          {"utterances": ["stop"], "lang": "en-US"},
                          {"session": session.serialize()})

        test = End2EndTest(
            minicroft=self.minicroft,
            skill_ids=[],
            eof_msgs=["ovos.utterance.handled"],
            flip_points=["recognizer_loop:utterance"],
            # the per-pipeline `*.stop.response` messages arrive in a
            # non-deterministic order (parallel fan-out), so we ignore them
            # and only assert the deterministic stop skeleton
            ignore_messages=STOP_RESPONSES,
            source_message=message,
            expected_messages=[
                message,
                Message("stop.openvoiceos.activate", {}),  # stop pipeline counts as active_skill

                # INTENT §8.1: the dispatcher announces the resolved intent and
                # brackets the handler with the ovos.intent.* lifecycle
                Message("ovos.intent.matched", {"intent_name": "stop:global"}),
                Message("ovos.intent.handler.start", {"intent_name": "global"}),

                Message("stop:global", {}),  # global stop, no active skill
                Message("mycroft.skill.handler.start", {"name": "StopService.handle_global_stop"}),
                Message("mycroft.stop", {}),
                Message("mycroft.skill.handler.complete", {"name": "StopService.handle_global_stop"}),

                Message("ovos.intent.handler.complete", {"intent_name": "global"}),
                Message("ovos.utterance.handled", {})
            ]
        )

        test.execute()

    def test_not_exact_high(self):
        session = Session("123")
        session.pipeline = ['ovos-stop-pipeline-plugin-high']
        message = Message("recognizer_loop:utterance",
                          {"utterances": ["could you stop that"], "lang": "en-US"},
                          {"session": session.serialize()})

        test = End2EndTest(
            minicroft=self.minicroft,
            skill_ids=[],
            eof_msgs=["ovos.utterance.handled"],
            flip_points=["recognizer_loop:utterance"],
            source_message=message,
            expected_messages=[
                message,
                Message("mycroft.audio.play_sound", {"uri": "snd/error.mp3"}),
                # INTENT §9.3: the intent layer reports the miss as ovos.intent.unmatched
                Message("ovos.intent.unmatched", {}),
                Message("ovos.utterance.handled", {}),
            ]
        )

        test.execute()

    def test_not_exact_med(self):
        session = Session("123")
        session.pipeline = ['ovos-stop-pipeline-plugin-medium']
        message = Message("recognizer_loop:utterance",
                          {"utterances": ["could you stop that"], "lang": "en-US"},
                          {"session": session.serialize()})

        test = End2EndTest(
            minicroft=self.minicroft,
            skill_ids=[],
            eof_msgs=["ovos.utterance.handled"],
            flip_points=["recognizer_loop:utterance"],
            # the per-pipeline `*.stop.response` messages arrive in a
            # non-deterministic order (parallel fan-out), so we ignore them
            # and only assert the deterministic stop skeleton
            ignore_messages=STOP_RESPONSES,
            source_message=message,
            expected_messages=[
                message,
                Message("stop.openvoiceos.activate", {}),  # stop pipeline counts as active_skill

                # INTENT §8.1: the dispatcher announces the resolved intent and
                # brackets the handler with the ovos.intent.* lifecycle
                Message("ovos.intent.matched", {"intent_name": "stop:global"}),
                Message("ovos.intent.handler.start", {"intent_name": "global"}),

                Message("stop:global", {}),  # global stop, no active skill
                Message("mycroft.skill.handler.start", {"name": "StopService.handle_global_stop"}),
                Message("mycroft.stop", {}),
                Message("mycroft.skill.handler.complete", {"name": "StopService.handle_global_stop"}),

                Message("ovos.intent.handler.complete", {"intent_name": "global"}),
                Message("ovos.utterance.handled", {})
            ]
        )

        test.execute()


class TestCountSkills(TestCase):

    def setUp(self):
        LOG.set_level("DEBUG")
        self.skill_id = "ovos-skill-count.openvoiceos"
        self.minicroft = get_minicroft([self.skill_id])  # reuse for speed, but beware if skills keeping internal state
        # to make tests easier to grok
        self.ignore_messages = ["speak",
                                "ovos.utterance.speak",  # speak under ovos.* namespace
                                # TTS playback boundaries (AUDIO-1 §5) fire once per
                                # spoken number and race with the counting daemon, so
                                # their count and position are non-deterministic;
                                # the speech.stop that silences an in-flight number
                                # only fires when playback is active at stop time
                                "recognizer_loop:audio_output_start",
                                "recognizer_loop:audio_output_end",
                                "mycroft.audio.speech.stop",
                                ] + STOP_RESPONSES

    def tearDown(self):
        if self.minicroft:
            self.minicroft.stop()
        LOG.set_level("CRITICAL")

    def test_count(self):
        session = Session("123")
        session.pipeline = ['ovos-stop-pipeline-plugin-high', "ovos-padatious-pipeline-plugin-high"]

        message = Message("recognizer_loop:utterance",
                          {"utterances": ["count to 3"], "lang": "en-US"},
                          {"session": session.serialize()})

        # first count to 10 to validate skill is working
        activate_skill = [
            message,
            Message("ovos-skill-count.openvoiceos.activate", {}),  # skill is activated

            # INTENT §8.1: dispatcher lifecycle brackets the skill intent handler
            Message("ovos.intent.matched",
                    {"intent_name": "ovos-skill-count.openvoiceos:count_to_n.intent"}),
            Message("ovos.intent.handler.start", {"intent_name": "count_to_n.intent"}),

            Message("ovos-skill-count.openvoiceos:count_to_n.intent", {}),  # intent triggers

            Message("mycroft.skill.handler.start", {
                "name": "CountSkill.handle_how_are_you_intent"
            }),
            # here would be N speak messages + their audio playback boundaries,
            # but we ignore them in this test
            Message("mycroft.skill.handler.complete", {
                "name": "CountSkill.handle_how_are_you_intent"
            }),

            Message("ovos.intent.handler.complete", {"intent_name": "count_to_n.intent"}),
            Message("ovos.utterance.handled", {})
        ]
        test = End2EndTest(
            minicroft=self.minicroft,
            skill_ids=[],
            eof_msgs=["ovos.utterance.handled"],
            flip_points=["recognizer_loop:utterance"],
            ignore_messages=self.ignore_messages,
            source_message=message,
            expected_messages=activate_skill
        )
        test.execute()

    def test_count_infinity_active(self):
        session = Session("123")
        session.pipeline = ['ovos-stop-pipeline-plugin-high',
                            "ovos-padatious-pipeline-plugin-high"]

        def make_it_count():
            nonlocal session
            message = Message("recognizer_loop:utterance",
                              {"utterances": ["count to infinity"], "lang": "en-US"},
                              {"session": session.serialize()})
            session.activate_skill(self.skill_id)  # ensure in active skill list
            self.minicroft.bus.emit(message)

        # count to infinity, the skill will keep running in the background
        create_daemon(make_it_count)

        time.sleep(3)

        message = Message("recognizer_loop:utterance",
                          {"utterances": ["stop"], "lang": "en-US"},
                          {"session": session.serialize()})  # skill in active list now

        stop_skill_active = [
            message,
            Message("ovos-skill-count.openvoiceos.stop.ping",
                    {"skill_id":self.skill_id}),
            Message("skill.stop.pong",
                    {"skill_id": self.skill_id, "can_handle": True},
                    {"skill_id": self.skill_id}),

            Message("stop.openvoiceos.activate",
                    context={"skill_id": "stop.openvoiceos"}),

            # INTENT §8.1: dispatcher lifecycle brackets the stop handler
            Message("ovos.intent.matched", {"intent_name": "stop:skill"},
                    {"skill_id": "stop.openvoiceos"}),
            Message("ovos.intent.handler.start", {"intent_name": "skill"},
                    {"skill_id": "stop.openvoiceos"}),

            Message("stop:skill",
                    {"skill_id": self.skill_id},
                    {"skill_id": "stop.openvoiceos"}),
            Message("mycroft.skill.handler.start",
                    {"name": "StopService.handle_skill_stop"},
                    {"skill_id": "stop.openvoiceos"}),
            Message(f"{self.skill_id}.stop",
                    context={"skill_id": "stop.openvoiceos"}),
            Message(f"{self.skill_id}.stop.response",
                    {"skill_id": self.skill_id, "result": True},
                    {"skill_id": self.skill_id}),

            # skill callback to stop everything (the TTS-silencing speech.stop
            # that may follow is ignored — it only fires mid-playback)
            Message("ovos.skills.converse.force_timeout", {"skill_id": self.skill_id},
                    {"skill_id": self.skill_id}),

            # the stop handler completes and the dispatcher closes its lifecycle
            Message("mycroft.skill.handler.complete",
                    {"name": "StopService.handle_skill_stop"},
                    {"skill_id": "stop.openvoiceos"}),
            Message("ovos.intent.handler.complete", {"intent_name": "skill"},
                    {"skill_id": "stop.openvoiceos"}),
            Message("ovos.utterance.handled", {},
                    {"skill_id": "stop.openvoiceos"})
        ]
        test = End2EndTest(
            minicroft=self.minicroft,
            # inject_active=[self.skill_id],  # ensure this skill is in active skills list for the test
            skill_ids=[],
            eof_msgs=["ovos.utterance.handled"],
            flip_points=["recognizer_loop:utterance"],
            ignore_messages=self.ignore_messages,
            source_message=message,
            expected_messages=stop_skill_active
        )
        test.execute()

    def test_count_infinity_global(self):
        session = Session("123")
        session.pipeline = ['ovos-stop-pipeline-plugin-high',
                            "ovos-padatious-pipeline-plugin-high"]

        def make_it_count():
            message = Message("recognizer_loop:utterance",
                              {"utterances": ["count to infinity"], "lang": "en-US"},
                              {"session": session.serialize()})
            self.minicroft.bus.emit(message)

        # count to infinity, the skill will keep running in the background
        create_daemon(make_it_count)

        time.sleep(3)

        # NOTE: skill not in active skill list for this Session, global stop will match instead
        # this doesnt typically happen at runtime, but possible since clients send whatever Session they want
        message = Message("recognizer_loop:utterance",
                          {"utterances": ["stop"], "lang": "en-US"},
                          {"session": session.serialize()})
        stop_skill_from_global = [
            message,
            Message("stop.openvoiceos.activate", {}),  # stop pipeline counts as active_skill

            # INTENT §8.1: dispatcher lifecycle brackets the global stop handler
            Message("ovos.intent.matched", {"intent_name": "stop:global"}),
            Message("ovos.intent.handler.start", {"intent_name": "global"}),

            Message("stop:global", {}),  # global stop, no active skill
            Message("mycroft.skill.handler.start", {"name": "StopService.handle_global_stop"}),
            Message("mycroft.stop", {}),

            Message(f"{self.skill_id}.stop.response",
                    {"skill_id": self.skill_id, "result": True}),
            Message("mycroft.skill.handler.complete", {"name": "StopService.handle_global_stop"}),
            Message("ovos.intent.handler.complete", {"intent_name": "global"}),
            Message("ovos.utterance.handled", {})
        ]
        test = End2EndTest(
            minicroft=self.minicroft,
            skill_ids=[],
            eof_msgs=["ovos.utterance.handled"],
            flip_points=["recognizer_loop:utterance"],
            ignore_messages=self.ignore_messages,
            source_message=message,
            expected_messages=stop_skill_from_global
        )
        test.execute()

