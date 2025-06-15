import time
from typing import Dict

from ovos_bus_client import SessionManager, Session, Message
from ovos_number_parser import pronounce_number, extract_number
from ovos_utils import classproperty
from ovos_utils.process_utils import RuntimeRequirements
from ovos_workshop.decorators import intent_handler
from ovos_workshop.skills import OVOSSkill


class CountSkill(OVOSSkill):

    @classproperty
    def runtime_requirements(self):
        # if this isn't defined the skill will
        # only load if there is internet
        return RuntimeRequirements(
            internet_before_load=False,
            network_before_load=False,
            gui_before_load=False,
            requires_internet=False,
            requires_network=False,
            requires_gui=False,
            no_internet_fallback=True,
            no_network_fallback=True,
            no_gui_fallback=True,
        )

    def initialize(self):
        self.active_sessions: Dict[str, bool] = {}

    def speak_n(self, i: int, lang: str, short_scale: bool = False, ordinals: bool =False):
        try:
            self.speak(pronounce_number(i, lang=lang, short_scale=short_scale, ordinals=ordinals))
        except:
            self.speak(str(i))

    @intent_handler("count_to_N.intent")
    def handle_how_are_you_intent(self, message):
        sess = SessionManager.get(message)
        number = message.data.get("number")
        utterance = message.data.get("utterance")
        short_scale = message.data.get("short_scake") or self.settings.get("short_scale", False)
        if number is None:
            number = extract_number(utterance, lang=sess.lang,
                                    short_scale=short_scale,
                                    ordinals=True)
        else:
            number = int(number)

        ordinal = (not self.voc_match(utterance, "cardinal", lang=sess.lang) and
                    self.voc_match(utterance, "ordinal", lang=sess.lang))
        self.active_sessions[sess.session_id] = True
        if self.voc_match(utterance, "infinity", self.lang):
            n = 1
            while True:
                if not self.active_sessions[sess.session_id]:
                    self.log.debug("Counting aborted")
                    return
                print(n)
                self.speak_n(n, lang=sess.lang, short_scale=short_scale, ordinals=ordinal)
                time.sleep(1)
                n += 1
        else:
            for n in range(1, number + 1):
                if not self.active_sessions[sess.session_id]:
                    self.log.debug("Counting aborted")
                    return
                print(n)
                self.speak_n(n, lang=sess.lang, short_scale=short_scale, ordinals=ordinal)
                time.sleep(1)

        self.active_sessions[sess.session_id] = False

    def can_stop(self, message: Message) -> bool:
        sess = SessionManager.get(message)
        return self.active_sessions.get(sess.session_id, False)

    def stop_session(self, session: Session) -> bool:
        if self.active_sessions.get(session.session_id):
            self.log.debug(f"Stopping session: {session.session_id}")
            self.active_sessions[session.session_id] = False
            return True
        return False
