# WanGP Arabic UI translation — rules & glossary

Audience: Arabic-speaking users of WanGP (AI video/image/audio generation app). Modern Standard Arabic, concise UI register.

## Hard rules
1. Output = JSON object `{ "<english exactly as given>": "<arabic>" }` covering EVERY key of your input chunk. Keys must be byte-identical to input.
2. Placeholders `{}` = runtime values. Keep the SAME NUMBER of placeholders. If Arabic word order needs them reordered, write indexed `{0}`, `{1}`… (0 = first `{}` in the English). Otherwise keep plain `{}`.
3. Never translate: model/product names (Wan, LTX, Hunyuan, Flux, Qwen, VACE, MMAudio, Deepy, Showrunner, Media Flow, WanGP, LoRA, VAE, GGUF, INT8, FP8, NVFP4, CUDA, Triton, Sage, RIFE…), file extensions, code in `backticks`, URLs, CLI flags, units (GB, fps, px, s, ms), keyboard keys, JSON/setting keys, numbers, sampler names (Euler, UniPC, DPM++), "Prompt" when it is a literal tag like [Shot 1].
4. Preserve leading/trailing punctuation & spaces semantics, markdown markers (`**`, `#`, `-`), and HTML entities. Fragments (strings starting/ending mid-sentence, e.g. ", ambience and physical sounds in") are pieces of a larger sentence split by bold text — translate them as natural fragments.
5. If a string is clearly NOT user-visible text (code, CSS, identifiers, regex, log keys, sample prompt text intended to be sent to the model in English), map it to itself (identical English). Example prompts shown as examples MAY stay English — prefer leaving them English.
6. Use Western digits (0-9). Use Arabic comma "،" in prose. Title-case English buttons → short Arabic imperative/noun.

## Glossary (use consistently)
Prompt → الموجّه | Negative Prompt → الموجّه السلبي | Enhance Prompt → تحسين الموجّه
Generate → توليد | Generation → التوليد | Queue → قائمة الانتظار | Abort/Cancel → إلغاء | Stop → إيقاف | Resume → استئناف | Pause → إيقاف مؤقت
Settings → الإعدادات | Configuration → التهيئة | Advanced → متقدم | Apply → تطبيق | Save → حفظ | Load → تحميل | Reset → إعادة تعيين | Delete → حذف | Close → إغلاق | Download → تنزيل | Upload → رفع | Import → استيراد | Export → تصدير
Model → النموذج | Checkpoint → نقطة الحفظ | Finetune → ضبط دقيق | Quantization → التكميم | Profile → ملف الأداء | Attention → الانتباه | Kernel(s) → النوى (kernels) | VRAM → ذاكرة الفيديو (VRAM) | RAM → الذاكرة (RAM)
Steps / Inference Steps → خطوات الاستدلال | Guidance / CFG → التوجيه (CFG) | Seed → البذرة | Sampler → المُعايِن (Sampler) | Scheduler → المُجدوِل | Denoising Strength → شدة إزالة الضجيج | Shift → الإزاحة (Shift)
Resolution → الدقة | Frames → الإطارات | Frame Rate / FPS → معدل الإطارات | Duration → المدة | Number of frames → عدد الإطارات | Aspect ratio → نسبة الأبعاد
Sliding Window → النافذة المنزلقة | Overlap → التداخل | Start Image → الصورة الابتدائية | End Image → الصورة الختامية | Reference Image → الصورة المرجعية | Control Video → فيديو التحكم | Source Video → الفيديو المصدر | Mask → القناع | Inpainting → الإكمال الداخلي | Outpainting → التوسيع الخارجي | Pose → الوضعية | Depth → العمق
Upsampling / Upscaler → رفع الدقة | Spatial → مكاني | Temporal → زمني | Interpolation → استيفاء الإطارات | Postprocessing → المعالجة اللاحقة | Preprocessing → المعالجة المسبقة
Gallery → المعرض | Video → فيديو | Image → صورة | Audio → صوت | Soundtrack → المسار الصوتي | Voice → الصوت/الصوت المرجعي | Speaker → المتحدث | Lip sync → مزامنة الشفاه
Plugin → إضافة | Lora preset → إعداد LoRA مسبق | Template → قالب | Batch → دفعة | Workspace → مساحة العمل | Shot → لقطة | Take → محاولة (Take) | Production → الإنتاج
Enabled/Disabled → مفعّل/معطّل | Auto → تلقائي | Default → افتراضي | Recommended → موصى به | Experimental → تجريبي | None → بلا | Yes/No → نعم/لا | On/Off → تشغيل/إيقاف
