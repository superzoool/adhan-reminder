#!/usr/bin/env python3
"""Adhan reminder: prayer times from the Aladhan API, hook + watcher entrypoints.

Usage:
  adhan.py hook            # called by Claude Code hooks (event JSON on stdin)
  adhan.py watch           # background loop: desktop notification at adhan / +10 min
  adhan.py set-city CITY [COUNTRY] [METHOD]
  adhan.py set-lang ar|en  # language of the reminder messages (default: ar)
  adhan.py times           # print today's times
  adhan.py status          # print config state (JSON)
  adhan.py notify on|off   # toggle desktop notifications (macOS / Windows / Linux)
  adhan.py stop            # stop background watcher
"""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

IS_WIN = sys.platform == "win32"

HOME = os.path.expanduser("~/.claude/adhan")
CONFIG = os.path.join(HOME, "config.json")
STATE = os.path.join(HOME, "state.json")
PIDFILE = os.path.join(HOME, "watcher.pid")

PRAYERS = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
AR = {"Fajr": "الفجر", "Dhuhr": "الظهر", "Asr": "العصر", "Maghrib": "المغرب", "Isha": "العشاء"}
EN = {"Fajr": "Fajr", "Dhuhr": "Dhuhr", "Asr": "Asr", "Maghrib": "Maghrib", "Isha": "Isha"}
LANGS = ("ar", "en")
GAP_MIN = 10          # minutes between the adhan message and the "go pray" message
LATE_WINDOW_MIN = 25  # how long after the +10 mark the "go pray" message may still show
WATCH_MAX_HOURS = 12

