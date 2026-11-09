# الواجهة العربية (Arabic UI)

> Applies to: The Arabic user interface layer (shared/i18n): enabling or disabling it, page layout options, and updating the translation dictionary.

تعمل واجهة WanGP بالعربية افتراضيًا مع اتجاه من اليمين لليسار (RTL)، وتشمل الواجهة الرئيسية وتطبيقات Deepy وShowrunner وMedia Flow.

## التشغيل

```bash
python wgp.py                      # عربي (افتراضي)
WANGP_UI_LANG=en python wgp.py     # الإنجليزية الأصلية
```

## كيف يعمل

التعريب طبقة تعمل وقت التشغيل في `shared/i18n/` ولا تعدّل منطق البرنامج:

| الملف | الدور |
|---|---|
| `__init__.py` | يترجم خصائص مكونات Gradio (العناوين، الشروح، النصوص التوضيحية، تسميات الخيارات، محتوى Markdown/HTML) قبل إرسالها للمتصفح، ورسائل `gr.Info/Warning/Error`. **قيم** الخيارات تبقى إنجليزية فلا يتأثر المنطق. |
| `i18n.js` | يُحقن في كل صفحة HTML ويترجم ما تبقى من نصوص حيّة (MutationObserver) ويفعّل RTL ولغة Gradio المدمجة. |
| `rtl.css` | الخط العربي وتعديلات الاتجاه؛ الفيديو واللوحات والمحررات والأرقام تبقى LTR. |
| `ar.json` | القاموس (نصوص ثابتة + قوالب `{}` للنصوص المتغيرة). |
| `tools/` | أدوات استخراج النصوص وبناء القاموس بعد تحديث WanGP. |

نص الموجّه (Prompt) وما يكتبه المستخدم لا يُترجم أبدًا.

## بعد تحديث WanGP من المصدر

```bash
python3 -I shared/i18n/tools/extract.py . /tmp/raw.json      # استخراج النصوص الجديدة
# ترجم النصوص غير الموجودة في ar.json إلى ملفات *.ar.json داخل مجلد، ثم:
python3 -I shared/i18n/tools/build_dict.py /tmp/raw.json <مجلد_الترجمات> shared/i18n/ar.json shared/i18n/ar.json
```

النصوص غير المترجمة تظهر بالإنجليزية ولا تكسر شيئًا.
