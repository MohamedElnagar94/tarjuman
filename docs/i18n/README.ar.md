<p align="center">
  <img src="../../assets/brand/icon-256.png" width="128" height="128" alt="أيقونة ترجمان: حرف التاء العربي تحت علامة التشغيل">
</p>

<h1 align="center">Tarjuman · ترجمان</h1>

<p align="center">
  <strong>شاهد أي فيديو بالعربية.</strong><br>
  ترجمة متزامنة، ودبلجة حية بصوت طبيعي، وملفات MP4 مدبلجة، وإضافة للمتصفح. وكل ذلك يعمل على جهازك أنت.
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="رخصة MIT" src="https://img.shields.io/badge/license-MIT-3550D6"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-1F2E8C">
  <img alt="Vue 3" src="https://img.shields.io/badge/vue-3-1F2E8C">
  <img alt="Chrome MV3" src="https://img.shields.io/badge/chrome-MV3-F0922B">
</p>

<p align="center">
  <a href="../../README.md">English</a> ·
  <b>العربية</b> ·
  <a href="README.fr.md">Français</a> ·
  <a href="README.es.md">Español</a> ·
  <a href="README.de.md">Deutsch</a> ·
  <a href="README.it.md">Italiano</a> ·
  <a href="README.pt.md">Português</a> ·
  <a href="README.tr.md">Türkçe</a> ·
  <a href="README.ru.md">Русский</a> ·
  <a href="README.ur.md">اردو</a> ·
  <a href="README.fa.md">فارسی</a> ·
  <a href="README.hi.md">हिन्दी</a> ·
  <a href="README.id.md">Bahasa Indonesia</a> ·
  <a href="README.zh.md">中文</a> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.ko.md">한국어</a>
</p>

<p align="center">
  <img src="../screenshots/watch.png" alt="ترجمان يعرض فيديو من YouTube بترجمة عربية مع لوحة الدبلجة مفتوحة" width="900">
</p>

<div dir="rtl">

## ماذا يفعل

الصق رابطًا من YouTube، أو ارفع فيديو من جهازك، أو أعطه رابطًا من أي موقع تقريبًا.

- **ترجمة متزامنة.** تظهر الترجمة العربية على الفيديو سطرًا بسطر، ومعها النص الأصلي أسفلها إن أردت. وتُجمع النصوص المولَّدة تلقائيًا في جمل كاملة قبل ترجمتها.
- **دبلجة حية تبدو كصوت إنسان.** صوت عربي مولَّد بالشبكات العصبية ينطق كل جملة في توقيتها مع المتحدث، باللهجة المصرية أو السعودية أو الإماراتية أو السورية أو الأردنية أو اللبنانية أو المغربية أو العراقية. لا تُقطع جملة ولا تُتخطّى، ولا يتوقف الفيديو إلا إذا تأخرت الدبلجة كثيرًا.
- **MP4 مدبلج.** صدّر الفيديو بالتعليق الصوتي العربي. يمكنه حذف صوت المتحدث الأصلي مع الإبقاء على الموسيقى والمؤثرات، وإعطاء كل متحدث صوتًا مناسبًا ذكوريًا أو أنثويًا، وتضمين الترجمة أو دمجها في الصورة.
- **لا يوجد نص للفيديو؟ لا مشكلة.** يحوّل Whisper الصوت إلى نص على جهازك، ثم يُترجم النص.
- **ملفات الترجمة.** نزّل SRT أو VTT أو نصًا عاديًا، بالعربية أو بلغتين، أو ملف MP4 مترجمًا جاهزًا للمشاركة.
- **قوائم تشغيل كاملة.** أعطه رابط قائمة تشغيل أو قناة ليصنع الترجمات أو مقاطع الفيديو المترجمة أو المدبلجة لكل فيديو فيها.
- **اسأل الفيديو** (ذكاء اصطناعي اختياري). احصل على ملخص، وأهم النقاط، وفصول قابلة للنقر، وإجابات تنقلك إلى اللحظة التي يتناول فيها الفيديو سؤالك. يعمل مع Claude أو أي مزوّد متوافق مع OpenAI (Gemini وGroq وOpenRouter وOllama).
- **تعلّم الإنجليزية.** انقر أي كلمة لترى معناها، واحفظها مع جملتها، وراجعها لاحقًا، وصدّرها إلى Anki. ويمكنك أيضًا تكرار جملة، أو الإيقاف بعد كل سطر، أو تمويه الترجمة لتختبر نفسك.
- **إضافة المتصفح.** استخدم الترجمة والدبلجة نفسيهما على YouTube مباشرة، وعلى المواقع التي يوفّر مشغّلها ترجمات (Coursera وUdemy وغيرهما)، أو على أي موقع آخر عبر الاستماع إلى صوت التبويب.