# Aladhan calculation methods: 4 = Umm Al-Qura (Makkah), 3 = MWL, 5 = Egyptian, ...
METHOD_BY_COUNTRY = {
    "saudi arabia": 4, "السعودية": 4, "kuwait": 9, "qatar": 10, "united arab emirates": 16,
    "uae": 16, "bahrain": 8, "oman": 4, "yemen": 4, "egypt": 5, "turkey": 13, "türkiye": 13,
    "jordan": 23, "morocco": 21, "algeria": 19, "tunisia": 18, "singapore": 11, "malaysia": 17,
    "indonesia": 20, "france": 12, "iran": 7, "pakistan": 1, "india": 1, "bangladesh": 1,
    "united states": 2, "usa": 2, "canada": 2, "united kingdom": 15, "uk": 15,
}


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save(path, data):
    os.makedirs(HOME, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def get_tz(name):
    """IANA zone by name. Windows has no system tz database (and no tzdata package by
    default), so fall back to the machine's own timezone instead of crashing."""
    if (name or "UTC") == "UTC":
        return timezone.utc
    try:
        return ZoneInfo(name)
    except Exception:
        return datetime.now().astimezone().tzinfo


def lang_of(cfg):
    lang = (cfg or {}).get("lang", "ar")
    return lang if lang in LANGS else "ar"


def default_method(country):
    return METHOD_BY_COUNTRY.get((country or "").strip().lower(), 3)


# ---------- prayer times ----------

def month_calendar(cfg, year, month):
    """Month of timings, cached on disk. Raises on network failure with no cache."""
    key = "%s_%s_%s_%04d%02d.json" % (cfg["city"], cfg["country"], cfg["method"], year, month)
    key = "".join(c if c.isalnum() or c in "._-" else "_" for c in key)
    path = os.path.join(HOME, "cache", key)
    cached = load(path, None)
    if cached:
        return cached
    q = urllib.parse.urlencode({"city": cfg["city"], "country": cfg["country"], "method": cfg["method"]})
    url = "https://api.aladhan.com/v1/calendarByCity/%d/%d?%s" % (year, month, q)
    with urllib.request.urlopen(url, timeout=15) as r:
        body = json.load(r)
    if body.get("code") != 200 or not body.get("data"):
        raise RuntimeError("Aladhan: %s" % body.get("data", body))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    save(path, body["data"])
    return body["data"]


def today_times(cfg, now_utc=None):
    """Returns (tz, {prayer: aware datetime}) for today in the city's timezone."""
    now_utc = now_utc or datetime.now(timezone.utc)
    tz = get_tz(cfg.get("tz") or "UTC")
    now = now_utc.astimezone(tz)
    data = month_calendar(cfg, now.year, now.month)
    day = data[now.day - 1]
    tz = get_tz(day["meta"]["timezone"])
    now = now_utc.astimezone(tz)
    times = {}
    for p in PRAYERS:
        hh, mm = day["timings"][p][:5].split(":")
        times[p] = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
    return tz, times


# ---------- messages ----------

ADHAN_LINES = {
    "ar": [
        "استعدّ، دقائق من الراحة والسكينة تنتظرك 🤍",
        "حان وقت لقاء ربك، الله يتقبل منك 🌿",
        "وقفة سكينة في وسط الشغل، الله يبارك لك فيه 🕊️",
        "أبشر بالخير، الصلاة راحة للقلب ✨",
        "الله يعينك ويقوّيك على طاعته 🤲",
        "يا بطل، هذي استراحة الروح، لا تفوّتها 💛",
    ],
    "en": [
        "Get ready: a few calm minutes are waiting for you 🤍",
        "It is time to meet your Lord. May Allah accept it from you 🌿",
        "A moment of peace in the middle of work. May Allah bless your time 🕊️",
        "Good news ahead: prayer is rest for the heart ✨",
        "May Allah help you and strengthen you in His obedience 🤲",
        "You've got this. This is the break your soul needs 💛",
    ],
}

PRAY_LINES = {
    "ar": [
        "راحة قلبك في سجدة، والتوفيق من الله 🤍",
        "دقائق قليلة بينك وبين ربك تنوّر لك يومك 🌿",
        "الله يبارك في وقتك وشغلك 🤲",
        "الصلاة نور، والشغل بعدها أخف بإذن الله ✨",
        "أنت أقوى بصلاتك، قوم وارجع أنشط 💪",
        "قدّم صلاتك، والبركة في وقتك بإذن الله 🌸",
        "استرح مع ربك، وارجع بهمّة جديدة ⭐",
        "ربنا يتقبل منك ويكتب لك الأجر 🤍",
        "قوم يا بطل، الصلاة تنتظرك 💛",
        "الله يعينك، خطوة صغيرة وتكسب راحة البال 🕊️",
    ],
    "en": [
        "The peace of your heart is in one prostration 🤍",
        "A few minutes with your Lord brighten the rest of your day 🌿",
        "May Allah bless your time and your work 🤲",
        "Prayer is light, and work feels lighter after it ✨",
        "You are stronger after prayer. Go, then come back refreshed 💪",
        "Put prayer first, and the barakah follows in sha Allah 🌸",
        "Rest with your Lord and return with new energy ⭐",
        "May Allah accept it from you and reward you 🤍",
        "You've got this, go pray 💛",
        "May Allah help you. One small step and you win peace of mind 🕊️",
    ],
}


def _pick(pool, lang, seed):
    lines = pool[lang]
    return lines[seed % len(lines)]


def adhan_message(prayer, lang="ar", seed=0):
    if lang == "en":
        return (
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "   ﷽   ✦ It is time for the %s adhan ✦\n"
            "   “Come to prayer, come to success”\n"
            "   %s\n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛" % (EN[prayer], _pick(ADHAN_LINES, lang, seed))
        )
    return (
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "   ﷽   ✦ حان الآن موعد أذان %s ✦\n"
        "   «حيّ على الصلاة، حيّ على الفلاح»\n"
        "   %s\n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛" % (AR[prayer], _pick(ADHAN_LINES, lang, seed))
    )


def pray_message(prayer, lang="ar", seed=0):
    if lang == "en":
        return (
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "   🕌 Get up and pray %s ✦\n"
            "   %d minutes have passed since the adhan\n"
            "   %s\n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛" % (EN[prayer], GAP_MIN, _pick(PRAY_LINES, lang, seed))
        )
    return (
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "   🕌 قوم صلِّ %s ✦\n"
        "   مضى %d دقائق على الأذان\n"
        "   %s\n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛" % (AR[prayer], GAP_MIN, _pick(PRAY_LINES, lang, seed))
    )


def due_messages(cfg, channel):
    """Messages not yet delivered on this channel. Marks them delivered."""
    try:
        tz, times = today_times(cfg)
    except Exception:
        return []
    now = datetime.now(tz)
    state = load(STATE, {})
    today = now.strftime("%Y-%m-%d")
    seed = now.toordinal() * len(PRAYERS)  # different line each prayer and each day
    # drop old days
    state = {k: v for k, v in state.items() if k.startswith(today)}
    out = []
    for p in PRAYERS:
        t = times[p]
        k_adhan = "%s|%s|%s|adhan" % (today, p, channel)
        k_pray = "%s|%s|%s|pray" % (today, p, channel)
        gap = t + timedelta(minutes=GAP_MIN)
        if gap <= now < gap + timedelta(minutes=LATE_WINDOW_MIN):
            if k_pray not in state:
                state[k_adhan] = state[k_pray] = True
                out.append(pray_message(p, lang_of(cfg), seed + PRAYERS.index(p)))
        elif t <= now < gap:
            if k_adhan not in state:
                state[k_adhan] = True
                out.append(adhan_message(p, lang_of(cfg), seed + PRAYERS.index(p)))
    save(STATE, state)
    return out


# ---------- hook entrypoint ----------

REMIND_START = {
    "ar": "[adhan-reminder] ذكّر المستخدم بالصلاة بإيجاز في ردك القادم.",
    "en": "[adhan-reminder] Briefly remind the user to pray in your next reply (in English).",
}
REMIND_MID = {
    "ar": "[adhan-reminder] وصلت للمستخدم رسالة موعد صلاة. أشر لها بإيجاز في ردك القادم.",
    "en": "[adhan-reminder] A prayer-time message was just shown to the user. Briefly acknowledge it in your next reply (in English).",
}


def cmd_hook():
    try:
        event = json.load(sys.stdin).get("hook_event_name", "")
    except Exception:
        event = ""
    cfg = load(CONFIG, None)
    result = {}

    if not cfg or not cfg.get("city"):
        if event == "SessionStart":
            run = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run.sh")
            result = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": (
                "[adhan-reminder] The user has not set a city yet. In your first reply (in the user's language), "
                "ask: which city are you in (default: Riyadh), and should the prayer reminders be in Arabic or English? "
                "(لم يحدد المستخدم مدينته بعد: اسأله عن مدينته ولغة الرسائل عربي/إنجليزي، الرياض والعربي افتراضيًا). "
                "Then run: sh \"" + run + "\" set-city \"<city in English>\" \"<country in English>\" "
                "and: sh \"" + run + "\" set-lang ar|en . "
                "If they say Riyadh or do not change it: set-city Riyadh \"Saudi Arabia\"."
            )}}
    else:
        msgs = due_messages(cfg, "hook")
        if msgs:
            result["systemMessage"] = "\n\n".join(msgs)
        if event == "SessionStart":
            ensure_watcher(cfg)
            if msgs and event in ("SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse"):
                result["hookSpecificOutput"] = {"hookEventName": event, "additionalContext":
                    REMIND_START[lang_of(cfg)]}
        elif msgs and event in ("UserPromptSubmit", "PreToolUse", "PostToolUse"):
            result["hookSpecificOutput"] = {"hookEventName": event, "additionalContext":
                REMIND_MID[lang_of(cfg)]}
    if result:
        print(json.dumps(result, ensure_ascii=False))


