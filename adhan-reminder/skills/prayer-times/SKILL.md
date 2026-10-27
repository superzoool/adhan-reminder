---
name: prayer-times
description: Show today's prayer times, change the user's city, switch reminder language (Arabic/English), or turn desktop notifications on/off. عرض مواقيت الصلاة أو تغيير المدينة أو لغة التذكير أو تشغيل/إيقاف الإشعارات. Use when the user says "prayer times", "مواقيت الصلاة", "change my city", "غيّر مدينتي", "أنا في جدة/دبي/...", "reminders in English", "خلّ التذكير بالإنجليزي", "stop prayer reminders", "وقف تذكير الصلاة".
---

Launcher: `${CLAUDE_PLUGIN_ROOT}/scripts/run.sh` (finds Python 3.9+ and runs `adhan.py`).
Reply to the user in the language they are writing in.

- **Show times / عرض المواقيت**: `sh "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh" times`
- **Change city / تغيير المدينة**: if the user did not name it, ask for the city and country. Convert both to English, then:
  `sh "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh" set-city "Jeddah" "Saudi Arabia"`
  (Times come from the Aladhan API. Saudi Arabia uses the Umm Al-Qura calendar automatically; other countries get a suitable method. A method number can be passed as a third argument.)
  If fetching fails, ask for another spelling of the city.
- **Reminder language / لغة التذكير**: `... set-lang ar` (Arabic, default) or `... set-lang en` (English). The setting is kept when the city changes.
- **Desktop notifications (macOS / Windows / Linux)**, which work even while Claude is busy with a long command: `... notify on` or `... notify off`. Stop the background process with `... stop`.

- **Always-on notifications (macOS only) / تشغيل دائم**: the watcher normally runs only while a Claude Code session has been active. `... service on` installs a small launchd agent (`~/Library/LaunchAgents/com.adhan-reminder.watcher.plist`) so it starts at login and restarts if it stops; `... service off` removes it; `... service status` shows the state. Run `service on` only after the user agrees.

After any change, show the user the times in a tidy list.
