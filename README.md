# Count Skill

CountSkill is a skill for [Open Voice OS (OVOS)](https://openvoiceos.org). It counts aloud from 1 to a number the user gives, or counts without a limit until stopped. It supports cardinal and ordinal formats and works offline, using [ovos-number-parser](https://github.com/OpenVoiceOS/ovos-number-parser) to extract and pronounce numbers.

## Install

```bash
pip install ovos-skill-count
```

## Usage

Say one of these to start the skill:

* "Count to 10"
* "Can you count to twenty-five?"
* "Start counting"
* "Count infinitely"
* "Count to the 5th"

These utterances need matching `*.intent` files in your locale directory.

The skill extracts a number from the utterance with `ovos-number-parser`, then speaks each number up to that limit with `pronounce_number`. It supports short and long scales, and cardinal or ordinal formats, depending on the configured language. If the user asks for infinite counting, the skill counts without a limit until stopped.

The skill implements `can_stop()` and `stop_session()` with OVOS session management. Say one of these to stop a count in progress:

* "Stop"
* "That's enough"
* "Cancel"

## Related projects

* [OpenVoiceOS/ovos-number-parser](https://github.com/OpenVoiceOS/ovos-number-parser) — parses and pronounces numbers; this skill uses it to read numbers aloud.

## License

See [LICENSE](LICENSE).