# ---------- watcher (desktop notifications while Claude is busy) ----------

def _which(name):
    from shutil import which
    return which(name)


def notify(title, text):
    try:
        if sys.platform == "darwin":
            esc = lambda t: t.replace("\\", "\\\\").replace('"', '\\"')
            script = 'display notification "%s" with title "%s" sound name "Glass"' % (esc(text), esc(title))
            subprocess.run(["osascript", "-e", script], timeout=10, check=False)
        elif IS_WIN:
            ps = (
                "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null;"
                "$x=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
                "$t=$x.GetElementsByTagName('text');"
                "$t.Item(0).AppendChild($x.CreateTextNode($env:ADHAN_TITLE)) | Out-Null;"
                "$t.Item(1).AppendChild($x.CreateTextNode($env:ADHAN_TEXT)) | Out-Null;"
                "$app='{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe';"
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show([Windows.UI.Notifications.ToastNotification]::new($x))"
            )
            env = dict(os.environ, ADHAN_TITLE=title, ADHAN_TEXT=text)
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                           env=env, timeout=15, check=False, creationflags=0x08000000,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif _which("notify-send"):
            subprocess.run(["notify-send", "-a", "adhan-reminder", "-u", "critical", title, text],
                           timeout=10, check=False)
    except Exception:
        pass


def notify_supported():
    return sys.platform == "darwin" or IS_WIN or bool(_which("notify-send"))