ولغات أخرى تعمل أيضًا: الفرنسية والإسبانية والألمانية والتركية والإنجليزية مدمجة كلغات هدف.

## البدء السريع

تحتاج إلى **Python 3.11+** و**Node.js 20+**.

**Windows:** انقر نقرًا مزدوجًا على `start.cmd`.

**macOS / Linux:**

```sh
./start.sh
```

يثبّت التشغيل الأول كل شيء: حزم Python، والصوت العربي الذي يعمل دون اتصال، ونسخة مبنية من تطبيق الويب. ثم يُفتح التطبيق على `http://127.0.0.1:4318`. وفي المرات التالية يبدأ خلال ثانيتين تقريبًا. ولاستخدامه من هاتفك، افتح العنوان الذي يطبعه لشبكة Wi-Fi.

<details>
<summary>الإعداد اليدوي</summary>

```sh
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt        # Windows: .venv\Scripts\pip
npm --prefix frontend install && npm --prefix frontend run build
PYTHONPATH=backend .venv/bin/python -m tarjuman           # Windows: set PYTHONPATH=backend
```

</details>

### الأوامر

| الأمر | وظيفته |
|---|---|
| `python -m tarjuman` | تشغيل التطبيق (`--port`، و`--host 127.0.0.1` لهذا الجهاز فقط، و`--no-open`) |
| `python -m tarjuman subs <link>` | كتابة ملفات الترجمة في `data/output` (`--lang`، `--format srt,vtt,txt`) |
| `python -m tarjuman setup` | تثبيت كل شيء أو إصلاحه |
| `python -m tarjuman update` | تحديث yt-dlp وعميل الأصوات، إذا توقف التنزيل أو الأصوات عن العمل |
| `python -m tarjuman doctor` | فحص كل المكونات |

## إضافة المتصفح

<p align="center">
  <img src="../screenshots/extension-popup.png" alt="النافذة المنبثقة لإضافة ترجمان" width="320">
</p>

1. ابنِها مرة واحدة: `npm --prefix extension install && npm --prefix extension run build`.
2. افتح `chrome://extensions` (أو `edge://extensions`)، وفعّل **وضع مطوّر البرامج**، وانقر **تحميل إضافة غير مضغوطة**، واختر `extension/dist`.
3. أبقِ التطبيق يعمل، وافتح فيديو، وانقر أيقونة ترجمان، أو اضغط <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>A</kbd>.

لا تتواصل الإضافة إلا مع التطبيق الموجود على جهازك. وحزمة متجر Chrome Web Store الخاصة بها (نص الصفحة، ومبررات الأذونات، وسياسة الخصوصية، والصور الترويجية) موجودة في [`extension/store`](../../extension/store).

## كيف تبقى الدبلجة متزامنة

