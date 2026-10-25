# 🕌 adhan-reminder — تذكير الصلاة لـ Claude Code

بلقن (plugin) لـ Claude Code يذكّرك بمواعيد الصلاة أثناء العمل.

A Claude Code plugin that reminds you of prayer times while you work.

## المميزات
- رسالة مزخرفة داخل كلود وقت الأذان، وأخرى بعد **10 دقائق**: «قم صلِّ».
- تظهر بين خطوات كلود حتى لو كان يشتغل على مهمة.
- إشعار macOS مع صوت (عملية خلفية) يوصلك حتى لو كلود مشغول بأمر طويل.
- يسألك عن مدينتك في أول استخدام، وتقدر تغيّرها وقت ما تبي.
- المواقيت من [Aladhan API](https://aladhan.com/prayer-times-api) (تقويم أم القرى للسعودية، وطرق مناسبة لبقية الدول).
- عرض المواقيت بنظام 12 ساعة (ص/م).

## التثبيت
```bash
claude plugin marketplace add superzoool/adhan-reminder
claude plugin install adhan-reminder@ahmed-plugins
```

## الاستخدام
- أول جلسة: كلود يسألك عن مدينتك (الرياض افتراضياً).
- قل لكلود: «مواقيت الصلاة» أو «غيّر مدينتي إلى جدة».
- أو من الطرفية:

```bash
python3 adhan-reminder/scripts/adhan.py set-city Jeddah "Saudi Arabia"
python3 adhan-reminder/scripts/adhan.py times
python3 adhan-reminder/scripts/adhan.py notify off   # إيقاف إشعارات macOS
python3 adhan-reminder/scripts/adhan.py stop         # إيقاف العملية الخلفية
```

## الخصوصية والمتطلبات
- يتصل بـ `api.aladhan.com` فقط، ويرسل اسم المدينة والدولة لجلب المواقيت، ثم يحفظها محلياً.
- الإعدادات في `~/.claude/adhan/`.
- العملية الخلفية لإشعارات macOS تعمل حتى 12 ساعة ثم تتوقف.
- يحتاج Python 3.9+ (بدون مكتبات إضافية). الإشعارات الخارجية على macOS فقط.

## الترخيص
MIT