def pid_alive(pid):
    if IS_WIN:
        # os.kill(pid, 0) would TERMINATE the process on Windows, so ask the OS instead.
        try:
            import ctypes
            k32 = ctypes.windll.kernel32
            h = k32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            code = ctypes.c_ulong()
            ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
            k32.CloseHandle(h)
            return bool(ok) and code.value == 259  # STILL_ACTIVE
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def ensure_watcher(cfg):
    if not cfg.get("os_notify", True) or not notify_supported():
        return
    pid = load(PIDFILE, {}).get("pid")
    if pid and pid_alive(pid):
        return
    kwargs = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if IS_WIN:
        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
        kwargs["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "watch"], **kwargs)


def cmd_watch():
    save(PIDFILE, {"pid": os.getpid()})
    end = time.time() + WATCH_MAX_HOURS * 3600
    while time.time() < end:
        cfg = load(CONFIG, None)
        if cfg and cfg.get("os_notify", True):
            for m in due_messages(cfg, "os"):
                lines = [l.strip(" ┃") for l in m.splitlines() if "━" not in l]
                notify("🕌 مواقيت الصلاة" if lang_of(cfg) == "ar" else "🕌 Prayer times", " — ".join(l.strip() for l in lines if l.strip()))
        time.sleep(20)
    try:
        os.remove(PIDFILE)
    except OSError:
        pass


def cmd_stop():
    pid = load(PIDFILE, {}).get("pid")
    if pid and pid_alive(pid):
        if IS_WIN:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.kill(pid, 15)
        print("stopped watcher", pid)
    else:
        print("no watcher running")


# ---------- user commands ----------

def cmd_set_city(args):
    if not args:
        sys.exit("usage: set-city CITY [COUNTRY] [METHOD]")
    city = args[0]
    country = args[1] if len(args) > 1 else "Saudi Arabia"
    method = int(args[2]) if len(args) > 2 else default_method(country)
    old = load(CONFIG, {})
    cfg = {"city": city, "country": country, "method": method,
           "os_notify": old.get("os_notify", True), "lang": lang_of(old)}
    now = datetime.now(timezone.utc)
    try:
        data = month_calendar(cfg, now.year, now.month)
    except Exception as e:
        sys.exit("تعذّر جلب المواقيت لـ %s, %s: %s" % (city, country, e))
    cfg["tz"] = data[0]["meta"]["timezone"]
    save(CONFIG, cfg)
    print("تم الحفظ: %s, %s (طريقة الحساب: %s، التوقيت: %s)" % (
        city, country, data[0]["meta"]["method"]["name"], cfg["tz"]))
    cmd_times()


def cmd_set_lang(args):
    if not args or args[0] not in LANGS:
        sys.exit("usage: set-lang ar|en")
    cfg = load(CONFIG, {})
    cfg["lang"] = args[0]
    save(CONFIG, cfg)
    print("lang =", cfg["lang"])


def cmd_times():
    cfg = load(CONFIG, None)
    if not cfg or not cfg.get("city"):
        sys.exit("لم تُحدد المدينة بعد. شغّل set-city  /  No city set yet. Run set-city")
    tz, times = today_times(cfg)
    en = lang_of(cfg) == "en"
    print(("Prayer times today — %s, %s" if en else "مواقيت الصلاة اليوم — %s, %s") % (cfg["city"], cfg["country"]))
    for p in PRAYERS:
        t = times[p]
        clock = t.strftime("%I:%M").lstrip("0")
        suffix = (" AM" if t.hour < 12 else " PM") if en else (" ص" if t.hour < 12 else " م")
        print("  %-8s %s" % (EN[p] if en else AR[p], clock + suffix))


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    cmd, args = (sys.argv[1] if len(sys.argv) > 1 else "times"), sys.argv[2:]
    if cmd == "hook":
        cmd_hook()
    elif cmd == "watch":
        cmd_watch()
    elif cmd == "set-city":
        cmd_set_city(args)
    elif cmd == "set-lang":
        cmd_set_lang(args)
    elif cmd == "times":
        cmd_times()
    elif cmd == "status":
        print(json.dumps(load(CONFIG, {}), ensure_ascii=False))
    elif cmd == "notify":
        cfg = load(CONFIG, {})
        cfg["os_notify"] = bool(args) and args[0] == "on"
        save(CONFIG, cfg)
        print("os_notify =", cfg["os_notify"])
    elif cmd == "stop":
        cmd_stop()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
