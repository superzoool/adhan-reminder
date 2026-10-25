#!/usr/bin/env python3
"""Adhan reminder: prayer times from the Aladhan API, hook + watcher entrypoints.

Usage:
  adhan.py hook            # called by Claude Code hooks (event JSON on stdin)
  adhan.py watch           # background loop: desktop notification at adhan / +10 min
  adhan.py set-city CITY [COUNTRY] [METHOD]
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

def adhan_message(prayer):
    name = AR[prayer]
    return (
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "   ﷽   ✦ حان الآن موعد أذان %s ✦\n"
        "   «حيّ على الصلاة، حيّ على الفلاح»\n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛" % name
    )


def pray_message(prayer):
    name = AR[prayer]
    return (
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "   🕌 قم صلِّ %s يا غالي ✦\n"
        "   مضى %d دقائق على الأذان — الشغل ما يطير، والصلاة أولى 🤍\n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛" % (name, GAP_MIN)
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
                out.append(pray_message(p))
        elif t <= now < gap:
            if k_adhan not in state:
                state[k_adhan] = True
                out.append(adhan_message(p))
    save(STATE, state)
    return out


# ---------- hook entrypoint ----------

def cmd_hook():
    try:
        event = json.load(sys.stdin).get("hook_event_name", "")
    except Exception:
        event = ""
    cfg = load(CONFIG, None)
    result = {}

    if not cfg:
        if event == "SessionStart":
            result = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": (
                "[adhan-reminder] لم يحدد المستخدم مدينته بعد. اسأله في أول رد: «في أي مدينة أنت؟ "
                "(الرياض افتراضيًا)» ثم شغّل: sh \"" + os.path.join(os.path.dirname(os.path.abspath(__file__)), "run.sh") + "\" "
                "set-city \"<المدينة بالإنجليزي>\" \"<الدولة بالإنجليزي>\" . "
                "لو قال الرياض أو ما غيّر، شغّل set-city Riyadh \"Saudi Arabia\"."
            )}}
    else:
        msgs = due_messages(cfg, "hook")
        if msgs:
            result["systemMessage"] = "\n\n".join(msgs)
        if event == "SessionStart":
            ensure_watcher(cfg)
            if msgs and event in ("SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse"):
                result["hookSpecificOutput"] = {"hookEventName": event, "additionalContext":
                    "[adhan-reminder] ذكّر المستخدم بالصلاة بإيجاز في ردك القادم."}
        elif msgs and event in ("UserPromptSubmit", "PreToolUse", "PostToolUse"):
            result["hookSpecificOutput"] = {"hookEventName": event, "additionalContext":
                "[adhan-reminder] وصلت للمستخدم رسالة موعد صلاة. أشر لها بإيجاز في ردك القادم."}
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
                notify("🕌 مواقيت الصلاة", " — ".join(l.strip() for l in lines if l.strip()))
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
    cfg = {"city": city, "country": country, "method": method, "os_notify": load(CONFIG, {}).get("os_notify", True)}
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


def cmd_times():
    cfg = load(CONFIG, None)
    if not cfg:
        sys.exit("لم تُحدد المدينة بعد. شغّل set-city")
    tz, times = today_times(cfg)
    print("مواقيت الصلاة اليوم — %s, %s" % (cfg["city"], cfg["country"]))
    for p in PRAYERS:
        print("  %-8s %s" % (AR[p], times[p].strftime("%I:%M").lstrip("0") + (" ص" if times[p].hour < 12 else " م")))


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
