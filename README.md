# 🕌 adhan-reminder — تذكير الصلاة لـ Claude Code

بلقن (plugin) لـ Claude Code يذكّرك بمواعيد الصلاة أثناء العمل.

A Claude Code plugin that reminds you of prayer times while you work.

> 💻 **مخصص للابتوب / الكمبيوتر فقط.** هذا البلقن يعمل داخل **Claude Code** على جهازك، فالتذكير يوصلك داخل كلود وأنت تشتغل ("قم صلِّ"). **لا يعمل على الجوال** ولا على تطبيق Claude للجوال أو الموقع.
>
> 💻 **Laptop/desktop only.** This plugin runs inside Claude Code on your computer, so the reminder reaches you right inside Claude while you work. It does not work on mobile or in the Claude mobile app/web.

## المميزات
- رسالة مزخرفة داخل كلود وقت الأذان، وأخرى بعد **10 دقائق**: «قم صلِّ».
- تظهر بين خطوات كلود حتى لو كان يشتغل على مهمة.
- إشعار على سطح المكتب مع صوت (عملية خلفية) يوصلك حتى لو كلود مشغول بأمر طويل: macOS وWindows وLinux.
- يسألك عن مدينتك في أول استخدام، وتقدر تغيّرها وقت ما تبي.
- المواقيت من [Aladhan API](https://aladhan.com/prayer-times-api) (تقويم أم القرى للسعودية، وطرق مناسبة لبقية الدول).
- عرض المواقيت بنظام 12 ساعة (ص/م).

## التثبيت
```bash
claude plugin marketplace add superzoool/adhan-reminder
claude plugin install adhan-reminder@ahmed-plugins
```

> 🔄 **أعد تشغيل Claude Code** (أو ابدأ جلسة جديدة) بعد التثبيت، عشان يتفعّل البلقن.

## الاستخدام
- أول جلسة: كلود يسألك عن مدينتك (الرياض افتراضياً).
- قل لكلود: «مواقيت الصلاة» أو «غيّر مدينتي إلى جدة».
- أو من الطرفية:

```bash
python3 adhan-reminder/scripts/adhan.py set-city Jeddah "Saudi Arabia"
python3 adhan-reminder/scripts/adhan.py times
python3 adhan-reminder/scripts/adhan.py notify off   # إيقاف إشعارات سطح المكتب
python3 adhan-reminder/scripts/adhan.py stop         # إيقاف العملية الخلفية
```

## الخصوصية والمتطلبات
- يحتاج **Claude Code** (يتطلب اشتراك Claude مدفوعاً مثل Pro أو Max، أو حساب API). البلقن نفسه مجاني ومفتوح المصدر.
- يحتاج **Python 3.9+** (بدون مكتبات إضافية). البلقن يبحث تلقائياً عن `python3` ثم `python` ثم `py`.
- يتصل بـ `api.aladhan.com` فقط، ويرسل اسم المدينة والدولة لجلب المواقيت، ثم يحفظها محلياً.
- الإعدادات في `~/.claude/adhan/`.
- العملية الخلفية للإشعارات تعمل حتى 12 ساعة ثم تتوقف (تتجدد مع كل جلسة جديدة).

### الأنظمة المدعومة
| النظام | رسالة داخل كلود | إشعار سطح المكتب |
|---|---|---|
| macOS | ✅ | ✅ (مدمج، بدون تثبيت) |
| Windows | ✅ تجريبي | ✅ تجريبي (Windows 10/11، عبر PowerShell) |
| Linux | ✅ تجريبي | يحتاج `notify-send` (حزمة `libnotify-bin`) |

- على Windows يحتاج Python مثبتاً من [python.org](https://www.python.org/downloads/) (فعّل خيار Add to PATH) و[Git for Windows](https://git-scm.com/download/win) (Claude Code نفسه يتطلبه).
- دعم Windows وLinux جديد ولم يُجرَّب على أجهزة حقيقية بعد؛ إذا واجهت مشكلة افتح Issue.

## الترخيص
MIT
