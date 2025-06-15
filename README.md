# 🧮 Count Skill 

**CountSkill** is a simple skill for [Open Voice OS (OVOS)](https://openvoiceos.org) that counts from 1 to any user-specified number — or even infinitely — speaking each number aloud. It supports both **cardinal** and **ordinal** formats and works offline thanks to `ovos-number-parser`.

> 💡 this skill was made with the purpose of testing the stop pipeline and showing how to use `ovos-number-parser`

---

## 🔧 Features

* 📢 Speaks numbers up to a given limit or infinitely
* 🔢 Supports cardinal (e.g., one, two) and ordinal (e.g., first, second) formats
* 🌍 Multilingual support (depending on the configured language)
* 📴 Fully offline capable — no internet required
* 🛑 Responds to stop requests mid-count
* 🧠 Intelligent number extraction from natural language

---

## 🗣 Example Utterances

> These require matching `*.intent` files in your locale directory.

* “Count to 10”
* “Can you count to twenty-five?”
* “Start counting”
* “Count infinitely”
* “Count to the 5th”

---

## 🧠 How It Works

* Extracts a number from user utterance using `ovos-number-parser`.
* Speaks each number up to the limit using `pronounce_number`.
* Optionally switches between short/long scales and ordinal/cardinal formats.
* Allows interrupting via `stop` or other cancel commands.

If the user requests **infinite counting**, the skill will count indefinitely until explicitly stopped.

---

## 🛑 Stopping the Skill

This skill implements `can_stop()` and `stop_session()` using OVOS session management. It can be interrupted with:

* "Stop"
* "That's enough"
* "Cancel"

---
