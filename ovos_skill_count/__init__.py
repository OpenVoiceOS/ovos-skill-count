import time
from fractions import Fraction
from typing import Dict

from numtag import NumberMention, Reason, Scale, SpokenForm, UnsupportedLanguageError, spell, tag_numbers
from ovos_bus_client import SessionManager, Session, Message
from ovos_number_parser import pronounce_number
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
            text = spell(str(i), lang,
                         form=SpokenForm.ORDINAL if ordinals else SpokenForm.CARDINAL,
                         scale=Scale.SHORT if short_scale else Scale.LONG)[0].text
        except UnsupportedLanguageError:
            # numtag has no writer for this language (fa, oc)
            try:
                text = pronounce_number(i, lang=lang, short_scale=short_scale, ordinals=ordinals)
            except Exception:
                text = str(i)
        self.speak(text)

    @staticmethod
    def _read_number(text: str, lang: str, scale: Scale | None) -> NumberMention | None:
        """The last number of the text: "count from one to ten" counts to ten.
        A lone article is no number."""
        mentions = [m for m in tag_numbers(text, lang, scale=scale)
                    if Reason.ARTICLE not in m.reasons]
        return mentions[-1] if mentions else None

    @intent_handler("count_to_n.intent")
    def handle_how_are_you_intent(self, message):
        sess = SessionManager.get(message)
        utterance = message.data.get("utterance")
        # the scale the user names, else the language's own scale
        if "short_scale" in message.data:
            scale = Scale.SHORT if message.data["short_scale"] else Scale.LONG
        elif self.voc_match(utterance, "long_scale", lang=sess.lang):
            scale = Scale.LONG
        elif self.voc_match(utterance, "short_scale", lang=sess.lang):
            scale = Scale.SHORT
        else:
            scale = None
        mention = self._read_number(str(message.data.get("number") or utterance),
                                    sess.lang, scale)
        number = int(Fraction(mention.value)) if mention else None
        short_scale = (scale or (mention and mention.number_scale)) == Scale.SHORT

        infinite = self.voc_match(utterance, "infinity", lang=sess.lang)
        if not infinite and number is None:
            # "count to infinity"/"count forever" legitimately carry no
            # number at all, so that path is exempt from this guard.
            # TODO - prompt user instead with get_response
            self.speak_dialog("failed_extract_number")
            return

        ordinal = (not self.voc_match(utterance, "cardinal", lang=sess.lang) and
                    self.voc_match(utterance, "ordinal", lang=sess.lang))
        self.active_sessions[sess.session_id] = True
        if infinite:
            n = 1
            while True:
                if not self.active_sessions[sess.session_id]:
                    self.log.debug("Counting aborted")
                    return
                self.speak_n(n, lang=sess.lang, short_scale=short_scale, ordinals=ordinal)
                time.sleep(1)
                n += 1
        else:
            for n in range(1, number + 1):
                if not self.active_sessions[sess.session_id]:
                    self.log.debug("Counting aborted")
                    return
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
