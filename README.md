# 🕌 adhan-reminder — تذكير الصلاة لـ Claude Code

**[English](#english) · [العربية](#العربية)**

> 💻 **Laptop/desktop only · مخصص للابتوب والكمبيوتر فقط.**
> It runs inside Claude Code on your computer. It does not work on mobile or in the Claude app/web.
> يعمل داخل Claude Code على جهازك، ولا يعمل على الجوال ولا على تطبيق Claude أو الموقع.

---

## English

A Claude Code plugin that reminds you of prayer times while you work. When the adhan time arrives, a decorated message appears inside Claude, and another one follows **10 minutes later**: "Time to pray".

### Features
- Reminder messages in **Arabic or English** (your choice).
- Messages appear between Claude's steps, even while it is busy with a task.
- Optional desktop notification with sound (background process) that reaches you even when Claude is running a long command: macOS, Windows, Linux.
- Asks for your city on first use; change it any time.
- Prayer times from the [Aladhan API](https://aladhan.com/prayer-times-api) (Umm Al-Qura calendar for Saudi Arabia, suitable methods for other countries).
- 12-hour clock.

### Install
```bash
claude plugin marketplace add superzoool/adhan-reminder
claude plugin install adhan-reminder@ahmed-plugins
```

> 🔄 **Restart Claude Code** (or start a new session) after installing so the plugin loads.

### Usage
- First session: Claude asks for your city and your preferred language (Riyadh and Arabic by default).
- Just tell Claude: "prayer times", "change my city to Dubai", "switch reminders to English", or "stop prayer notifications".
- Prefer the terminal? From a clone of this repo:

```bash
sh adhan-reminder/scripts/run.sh set-city Dubai "United Arab Emirates"
sh adhan-reminder/scripts/run.sh set-lang en        # or: ar
sh adhan-reminder/scripts/run.sh times
sh adhan-reminder/scripts/run.sh notify off         # turn off desktop notifications
sh adhan-reminder/scripts/run.sh stop               # stop the background process
sh adhan-reminder/scripts/run.sh service on         # macOS: keep notifications running at every login
```

### Always-on notifications (macOS, optional)
By default the background process starts with a Claude Code session and stops after 12 hours, so you can miss a reminder when no session was open. On macOS, `service on` installs a small launchd agent that starts at login and restarts if it stops; it uses almost no CPU or memory. Claude offers it once on your first session. Remove it any time with `service off`; `service status` shows its state.

### Requirements and privacy
- **Claude Code**, which needs a paid Claude plan (Pro or Max) or an API account. The plugin itself is free and open source.
- **Python 3.9+**, no extra packages. The plugin looks for `python3`, then `python`, then `py`.
- It only contacts `api.aladhan.com`, sending the city and country name to fetch times, then caches them locally.
- Settings are stored in `~/.claude/adhan/`.
- Without the optional service, the notification process runs for up to 12 hours, then stops (it restarts with each new session).

### Supported systems
| System | Message inside Claude | Desktop notification |
|---|---|---|
| macOS | ✅ | ✅ (built in, nothing to install) |
| Windows | ✅ experimental | ✅ experimental (Windows 10/11, via PowerShell) |
| Linux | ✅ experimental | needs `notify-send` (package `libnotify-bin`) |

- On Windows you need Python from [python.org](https://www.python.org/downloads/) (tick "Add to PATH") and `sh`, which comes with [Git for Windows](https://git-scm.com/download/win).
- Windows and Linux support is new and has not been tested on real machines yet. If something breaks, please open an issue.

---

## العربية

بلقن (plugin) لـ Claude Code يذكّرك بمواعيد الصلاة أثناء العمل. وقت الأذان تظهر رسالة مزخرفة داخل كلود، وبعد **10 دقائق** تظهر أخرى: «قم صلِّ».

### المميزات
- رسائل التذكير **بالعربي أو بالإنجليزي** حسب اختيارك.
- تظهر بين خطوات كلود حتى لو كان يشتغل على مهمة.
- إشعار اختياري على سطح المكتب مع صوت (عملية خلفية) يوصلك حتى لو كلود مشغول بأمر طويل: macOS وWindows وLinux.
- يسألك عن مدينتك في أول استخدام، وتقدر تغيّرها وقت ما تبي.
- المواقيت من [Aladhan API](https://aladhan.com/prayer-times-api) (تقويم أم القرى للسعودية، وطرق مناسبة لبقية الدول).
- عرض المواقيت بنظام 12 ساعة (ص/م).

### التثبيت
```bash
claude plugin marketplace add superzoool/adhan-reminder
claude plugin install adhan-reminder@ahmed-plugins
```

> 🔄 **أعد تشغيل Claude Code** (أو ابدأ جلسة جديدة) بعد التثبيت، عشان يتفعّل البلقن.

### الاستخدام
- أول جلسة: كلود يسألك عن مدينتك ولغة الرسائل (الرياض والعربي افتراضياً).
- قل لكلود: «مواقيت الصلاة» أو «غيّر مدينتي إلى جدة» أو «خلّ التذكير بالإنجليزي» أو «وقّف إشعارات الصلاة».
- أو من الطرفية، من نسخة المستودع:

```bash
sh adhan-reminder/scripts/run.sh set-city Jeddah "Saudi Arabia"
sh adhan-reminder/scripts/run.sh set-lang ar        # أو: en
sh adhan-reminder/scripts/run.sh times
sh adhan-reminder/scripts/run.sh notify off         # إيقاف إشعارات سطح المكتب
sh adhan-reminder/scripts/run.sh stop               # إيقاف العملية الخلفية
sh adhan-reminder/scripts/run.sh service on         # macOS: تشغيل الإشعارات تلقائياً عند كل تسجيل دخول
```

### إشعارات دائمة (macOS، اختياري)
افتراضياً تبدأ العملية الخلفية مع جلسة Claude Code وتتوقف بعد 12 ساعة، فقد يفوتك تذكير إذا لم تكن هناك جلسة مفتوحة. على macOS الأمر `service on` يثبّت خدمة launchd صغيرة تبدأ عند تسجيل الدخول وتعيد تشغيل نفسها إذا توقفت، واستهلاكها للمعالج والذاكرة شبه معدوم. يعرضها عليك كلود مرة واحدة في أول جلسة. تلغيها بـ `service off`، و`service status` يعرض حالتها.

### الخصوصية والمتطلبات
- يحتاج **Claude Code** (يتطلب اشتراك Claude مدفوعاً مثل Pro أو Max، أو حساب API). البلقن نفسه مجاني ومفتوح المصدر.
- يحتاج **Python 3.9+** (بدون مكتبات إضافية). البلقن يبحث تلقائياً عن `python3` ثم `python` ثم `py`.
- يتصل بـ `api.aladhan.com` فقط، ويرسل اسم المدينة والدولة لجلب المواقيت، ثم يحفظها محلياً.
- الإعدادات في `~/.claude/adhan/`.
- بدون الخدمة الاختيارية، العملية الخلفية للإشعارات تعمل حتى 12 ساعة ثم تتوقف (تتجدد مع كل جلسة جديدة).

### الأنظمة المدعومة
| النظام | رسالة داخل كلود | إشعار سطح المكتب |
|---|---|---|
| macOS | ✅ | ✅ (مدمج، بدون تثبيت) |
| Windows | ✅ تجريبي | ✅ تجريبي (Windows 10/11، عبر PowerShell) |
| Linux | ✅ تجريبي | يحتاج `notify-send` (حزمة `libnotify-bin`) |

- على Windows يحتاج Python من [python.org](https://www.python.org/downloads/) (فعّل خيار Add to PATH) و`sh` الذي يأتي مع [Git for Windows](https://git-scm.com/download/win).
- دعم Windows وLinux جديد ولم يُجرَّب على أجهزة حقيقية بعد؛ إذا واجهت مشكلة افتح Issue.

---

## License · الترخيص
MIT