تُدمج أسطر الترجمة في جمل كاملة، وتُحذف حشوات الكلام. ثم تُحدَّد سرعة كل جملة بناءً على نافذة استباقية مدتها نحو 12 ثانية، فتُعير الجملة التي لديها متّسع من الوقت جزءًا منه لجملة مزدحمة، وتتغير السرعة تدريجيًا بدل أن تقفز. وقبل أن يشغّل المتصفح أي شيء، يولّد الخادم كل جملة صوتيًا ويقيس مدتها، فتقوم الخطة على مُدد حقيقية لا على تخمين. وإذا تأخرت الدبلجة رغم ذلك، تُشغَّل الجمل التالية أسرع قليلًا؛ ولا يتوقف الفيديو إلا إذا تجاوز الفارق ثانيتين تقريبًا. والانتقال إلى أي موضع يستأنف الدبلجة من النقطة نفسها بالضبط.

التصميم الكامل في [docs/implementation.md](../implementation.md).

## الخصوصية

ترجمان يعمل محليًا أولًا. تبقى مقاطعك وترجماتك وكلماتك المحفوظة وإعداداتك ومفتاح API في مجلد `data/` على جهازك. يتصل التطبيق بـ YouTube (الترجمات والتنزيلات)، وGoogle Translate وMyMemory (الترجمة)، وخدمة أصوات Edge من Microsoft (النطق)، وبمزوّد الذكاء الاصطناعي الذي تختاره فقط إذا فعّلته. لا حسابات ولا إحصاءات ولا تتبّع. ويرفض الـ API الطلبات الواردة من مواقع أخرى، ولا يمكن تغيير إعدادات الذكاء الاصطناعي إلا من الجهاز الذي يعمل عليه التطبيق.

## الإعدادات

| متغير البيئة | القيمة الافتراضية | المعنى |
|---|---|---|
| `TARJUMAN_HOME` | مجلد المشروع | مكان حفظ `data/` |
| `TARJUMAN_PORT` | `4318` | أول منفذ يُجرَّب (ينتقل إلى المنفذ التالي إذا كان مشغولًا، والإضافة تتبعه) |
| `TARJUMAN_HOST` | `0.0.0.0` | استخدم `127.0.0.1` لإبقاء التطبيق خارج شبكة Wi-Fi |
| `TARJUMAN_WHISPER_MODEL` | `base` | `small` أو `medium` لتفريغ صوتي أدق (وأبطأ) |
| `ANTHROPIC_API_KEY` | – | يُستخدم مع Claude إذا لم يُحفظ مفتاح في الإعدادات |

## بنية المشروع

```
backend/     Python package `tarjuman` (FastAPI): captions, translation, voices, dubbing, AI, jobs
frontend/    Vue 3 + Vite + TypeScript web app
extension/   Chrome / Edge extension (Manifest V3, Vue + Vite) and its store kit
shared/      the live dub engine used by both the web app and the extension
assets/      brand (icon source and renders)
docs/        plan, specification, implementation notes, translated READMEs, screenshots
```

## التطوير

```sh
# backend tests (offline)
cd backend && ../.venv/bin/python -m pytest      # Windows: ...venvScriptspython

# dub engine tests
npm test

# web app with hot reload (proxies the API to 127.0.0.1:4318)
npm --prefix frontend run dev

# extension: build, test, package a store zip
npm --prefix extension run build && npm --prefix extension test && npm --prefix extension run package
```

اقرأ [docs/specs.md](../specs.md) قبل تغيير أي مسار في الـ API، فتطبيق الويب والإضافة كلاهما يعتمدان عليه.

## بُني باستخدام

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) ·
[edge-tts](https://github.com/rany2/edge-tts) ·
[Piper](https://github.com/rhasspy/piper) ·
[yt-dlp](https://github.com/yt-dlp/yt-dlp) ·
[نماذج MDX-Net من Ultimate Vocal Remover](https://github.com/TRvlvr/model_repo) ·
[FastAPI](https://fastapi.tiangolo.com) ·
[Vue](https://vuejs.org) ·
[Claude](https://www.anthropic.com/claude)

## الرخصة

[MIT](../../LICENSE). يخضع تنزيل مقاطع الفيديو والترجمات لشروط كل موقع. استخدم ترجمان للمحتوى المسموح لك بمشاهدته وتكييفه.

</div>
