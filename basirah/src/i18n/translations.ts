/**
 * BASIRAH bilingual copy.
 *
 * Every user-visible string lives here — no inline literals in
 * components. Keys are grouped by feature so a screen's copy can be
 * read top-to-bottom in one place.
 *
 * `en` is the source of truth: `ar` is typed against it, so a missing
 * or misspelled Arabic key is a compile error, not a silent fallback
 * to English at runtime.
 */

export const translations = {
  /* ------------------------------------------------------------------ */
  brand: {
    name: 'BASIRAH',
    nameAr: 'بصيرة',
    subtitle: {
      en: 'Suspicious Digital Content Intelligence',
      ar: 'استخبارات المحتوى الرقمي المشبوه',
    },
    tagline: { en: 'Look beyond what appears.', ar: 'لا تكتفِ بما تراه، افحص ما وراءه.' },
    /**
     * The canonical positioning sentence. The hero, the About section
     * and the footer all resolve this key rather than paraphrasing it,
     * so the platform describes itself identically everywhere.
     * Suspicious IMAGES lead; suspicious URLs are named last because
     * they are the secondary modality.
     */
    positioning: {
      en: 'BASIRAH is an AI-powered digital trust platform for analysing suspicious images, risky digital content, encoded signals, digital evidence, and suspicious links.',
      ar: 'بصيرة منصة مدعومة بالذكاء الاصطناعي لتحليل الصور المشبوهة والمحتوى الرقمي المريب والإشارات المشفرة والأدلة الرقمية والروابط المشبوهة.',
    },
  },

  /* ------------------------------------------------------------------ */
  /* Primary navigation                                                 */
  /* ------------------------------------------------------------------ */
  nav: {
    label: { en: 'Primary', ar: 'التنقل الرئيسي' },
    menu: { en: 'Menu', ar: 'القائمة' },
    open: { en: 'Open navigation', ar: 'فتح قائمة التنقل' },
    close: { en: 'Close navigation', ar: 'إغلاق قائمة التنقل' },
    overview: { en: 'Overview', ar: 'نظرة عامة' },
    categories: { en: 'Categories', ar: 'الفئات' },
    analyze: { en: 'Analyze', ar: 'التحليل' },
    challenge: { en: 'Challenge', ar: 'التحدي' },
    capabilities: { en: 'Capabilities', ar: 'الإمكانات' },
    dashboard: { en: 'Dashboard', ar: 'لوحة النظام' },
    reports: { en: 'Reports', ar: 'التقارير' },
    team: { en: 'Team', ar: 'الفريق' },
    about: { en: 'About', ar: 'عن المنصة' },
    startAnalysis: { en: 'Start Analysis', ar: 'ابدأ التحليل' },
  },

  /* ------------------------------------------------------------------ */
  /* Theme control                                                       */
  theme: {
    toggle: { en: 'Switch colour theme', ar: 'تبديل سمة الألوان' },
    switchToDark: { en: 'Switch to dark theme', ar: 'التبديل إلى السمة الداكنة' },
    switchToLight: { en: 'Switch to light theme', ar: 'التبديل إلى السمة الفاتحة' },
    light: { en: 'Light', ar: 'فاتح' },
    dark: { en: 'Dark', ar: 'داكن' },
    current: { en: 'Current theme', ar: 'السمة الحالية' },
    /* The reveal must announce itself once, then get out of the way. */
    revealLabel: { en: 'BASIRAH — Digital Trust Intelligence', ar: 'بصيرة — استخبارات الثقة الرقمية' },
    revealHint: { en: 'Loading the platform', ar: 'جارٍ تحميل المنصة' },
  },

  /* ------------------------------------------------------------------ */
  /* Hero intelligence frame — perimeter labels ------------------------- */
  hero: {
    frameLabel: { en: 'Analysis modalities in scope', ar: 'وسائل التحليل المشمولة' },
    modImage: { en: 'IMAGE', ar: 'صورة' },
    modEvidence: { en: 'EVIDENCE', ar: 'دليل' },
    modTrust: { en: 'TRUST', ar: 'ثقة' },
    modFiles: { en: 'FILES', ar: 'ملفات' },
    modEncoding: { en: 'ENCODING', ar: 'ترميز' },
    modUrl: { en: 'URL', ar: 'رابط' },
  },

  /* ------------------------------------------------------------------ */
  /* Intelligence ticker                                                 */
  ticker: {
    label: { en: 'Digital trust awareness', ar: 'الوعي بالثقة الرقمية' },
    pause: { en: 'Pause the awareness ticker', ar: 'إيقاف شريط الوعي مؤقتاً' },
    play: { en: 'Resume the awareness ticker', ar: 'استئناف شريط الوعي' },
    paused: { en: 'Ticker paused', ar: 'الشريط متوقف' },
    categories: {
      phishing: { en: 'Phishing', ar: 'التصيّد' },
      qrSafety: { en: 'QR safety', ar: 'أمان رموز QR' },
      digitalTrust: { en: 'Digital trust', ar: 'الثقة الرقمية' },
      socialEngineering: { en: 'Social engineering', ar: 'الهندسة الاجتماعية' },
      syntheticMedia: { en: 'Synthetic media', ar: 'الوسائط المُولَّدة' },
    },
    items: {
      hoverOverDomain: {
        tag: 'phishing',
        en: 'Read the domain before the message. Urgency and authority are the two oldest lures in phishing.',
        ar: 'اقرأ النطاق قبل الرسالة. الإلحاح والسلطة هما أقدم خدعتين في التصيّد.',
      },
      qrUnknownDestination: {
        tag: 'qrSafety',
        en: 'A QR code can hide its destination until it is scanned. Resolve where it leads before you follow it.',
        ar: 'قد يُخفي رمز QR وجهته حتى يُمسح. تحقّق من الوجهة قبل اتباعه.',
      },
      mismatchBrand: {
        tag: 'digitalTrust',
        en: 'A familiar logo does not make a message genuine. Compare the sender address, not the branding.',
        ar: 'الشعار المألوف لا يجعل الرسالة حقيقية. قارن عنوان المرسل لا العلامة.',
      },
      tooMuchInformation: {
        tag: 'socialEngineering',
        en: 'Requests for credentials, transfers or urgency are signals in themselves. Pause before responding.',
        ar: 'طلبات البيانات أو التحويلات أو الاستعجال هي إشارات بذاتها. توقّف قبل الرد.',
      },
      reverseImageSearch: {
        tag: 'syntheticMedia',
        en: 'Look for physical inconsistency before trusting an image: text on signs, reflections, and edges of hands.',
        ar: 'ابحث عن عدم اتساق مادي قبل الوثوق بصورة: النصوص على اللافتات والانعكاسات وحدود الأيدي.',
      },
      metadataRemains: {
        tag: 'syntheticMedia',
        en: 'Editing a file often leaves metadata behind. Its presence is a clue, and its absence is not a clean bill of health.',
        ar: 'غالباً ما يترك التعديل بيانات وصفية. وجودها دليل، وغيابها ليس شهادة بخلوّ الملف.',
      },
      shortenerHidesTarget: {
        tag: 'phishing',
        en: 'A shortened link conceals its final destination. Expand it before you decide whether to open it.',
        ar: 'الرابط المختصر يخفي وجهته النهائية. وسّعه قبل أن تقرر فتحه.',
      },
      credentialsNeverRequested: {
        tag: 'socialEngineering',
        en: 'No legitimate organisation asks for your password by message. That request is the attack.',
        ar: 'لا تطلب أي جهة شرعية كلمة مرورك عبر رسالة. هذا الطلب هو الهجوم.',
      },
      provenanceNotDecoration: {
        tag: 'digitalTrust',
        en: 'Content credentials describe how a file was produced. They are evidence of process, not proof of truth.',
        ar: 'بيانات الاعتماد تصف كيفية إنتاج الملف. هي دليل على العملية لا إثبات على الصحة.',
      },
      encodedContentExists: {
        tag: 'digitalTrust',
        en: 'Content can be concealed inside a file rather than displayed by it. A clean preview is not the whole file.',
        ar: 'يمكن إخفاء المحتوى داخل الملف بدل عرضه. المعاينة النظيفة ليست الملف بأكمله.',
      },
      manipulatedContext: {
        tag: 'syntheticMedia',
        en: 'An unaltered image placed in a false context is still misleading. Check where it appeared, not only how it looks.',
        ar: 'صورة غير معدّلة في سياق كاذب تظل مضلّلة. تحقّق من مكان ظهورها لا من شكلها فقط.',
      },
      verifyOutOfBand: {
        tag: 'phishing',
        en: 'If a request matters, confirm it through a channel you already trust — not the one the message supplied.',
        ar: 'إذا كان الطلب مهماً، أكّده عبر قناة تثق بها مسبقاً — لا القناة التي أرسلتها الرسالة.',
      },
    },
  },

  /* ------------------------------------------------------------------ */
  /* Dashboard charts — honest data only                                 */
  charts: {
    title: { en: 'Platform measurements', ar: 'قياسات المنصة' },
    subtitle: {
      en: 'Every figure below comes from configuration the platform can actually demonstrate. Nothing here is a projected, averaged or illustrative number.',
      ar: 'كل رقم أدناه يأتي من إعداد تستطيع المنصة إثباته فعلياً. لا شيء هنا رقم متوقع أو متوسط أو توضيحي.',
    },
    readinessTitle: { en: 'Module readiness', ar: 'جاهزية الوحدات' },
    readinessSubtitle: {
      en: 'A categorical count of modules by the state they are really in. This is a census of the codebase, not a performance score.',
      ar: 'عدّ فئوي للوحدات حسب حالتها الفعلية. هذا إحصاء لشفرة النظام لا مؤشر أداء.',
    },
    stateCount: { en: '{count} modules', ar: '{count} وحدة' },
    readinessAlt: {
      en: 'Bar chart of module counts by state. {active} active, {research} research-grade, {advisory} advisory, {planned} planned.',
      ar: 'رسم أعمدة لعدد الوحدات حسب الحالة. {active} نشطة، {research} مستوى بحثي، {advisory} إرشادية، {planned} مخططة.',
    },
    historyTitle: { en: 'Analyses on this device', ar: 'التحليلات على هذا الجهاز' },
    historySubtitle: {
      en: 'A local record of analyses you have run in this browser. It never leaves this device, and no image or file is stored.',
      ar: 'سجل محلي للتحليلات التي أجريتها في هذا المتصفح. لا يغادر هذا الجهاز، ولا تُخزَّن أي صورة أو ملف.',
    },
    historyEmpty: {
      en: 'No analyses recorded on this device yet.',
      ar: 'لم تُسجَّل أي تحليلات على هذا الجهاز بعد.',
    },
    historyEmptyHint: {
      en: 'Run an analysis and its outcome will be summarised here — timestamp, modality, assessment and risk band only.',
      ar: 'أجرِ تحليلاً وسيُلخَّص نتيجته هنا — الوقت والوسيلة والتقييم وفئة الخطورة فقط.',
    },
    historyCount: { en: '{count} recorded', ar: '{count} مسجّل' },
    modalityTitle: { en: 'Modality mix', ar: 'توزيع الوسائل' },
    modalitySubtitle: {
      en: 'Which kind of signal your local analyses were submitted as.',
      ar: 'نوع الإشارة التي أُرسلت بها تحليلاتك المحلية.',
    },
    outcomeTitle: { en: 'Assessment outcomes', ar: 'نتائج التقييم' },
    outcomeSubtitle: {
      en: 'The classification each completed analysis returned, in the platform’s own three-way vocabulary.',
      ar: 'التصنيف الذي أعادته كل تحليل مكتمل، بمفردات المنصة الثلاثية.',
    },
    riskTitle: { en: 'Risk bands', ar: 'فئات الخطورة' },
    riskSubtitle: {
      en: 'How completed analyses were banded. The band is stated in words beside every value.',
      ar: 'كيف صُنِّفت التحليلات المكتملة. تُذكر الفئة بالكلمات إلى جانب كل قيمة.',
    },
    trustHistoryTitle: { en: 'Trust score over time', ar: 'درجة الثقة عبر الزمن' },
    trustHistorySubtitle: {
      en: 'Each recorded analysis as one point, ordered oldest to newest. A gap means no analysis was run then.',
      ar: 'كل تحليل مسجّل كنقطة واحدة، من الأقدم إلى الأحدث. الفراغ يعني عدم إجراء تحليل حينها.',
    },
    modalityImage: { en: 'Image', ar: 'صورة' },
    modalityScreenshot: { en: 'Screenshot', ar: 'لقطة شاشة' },
    modalityFile: { en: 'File', ar: 'ملف' },
    modalityUrl: { en: 'URL', ar: 'رابط' },
    modalityOther: { en: 'Other', ar: 'أخرى' },
    outcomeAuthentic: { en: 'Likely authentic', ar: 'يُرجّح أنها أصلية' },
    outcomeSynthetic: { en: 'Likely synthetic', ar: 'يُرجّح أنها اصطناعية' },
    outcomeUncertain: { en: 'Uncertain', ar: 'غير مؤكَّد' },
    outcomeNoStrong: {
      en: 'No strong synthetic indicators',
      ar: 'لا مؤشرات اصطناعية قوية',
    },
    outcomeProvenanceVerified: {
      en: 'Verified generative provenance',
      ar: 'مصدر توليد موثَّق',
    },
    outcomeProvenanceUnavailable: {
      en: 'Provenance unavailable',
      ar: 'المصدر غير متاح',
    },
    outcomeAdvisory: { en: 'Advisory band', ar: 'فئة إرشادية' },
    labelCount: { en: 'Count', ar: 'العدد' },
    labelTrust: { en: 'Trust score', ar: 'درجة الثقة' },
    labelRisk: { en: 'Risk band', ar: 'فئة الخطورة' },
    labelAssessment: { en: 'Assessment', ar: 'التقييم' },
    labelModality: { en: 'Modality', ar: 'الوسيلة' },
    labelWhen: { en: 'When', ar: 'الوقت' },
    chartAlt: {
      en: 'Chart. The same data is listed as text below.',
      ar: 'رسم بياني. البيانات نفسها مدرجة كنص أدناه.',
    },
    dataTableLabel: { en: 'Chart data as a table', ar: 'بيانات الرسم كجدول' },
    sourceLocal: { en: 'Local device record', ar: 'سجل الجهاز المحلي' },
    sourceConfig: { en: 'Platform configuration', ar: 'إعداد المنصة' },
    clearHistory: { en: 'Clear local record', ar: 'مسح السجل المحلي' },
    clearHistoryConfirm: {
      en: 'This removes the stored summaries from this device. It cannot be undone.',
      ar: 'يزيل هذا الملخصات المخزَّنة من هذا الجهاز. لا يمكن التراجع.',
    },
    cleared: { en: 'Local record cleared', ar: 'تم مسح السجل المحلي' },
  },

  /* ------------------------------------------------------------------ */
  /* Reports Center                                                      */
  reports: {
    title: { en: 'Reports Center', ar: 'مركز التقارير' },
    subtitle: {
      en: 'Every completed analysis can be issued as a written report. Reports are advisory documents: they record what the models measured, and what they could not establish.',
      ar: 'كل تحليل مكتمل يمكن إصداره تقريراً مكتوباً. التقارير وثائق استشارية: تسجّل ما قاسته النماذج وما تعذّر عليها إثباته.',
    },
    empty: { en: 'No reports on this device yet.', ar: 'لا توجد تقارير على هذا الجهاز بعد.' },
    emptyHint: {
      en: 'Run an analysis, then generate a report from the result. Reports are stored locally and never uploaded.',
      ar: 'أجرِ تحليلاً، ثم أصدر تقريراً من النتيجة. تُخزَّن التقارير محلياً ولا تُرفع أبداً.',
    },
    generate: { en: 'Generate report', ar: 'إصدار تقرير' },
    generateHint: {
      en: 'Issued from the current result. Save it to this device to find it here.',
      ar: 'يُصدر من النتيجة الحالية. احفظه على هذا الجهاز لتجده هنا.',
    },
    open: { en: 'Open report', ar: 'فتح التقرير' },
    back: { en: 'All reports', ar: 'كل التقارير' },
    delete: { en: 'Delete report', ar: 'حذف التقرير' },
    deleteConfirm: {
      en: 'This removes the report from this device. It cannot be undone.',
      ar: 'يزيل هذا التقرير من هذا الجهاز. لا يمكن التراجع.',
    },
    reportId: { en: 'Report ID', ar: 'معرّف التقرير' },
    created: { en: 'Generated', ar: 'تاريخ الإصدار' },
    modality: { en: 'Modality', ar: 'الوسيلة' },
    item: { en: 'Analysed item', ar: 'العنصر المحلَّل' },
    executiveSummary: { en: 'Executive summary', ar: 'الملخص التنفيذي' },
    assessment: { en: 'Assessment', ar: 'التقييم' },
    trustAndRisk: { en: 'Trust and risk', ar: 'الثقة والخطورة' },
    keyEvidence: { en: 'Key evidence', ar: 'الأدلة الرئيسية' },
    dnaSummary: { en: 'Trust DNA summary', ar: 'ملخص بصمة الثقة' },
    metadataSection: { en: 'Metadata and provenance', ar: 'البيانات الوصفية والمصدر' },
    timelineSection: { en: 'Investigation timeline', ar: 'الخط الزمني للتحقيق' },
    modelSection: { en: 'Model disclosure', ar: 'الإفصاح عن النموذج' },
    limitationsSection: { en: 'Limitations', ar: 'القيود' },
    safetySection: { en: 'Safety and intended use', ar: 'السلامة والاستخدام المقصود' },
    timeline: {
      title: { en: 'Investigation Timeline 2.0', ar: 'الخط الزمني للتحقيق 2.0' },
      subtitle: { en: 'The ordered record of what was examined.', ar: 'سجل التسلسل الزمني لما تمتّع به.' },
      emptyState: { en: 'No timeline entries yet.', ar: 'لا توجد نقاط بعد في السجل.' },
      contentHistory: { en: 'Content history', ar: 'سجل المحتوى' },
    },
    evidenceFingerprint: { en: 'Evidence fingerprint', ar: 'بصمة الأدلة' },
    evidenceFingerprintSub: { en: 'SHA-256 of the original uploaded bytes.', ar: 'بصمة SHA-256 لم바이트 المرفع الأصلي.' },
    evidenceFingerprintLabel: { en: 'Fingerprint', ar: 'البصمة' },
    evidenceFingerprintNote: { en: 'Do not call this blockchain or notarization. No upload is sent externally.', ar: 'لا تسمي هذا بالبلوكشين أو الشهادة. لا تُرسل أي رفع خارجيًا.' },
    reportTraceability: { en: 'Report traceability', ar: 'تتبّع التقرير' },
    reportTraceabilitySub: { en: 'Every finding is traceable to its evidence IDs.', ar: 'يكون كل تقييم قابلاً للتتبع لمعرّفات الأدلة الخاصة به.' },
    reportTraceabilityEmpty: { en: 'No evidence references available.', ar: 'لا توجد مرجعيات أدلة متاحة.' },
    teamSection: { en: 'Project credits', ar: 'شكر وتقدير المشروع' },
    stampArea: { en: 'Verification', ar: 'التحقق' },
    stampLine: {
      en: 'Generated locally by BASIRAH. This identifier is a local reference only — it is not a cryptographic signature, a certificate, or a legal attestation.',
      ar: 'أُنشئ محلياً بواسطة بصيرة. هذا المعرّف مرجع محلي فقط — وليس توقيعاً تشفيرياً ولا شهادة ولا تصديقاً قانونياً.',
    },
    exportedBy: { en: 'Exported', ar: 'تم التصدير' },
    teamCredits: { en: 'Project team', ar: 'فريق المشروع' },
    noEvidence: {
      en: 'No evidence nodes were returned for this analysis.',
      ar: 'لم تُعقد عقد أدلة لهذا التحليل.',
    },
    noTimeline: {
      en: 'No investigation stages were recorded.',
      ar: 'لم تُسجَّل مراحل تحقيق.',
    },
    noLimitations: {
      en: 'No limitation statements were supplied for this run.',
      ar: 'لم تُقدَّم أي قيود لهذا التشغيل.',
    },
    notMeasured: { en: 'Not measured', ar: 'لم يُقَس' },
    graph: {
      title: { en: 'Evidence graph', ar: 'الرسم البياني للأدلة' },
      subtitle: { en: 'Click a node to inspect; hover to highlight related evidence.', ar: 'انقر على العقدة للتفاصيل؛ التحويم على الأدلة ذات الصلة.' },
      select: { en: 'Select a node for details', ar: 'اختر عقدة لعرض التفاصيل' },
      correlations: { en: 'Cross-modal correlations', ar: 'روابط متعددة النماذج' },
      correlations_title: { en: 'Cross-modal correlations', ar: 'روابط متعددة النماذج' },
      filter_title: { en: 'Filter by category', ar: 'تصفية حسب الفئة' },
      clear: { en: 'Clear filter', ar: 'مسح الفلتر' },
      detailLabel: { en: 'evidence details', ar: 'تفاصيل الأدلة' },
    },
  /* Mandatory on every report, in both languages. */
    disclaimer: {
      en: 'BASIRAH provides advisory, probabilistic analysis. This report should not be considered definitive proof or used as the sole basis for a decision.',
      ar: 'توفر بصيرة تحليلاً استشارياً واحتمالياً. لا ينبغي اعتبار هذا التقرير دليلاً قاطعاً أو استخدامه كأساس منفرد لاتخاذ قرار.',
    },
    stamp: {
      project: 'BASIRAH',
      descriptorEn: 'Digital Trust Intelligence',
      descriptorAr: 'استخبارات الثقة الرقمية',
      titleEn: 'Generated Analysis Report',
      titleAr: 'تقرير تحليل مُنشأ',
    },
    modalities: {
      image: { en: 'Image analysis', ar: 'تحليل صورة' },
      screenshot: { en: 'Screenshot analysis', ar: 'تحليل لقطة شاشة' },
      qr: { en: 'Image containing QR code', ar: 'صورة تحتوي رمز QR' },
      url: { en: 'URL analysis', ar: 'تحليل رابط' },
      text: { en: 'Text analysis', ar: 'تحليل نص' },
      file: { en: 'File analysis', ar: 'تحليل ملف' },
    },
  },

  /* ------------------------------------------------------------------ */
  /* Exports                                                             */
  exportSection: {
    print: { en: 'Print', ar: 'طباعة' },
    pdf: { en: 'Save as PDF', ar: 'حفظ كـ PDF' },
    pdfHint: {
      en: 'Opens your browser’s print dialogue with the report laid out for A4. Choose “Save as PDF” as the destination.',
      ar: 'يفتح حوار الطباعة في متصفحك بتنسيق التقرير لمقاس A4. اختر «حفظ كـ PDF» كوجهة.',
    },
    excel: { en: 'Export Excel', ar: 'تصدير Excel' },
    excelHint: {
      en: 'A structured workbook with one sheet per evidence category — never a raw data dump.',
      ar: 'مصنَّف منظم بورقة لكل فئة من الأدلة — لا تفريغ خام للبيانات.',
    },
    preparing: { en: 'Preparing…', ar: 'جارٍ التحضير…' },
    printPreparing: { en: 'Opening print dialogue…', ar: 'جارٍ فتح حوار الطباعة…' },
    excelPreparing: { en: 'Building workbook…', ar: 'جارٍ إنشاء المصنَّف…' },
    failed: { en: 'The export could not be produced.', ar: 'تعذّر إنتاج الملف.' },
    done: { en: 'Export ready', ar: 'الملف جاهز' },
    printControlsLabel: { en: 'Report export options', ar: 'خيارات تصدير التقرير' },
    openPdfDialog: { en: 'Choose “Save as PDF” in the destination list', ar: 'اختر «حفظ كـ PDF» من قائمة الوجهة' },
  },

  /* ------------------------------------------------------------------ */
  /* Evidence graph — flat keys for Phase 4 */
  /* ------------------------------------------------------------------ */
  graphTitle: { en: 'Evidence graph', ar: 'الرسم البياني للأدلة' },
  graphSubtitle: { en: 'Click a node to inspect; hover to highlight related evidence.', ar: 'انقر على العقدة للتفاصيل؛ التحويم على الأدلة ذات الصلة.' },
  graphSelect: { en: 'Select a node for details', ar: 'اختر عقدة لعرض التفاصيل' },
  graphDetailLabel: { en: 'evidence details', ar: 'تفاصيل الأدلة' },
  graphCorrelations: { en: 'Cross-modal correlations', ar: 'روابط متعددة النماذج' },
  graphFilterTitle: { en: 'Filter by category', ar: 'تصفية حسب الفئة' },
  graphClear: { en: 'Clear filter', ar: 'مسح الفلتر' },
  filterTitle: { en: 'Filter by category', ar: 'تصفية حسب الفئة' },
  filterClear: { en: 'Clear filter', ar: 'مسح الفلتر' },

  /* ------------------------------------------------------------------ */
  /* Overview (landing)                                                 */
  /* ------------------------------------------------------------------ */
  overview:{
    eyebrow: {
      en: 'Digital trust · suspicious content detection',
      ar: 'الثقة الرقمية · كشف المحتوى المشبوه',
    },
    valueTitle: {
      en: 'Images first. Links second. Evidence throughout.',
      ar: 'الصور أولاً، والروابط ثانياً، والأدلة في كل خطوة.',
    },
    valueBody: {
      en: 'Most people meet manipulated media long before they meet a suspicious link. BASIRAH is built for that order: image and content intelligence is the primary modality, URL analysis is the secondary one, and every verdict is decomposed into the evidence that produced it.',
      ar: 'ي большин الناس يواجهون الوسائط المُعدَّلة قبل أن يواجهون رابطاً مشبوهاً. بُنيت بصيرة على هذا الترتيب: ذكاء الصور والمحتوى هو الوسيلة الأساسية، وتحليل الروابط هو الوسيلة الثانوية، وكل نتيجة تُفكَّك إلى الأدلة التي أنتجتها.',
    },
    secondaryCta: { en: 'Explore Capabilities', ar: 'استكشف الإمكانات' },
    quickActionsTitle: { en: 'Quick actions', ar: 'إجراءات سريعة' },
    quickActionsSub: {
      en: 'Jump straight to the part of the platform you need.',
      ar: 'انتقل مباشرة إلى الجزء الذي تحتاجه من المنصة.',
    },
    actionAnalyzeImage: { en: 'Analyze an image', ar: 'حلّل صورة' },
    actionAnalyzeImageSub: {
      en: 'Primary modality — research-grade synthetic-media detection',
      ar: 'الوسيلة الأساسية — كشف الوسائط المُولَّدة بمستوى بحثي',
    },
    actionAnalyzeLink: { en: 'Analyze a link', ar: 'حلّل رابطاً' },
    actionAnalyzeLinkSub: {
      en: 'Secondary modality — URL structure, identity and domain signals',
      ar: 'الوسيلة الثانوية — بنية الرابط والهوية وإشارات النطاق',
    },
    actionCategories: { en: 'Browse detection categories', ar: 'تصفّح فئات الكشف' },
    actionCategoriesSub: {
      en: 'What BASIRAH looks for, and what is not built yet',
      ar: 'ما الذي تبحث عنه بصيرة، وما لم يُبنَ بعد',
    },
    actionMethodology: { en: 'Read the methodology', ar: 'اقرأ المنهجية' },
    actionMethodologySub: {
      en: 'How the assessment is produced and what it cannot establish',
      ar: 'كيف يُنتَج التقييم وما الذي لا يستطيع إثباته',
    },
    scrollHint: { en: 'Scroll', ar: 'مرّر' },
  },

  /* ------------------------------------------------------------------ */
  /* Detection categories                                               */
  /* ------------------------------------------------------------------ */
  categories: {
    title: { en: 'Detection categories', ar: 'فئات الكشف' },
    subtitle: {
      en: 'What BASIRAH is built to detect — and the honest state of each one. Planned categories are named so the roadmap is visible rather than hidden; none of them analyse anything yet.',
      ar: 'ما هي الفئات التي بُنيت بصيرة لكشفها، والحالة الصادقة لكل منها. الفئات المخططة مذكورة ليظهر خارطة الطريق بصدق، وهي لا تحلّل أي شيء بعد.',
    },
    statusLabel: { en: 'State', ar: 'الحالة' },
    images: {
      name: { en: 'Suspicious Images', ar: 'الصور المشبوهة' },
      body: {
        en: 'The primary modality. Synthetic-media likelihood with an explicit uncertainty band, plus the raw measurements behind it: embedded metadata, forensic characteristics and content provenance.',
        ar: 'الوسيلة الأساسية. احتمال الوسائط المُولَّدة مع نطاق عدم يقين صريح، إضافةً إلى القياسات الخام التي تقف خلفه: البيانات الوصفية المضمّنة والخصائص الجنائية ومصدر المحتوى.',
      },
    },
    files: {
      name: { en: 'Digital Files & Evidence', ar: 'الملفات الرقمية والأدلة' },
      body: {
        en: 'Active for supported safe text formats. Structure, extracted text, embedded URLs, emails, IPs and encoded payloads are reported. A refused format is reported with its reason and is never presented as clean.',
        ar: 'نشط لصيغ النص الآمنة المدعومة. تُعرض البنية والنص المستخرج والروابط والبريد وعناوين IP والحمولات المشفّرة. أما الصيغة المرفوضة فتُعرض مع سببها ولا تُقدَّم أبداً على أنها نظيفة.',
      },
    },
    encoded: {
      name: { en: 'Encoded / Hidden Content', ar: 'المحتوى المشفّر أو المخفي' },
      body: {
        en: 'Active for text payloads inside accepted files. Each finding shows the raw and the decoded side by side, so the reader can judge the decode rather than trust it.',
        ar: 'نشط للحمولات النصية داخل الملفات المقبولة. تُعرض كل نتيجة خاماً ومفكوكة جنباً إلى جنب، ليحكم القارئ على فك الترميز لا أن يثق به.',
      },
    },
    urls: {
      name: { en: 'Suspicious URLs', ar: 'الروابط المشبوهة' },
      body: {
        en: 'Active and advisory. Domain structure, lexical entropy, identity signals and reputation context for a pasted link.',
        ar: 'نشطة وإرشادية. بنية النطاق والعشوائية اللفظية وإشارات الهوية وسياق السمعة للرابط الملصوق.',
      },
    },
    ocr: {
      name: { en: 'Screenshot / OCR', ar: 'لقطات الشاشة والتعرف الضوئي' },
      body: {
        en: 'Active. Text is read out of screenshots so a fake interface can be compared against what it claims to show. Every engine that ran is named; Arabic is supported but weaker than English.',
        ar: 'نشط. يُستخرج النص من لقطات الشاشة حتى يمكن مقارنة واجهة مزيفة بما تدّعي عرضه. ويُذكر اسم كل محرك عمل؛ والعربية مدعومة لكن أضعف من الإنجليزية.',
      },
    },
    qr: {
      name: { en: 'QR Analysis', ar: 'تحليل رموز الاستجابة السريعة' },
      body: {
        en: 'Active. QR payloads are decoded and, when they are URLs, scored as strings by URL Intelligence. Nothing is opened or followed.',
        ar: 'نشط. تُفك رموز الاستجابة السريعة، وإذا كانت روابط تُقيَّم كنصوص بواسطة استخبارات الروابط. ولا يُفتح أي شيء ولا يُتبع.',
      },
    },
    correlation: {
      name: { en: 'Trust & Evidence Correlation', ar: 'ربط الثقة والأدلة' },
      body: {
        en: 'Active as evidence fusion. Findings from every modality are ranked by evidence tier and correlated into one explainable assessment rather than a single opaque verdict.',
        ar: 'نشط كدمج للأدلة. تُرتَّب نتائج كل الوسائل حسب درجة الدليل وتُربط في تقييم واحد قابل للتفسير بدلاً من حكم غامض واحد.',
      },
    },
    c2pa: {
      name: { en: 'C2PA Content Credentials', ar: 'بيانات اعتماد C2PA' },
      body: {
        en: 'Limited. Manifests are located and signature validation is attempted. This is not a full trust-list implementation, and the module is labelled Limited wherever its status is shown.',
        ar: 'محدودة. تُحدَّد البيانات وتُحاول التحقق من التوقيع. ليست تنفيذاً كاملاً لقائمة ثقة، وتُوصف الوحدة بأنها محدودة أينما ظهرت حالتها.',
      },
    },
  },

  /* ------------------------------------------------------------------ */
  /* Module states — the only vocabulary this product uses about itself */
  /* ------------------------------------------------------------------ */
  state: {
    active: { en: 'Active', ar: 'نشط' },
    researchGrade: { en: 'Research-grade', ar: 'مستوى بحثي' },
    advisory: { en: 'Advisory', ar: 'إرشادي' },
    planned: { en: 'Planned', ar: 'مخططة' },
    comingSoon: { en: 'Coming Soon', ar: 'قريباً' },
    inDevelopment: { en: 'In development', ar: 'قيد التطوير' },
    expanding: { en: 'Expanding', ar: 'قيد التوسع' },
    capability: { en: 'Platform Capability', ar: 'إمكانية في المنصة' },
    /** LIMITED is its own state, not a flavour of active. */
    limited: { en: 'Limited', ar: 'محدودة' },
  },
  /* ------------------------------------------------------------------ */
  capabilities: {
    title: { en: 'Capabilities', ar: 'الإمكانات' },
    subtitle: {
      en: 'What the platform measures, and how each finding is reported. Nothing here is a marketing claim: every entry names the measurement it rests on.',
      ar: 'ما الذي تقيسه المنصة وكيف يُعرض كل تقييم. لا شيء هنا ادعاء تسويقي: كل مدخل يذكر القياس الذي يستند إليه.',
    },
    imageIntelligence: {
      name: { en: 'Image Ensemble', ar: 'كواشف الصور' },
      body: {
        en: 'Active, research-grade and advisory. Two independent detectors run on every image; they are reported separately and are never averaged into one number.',
        ar: 'نشطة بمستوى بحثي وإرشادية. يعمل كاشفان مستقلان على كل صورة، ويُعرضان منفصلين ولا يُدمجان في رقم واحد أبداً.',
      },
      state: 'researchGrade',
    },
    urlIntelligence: {
      name: { en: 'URL Intelligence', ar: 'استخبارات الروابط' },
      body: {
        en: 'Active and advisory. Structural and lexical analysis of a pasted link: domain shape, subdomain depth, character entropy and identity signals. URLs are scored as strings — nothing is fetched.',
        ar: 'نشطة وإرشادية. تحليل بنيوي ولفظي للرابط الملصوق: شكل النطاق وعمق النطاقات الفرعية وعشوائية الأحرف وإشارات الهوية. تُقيَّم الروابط كنصوص — ولا يُجلب أي شيء.',
      },
      state: 'advisory',
    },
    trustDna: {
      name: { en: 'Trust DNA', ar: 'بصمة الثقة' },
      body: {
        en: 'A five-axis fingerprint of the analysed signal. An axis that was not measured carries no value at all — a blank axis is more honest than a low score.',
        ar: 'بصمة من خمسة محاور للإشارة المحلَّلة. المحور الذي لم يُقاس يحمل لا قيمة إطلاقاً، فالمحور الفارغ أصدق من درجة منخفضة.',
      },
      state: 'active',
    },
    evidenceGraph: {
      name: { en: 'Evidence Graph', ar: 'رسم الأدلة' },
      body: {
        en: 'Every finding as a node, with the relationships between them: what one signal asserts, contradicts or derives from another.',
        ar: 'كل تقييم كعقدة، مع العلاقات بينها: ما يثبته أي مصدر أو يناقضه أو يشتقه من مصدر آخر.',
      },
      state: 'active',
    },
    timeline: {
      name: { en: 'Investigation Timeline', ar: 'الخط الزمني للتحقيق' },
      body: {
        en: 'The ordered record of what was examined. Stage order follows the signal submitted, so a link and an image produce different — and equally honest — journeys.',
        ar: 'السجل المرتّب لما جرى فحصه. يتبع ترتيب المراحل الإشارة المُرسَلة، فينتج الرابط والصورة رحلتين مختلفتين وكلتاهما صادقتان.',
      },
      state: 'active',
    },
    correlation: {
      name: { en: 'Multimodal Correlation', ar: 'الربط متعدد الوسائط' },
      body: {
        en: 'Combining image and link findings into a single assessment. Under development; the current release analyses one signal at a time.',
        ar: 'دمج نتائج الصور والروابط في تقييم واحد. قيد التطوير؛ النسخة الحالية تحلل إشارة واحدة في كل مرة.',
      },
      state: 'inDevelopment',
    },
    provenance: {
      name: { en: 'Provenance & Forensics', ar: 'مصدر المحتوى والخصائص الجنائية' },
      body: {
        en: 'Measured image characteristics, each reported with what it does not establish — the limitation travels with the finding.',
        ar: 'خصائص الصورة المقاسة، كل منها يُعرض مع ما لا تثبته، فيسير القيد مع النتيجة.',
      },
      state: 'active',
    },
    fileIntelligence: {
      name: { en: 'File Intelligence', ar: 'ذكاء الملفات' },
      body: {
        en: 'Active for supported safe text formats. A refused format is reported with the backend’s own reason and is not analysed — refusal is not a clean result.',
        ar: 'نشط لصيغ النص الآمنة المدعومة. أما الصيغة المرفوضة فتُعرض مع سبب الرفض من المحرك ولا تُحلَّل — والرفض ليس نتيجة نظيفة.',
      },
      state: 'active',
    },
    screenshotOcr: {
      name: { en: 'Screenshot / OCR', ar: 'لقطات الشاشة والتعرف الضوئي' },
      body: {
        en: 'Active. Every engine that ran is named. Arabic OCR is available but weaker than English, especially on small or low-contrast type.',
        ar: 'نشط. يُذكر اسم كل محرك عمل. التعرّف الضوئي للعربية متاح لكنه أضعف من الإنجليزية، خاصة مع الخط الصغير أو منخفض التباين.',
      },
      state: 'active',
    },
    qrExtraction: {
      name: { en: 'QR Extraction', ar: 'استخراج رموز الاستجابة السريعة' },
      body: {
        en: 'Active. A decoded payload is treated as a string candidate and scored by URL Intelligence — it is never opened.',
        ar: 'نشط. يُعامل المحتوى المفكوك كمرشّح نصي وتقيّمه استخبارات الروابط — ولا يُفتح أبداً.',
      },
      state: 'active',
    },
    encodedContent: {
      name: { en: 'Encoded Content Analysis', ar: 'تحليل المحتوى المشفّر' },
      body: {
        en: 'Active. Base64, hex and URL-encoded payloads found inside accepted text files are shown raw and decoded, side by side.',
        ar: 'نشط. تُعرض الحمولات المشفّرة base64 وhex وتشفير الروابط الموجودة داخل الملفات النصية المقبولة خاماً ومفكوكة جنباً إلى جنب.',
      },
      state: 'active',
    },
    c2pa: {
      name: { en: 'C2PA / Content Credentials', ar: 'C2PA / بيانات الاعتماد' },
      body: {
        en: 'LIMITED. Manifests are located and signature validation is attempted, but this is not a full trust-list implementation. It is never labelled verified without an actual signature check.',
        ar: 'محدودة. تُحدَّد البيانات وتُحاول التحقق من التوقيع، لكنها ليست تنفيذاً كاملاً لقائمة ثقة. لا تُوصف بأنها موثَّقة دون فحص توقيع فعلي.',
      },
      state: 'limited',
    },
    evidenceFusion: {
      name: { en: 'Evidence Fusion', ar: 'دمج الأدلة' },
      body: {
        en: 'Active. Findings are ranked by evidence tier. A verified provenance assertion outranks a pixel detector, and a high-risk destination is not diluted by an image that merely looks real.',
        ar: 'نشط. تُرتَّب النتائج حسب درجة الدليل. يتفوق إقرار مصدر موثَّق على كاشف البكسلات، ولا يُخفَّف وجهة عالية الخطورة بصورة تبدو سليمة فقط.',
      },
      state: 'active',
    },
  },

  /* ------------------------------------------------------------------ */
  /* Dashboard / platform summary                                       */
  /* ------------------------------------------------------------------ */
  dashboard: {
    title: { en: 'Platform summary', ar: 'ملخص المنصة' },
    subtitle: {
      en: 'The system state, as it actually is. No usage counters, no accuracy figures, no uptime claims — those numbers do not exist yet, and inventing them would make every other number on this page unreadable.',
      ar: 'حالة النظام كما هي فعلاً. لا عدادات استخدام ولا نسب دقة ولا ادعاءات توافر، فتلك الأرقام غير موجودة بعد، وافتراخها يجعل كل رقم آخر في هذه الصفحة غير مقروء.',
    },
    activeModulesTitle: { en: 'Active modules', ar: 'الوحدات النشطة' },
    limitedModulesTitle: {
      en: 'Partially supported modules',
      ar: 'الوحدات المدعومة جزئياً',
    },
    plannedModulesTitle: { en: 'Planned modules', ar: 'الوحدات المخططة' },
    trustFrameworkTitle: { en: 'Trust framework', ar: 'إطار الثقة' },
    trustFrameworkSub: {
      en: 'Principles that hold regardless of which modules are live.',
      ar: 'مبادئ ثابتة بغض النظر عن أي الوحدات النشطة.',
    },
    statusTitle: { en: 'Platform status', ar: 'حالة المنصة' },
    evidenceCorrelation: { en: 'Evidence correlation', ar: 'ربط الأدلة' },
    probabilistic: { en: 'Probabilistic assessment', ar: 'تقييم احتمالي' },
    advisoryOnly: { en: 'Advisory only', ar: 'إرشادي فقط' },
    trustCorrelationBody: {
      en: 'Findings from every active modality are combined into one assessment, with each contributing signal shown to the reader.',
      ar: 'تُدمج نتائج كل الوسائل النشطة في تقييم واحد، مع عرض كل إشارة مساهمة للقارئ.',
    },
    trustProbabilisticBody: {
      en: 'Every output is a likelihood with a stated confidence and an uncertainty band — never a binary verdict.',
      ar: 'كل مخرَج احتمال مُصرَّح بثقته ونطاق عدم يقينه، ولا يكون حكماً ثنائياً أبداً.',
    },
    trustAdvisoryBody: {
      en: 'BASIRAH output supports a human decision. It is never proof, and never the sole basis for one.',
      ar: 'مخرجات بصيرة تدعم قرار الإنسان، وهي ليست دليلاً قاطعاً ولا أساساً منفرداً لقرار.',
    },
    honestyNoteTitle: { en: 'Why no metrics are shown', ar: 'لماذا لا تُعرض أرقام' },
    honestyNoteBody: {
      en: 'Threat counts, accuracy percentages and availability figures would all be fabrications at this stage. Until they can be measured and published honestly, the platform reports only what it can demonstrate: which modules exist, and what state each one is in.',
      ar: 'أعداد التهديدات ونسب الدقة وأرقام التوافر ستكون كلها افتراحات في هذه المرحلة. وحين يمكن قياسها ونشرها بصدق، تُبلّغ المنصة فقط عمّا تستطيع إثباته: أي الوحدات موجودة وفي أي حالة.',
    },
  },

  /* ------------------------------------------------------------------ */
  /* Team                                                               */
  /* ------------------------------------------------------------------ */
  team: {
    title: { en: 'Project team', ar: 'فريق المشروع' },
    subtitle: {
      en: 'Undergraduate Artificial Intelligence students at the University of Bisha, working on BASIRAH as a graduation project.',
      ar: 'طلاب بكالوريوس الذكاء الاصطناعي بجامعة بيشة، يعملون على بصيرة كمشروع تخرج.',
    },
    specializationLabel: { en: 'Specialization', ar: 'التخصص' },
    studentIdLabel: { en: 'Student ID', ar: 'الرقم الجامعي' },
    roleLabel: { en: 'Role', ar: 'الدور' },
    leader: { en: 'Leader', ar: 'قائد الفريق' },
    member: { en: 'Team member', ar: 'عضو فريق' },
    previewTitle: { en: 'Team', ar: 'الفريق' },
    viewTeam: { en: 'View the full team', ar: 'عرض الفريق كاملاً' },
    universityTitle: { en: 'Academic affiliation', ar: 'الجهة الأكاديمية' },
    universityName: { en: 'University of Bisha', ar: 'جامعة بيشة' },
    universitySub: {
      en: 'College of Computer Science · Graduation project',
      ar: 'كلية الحاسب الآلي · مشروع تخرج',
    },
  },
  /* ------------------------------------------------------------------ */
  language: {
    toggle: { en: 'Switch language', ar: 'تغيير اللغة' },
    switchToArabic: { en: 'التبديل إلى العربية', ar: 'التبديل إلى العربية' },
    switchToEnglish: { en: 'Switch to English', ar: 'التبديل إلى الإنجليزية' },
  },

/* ------------------------------------------------------------------ */
  status: {
    label: { en: 'System', ar: 'النظام' },
    demoMode: { en: 'Service offline', ar: 'الخدمة غير متاحة' },
    live: { en: 'Live analysis', ar: 'تحليل مباشر' },
    tooltip: {
      en: 'The analysis service could not be reached. Submissions will fail rather than return a fabricated result.',
      ar: 'تعذّر الوصول إلى خدمة التحليل. ستفشل عمليات الإرسال بدلاً من إعادة نتيجة مفبركة.',
    },
    liveTooltip: {
      en: 'Image and URL analysis run against the BASIRAH backend. Image results are research-grade; URL results are advisory. Everything is probabilistic.',
      ar: 'يتحقق تحليل الصور والروابط عبر خادم بصيرة. نتائج الصور بمستوى بحثي، ونتائج الروابط إرشادية. وكلها احتمالية.',
    },
  },

  header: {
    openAbout: { en: 'Open project information', ar: 'فتح معلومات المشروع' },
    closeAbout: { en: 'Close project information', ar: 'إغلاق معلومات المشروع' },
  },

  /* ------------------------------------------------------------------ */
  core: {
    idleHint: { en: 'Awaiting signal', ar: 'بانتظار الإشارة' },
    dragHint: { en: 'Release to investigate', ar: 'أفلت للتحقيق' },
    analyzingHint: { en: 'Analyzing signal', ar: 'يتم تحليل الإشارة' },
    resultHint: { en: 'Signal resolved', ar: 'تم حل الإشارة' },
    statusIdle: { en: 'IDLE', ar: 'خامل' },
    statusDragging: { en: 'DRAG', ar: 'سحب' },
    statusAnalyzing: { en: 'ACTIVE', ar: 'نشط' },
    statusResult: { en: 'RESOLVED', ar: 'مُحلَّلة' },
  },

  /* ------------------------------------------------------------------ */
  /* Analysis workspace — image is the primary intake, URL the secondary */
  /* ------------------------------------------------------------------ */
  workspace: {
    title: { en: 'Analysis workspace', ar: 'مساحة التحليل' },
    subtitle: {
      en: 'Submit a signal. Image intake is primary; link intake is secondary, and both run the same evidence pipeline.',
      ar: 'أرسل إشارة. استقبال الصور هو الأساسي، واستقبال الروابط هو الثانوي، وكلاهما يمرّ بنفس خط الأدلة.',
    },
    primaryTitle: { en: 'Primary — image analysis', ar: 'أساسي — تحليل الصور' },
    secondaryTitle: { en: 'Secondary — link analysis', ar: 'ثانوي — تحليل الروابط' },
    primaryNote: {
      en: 'Upload or drop an image. This is the modality the platform is built around.',
      ar: 'ارفع صورة أو أفلتها. هذه هي الوسيلة التي بُنيت حولها المنصة.',
    },
    secondaryNote: {
      en: 'Paste a link to inspect its structure, identity and domain signals.',
      ar: 'الصق رابطاً لفحص بنيته وإشارات هويته ونطاقه.',
    },
    title4: {
      en: 'Submit a signal in one of four modes. Three are uploads analysed end to end; the fourth is a link scored as a string.',
      ar: 'أرسل إحدى أربع إشارات. ثلاث منها رفعات تُحلَّل من طرف إلى طرف، والرابعة رابط يُقيَّم كنص.',
    },
  },

  input: {
    dropAnything: {
      en: 'Drop an image, a screenshot or a file — or paste a link.',
      ar: 'أفلت صورة أو لقطة شاشة أو ملفاً — أو الصق رابطاً.',
    },
    sub: {
      en: 'Image intelligence is primary here. Uploads run the full evidence chain; a pasted link is scored as a string and never fetched.',
      ar: 'ذكاء الصور هو الأساس هنا. تمر الرفعات بسلسلة الأدلة كاملة؛ والرابط الملصوق يُقيَّم كنص ولا يُجلب أبداً.',
    },
    placeholder: {
      en: 'Paste a URL, or drop a file',
      ar: 'الصق رابطاً، أو أفلت ملفاً',
    },
    fileButton: { en: 'Select a file', ar: 'اختر ملفاً' },
    clipboardHint: {
      en: 'Tip: press Ctrl+V to paste an image directly',
      ar: 'نصيحة: اضغط Ctrl+V للصق صورة مباشرة',
    },
    acceptHint: {
      en: 'Images, screenshots and safe text files. A refused format is reported with its reason, not silently dropped.',
      ar: 'الصور ولقطات الشاشة وملفات النص الآمنة. أما الصيغة المرفوضة فتُعرض مع سببها لا تُهمَل بصمت.',
    },
    receivedUrl: { en: 'URL signal captured', ar: 'تم التقاط إشارة رابط' },
    receivedImage: { en: 'Image signal captured', ar: 'تم التقاط إشارة صورة' },
    receivedScreenshot: { en: 'Screenshot captured', ar: 'تم التقاط لقطة شاشة' },
    receivedFile: { en: 'File captured', ar: 'تم التقاط ملف' },
    receivedQr: { en: 'Image containing a QR code', ar: 'صورة تحتوي رمز استجابة سريعة' },
    imagePreviewAlt: { en: 'Captured signal preview', ar: 'معاينة الإشارة الملتقطة' },
  },

  /* ------------------------------------------------------------------ */
  journey: {
    title: { en: 'Analysis journey', ar: 'رحلة التحليل' },
    stages: {
      acquire: { en: 'Signal acquired', ar: 'تم التقاط الإشارة' },
      identify: { en: 'Content type identified', ar: 'تم التعرف على نوع المحتوى' },
      visual: { en: 'Visual structure extracted', ar: 'تم استخراج البنية البصرية' },
      url: { en: 'URL structure inspected', ar: 'تم فحص بنية الرابط' },
      metadata: { en: 'Metadata examined', ar: 'تم فحص البيانات الوصفية' },
      provenance: { en: 'Provenance checked', ar: 'تم التحقق من المصدر' },
      synthetic: { en: 'Synthetic indicators evaluated', ar: 'تم تقييم مؤشرات التوليد' },
      correlate: { en: 'Evidence correlated', ar: 'تم ربط الأدلة' },
      score: { en: 'Trust score computed', ar: 'تم احتساب درجة الثقة' },
    },
    lanes: {
      urlIntel: { en: 'URL Intelligence', ar: 'استخبارات الروابط' },
      syntheticMedia: { en: 'Synthetic Media', ar: 'الوسائط المُولَّدة' },
      metadata: { en: 'Metadata', ar: 'البيانات الوصفية' },
      provenance: { en: 'Provenance', ar: 'مصدر المحتوى' },
      identity: { en: 'Identity Analysis', ar: 'تحليل الهوية' },
      fusion: { en: 'Evidence Fusion', ar: 'دمج الأدلة' },
      score: { en: 'Trust Score', ar: 'درجة الثقة' },
    },
    progressLabel: { en: 'Analysis progress', ar: 'تقدم التحليل' },
  },

  /* ------------------------------------------------------------------ */
  score: {
    title: { en: 'Trust Score', ar: 'درجة الثقة' },
    outOf: { en: '/ 100', ar: '/ ١٠٠' },
    classificationLabel: { en: 'Classification', ar: 'التصنيف' },
    trusted: { en: 'Trusted', ar: 'موثوق' },
    caution: { en: 'Caution', ar: 'تحفّظ' },
    highRisk: { en: 'High risk', ar: 'خطورة عالية' },
    confidenceLabel: { en: 'Model confidence', ar: 'ثقة النموذج' },
    provisional: {
      en: 'A probabilistic assessment of the evidence gathered for this signal. It supports a human decision; it is not proof of anything on its own.',
      ar: 'تقييم احتمالي استناداً إلى الأدلة المجموعة لهذه الإشارة. يدعم قرار الإنسان، ولا يُعد دليلاً على شيء بذاته.',
    },
  },

  dna: {
    title: { en: 'Trust DNA', ar: 'بصمة الثقة' },
    subtitle: {
      en: 'Visual fingerprint of the analyzed signal',
      ar: 'بصمة بصرية للإشارة التي تم تحليلها',
    },
    axes: {
      synthetic: { en: 'Synthetic', ar: 'التوليد' },
      identity: { en: 'Identity', ar: 'الهوية' },
      domain: { en: 'Domain', ar: 'النطاق' },
      provenance: { en: 'Provenance', ar: 'المصدر' },
      behavior: { en: 'Behavior', ar: 'السلوك' },
    },
    scaleLabel: {
      en: 'Higher value = stronger signal detected on this axis',
      ar: 'القيمة الأعلى = إشارة أقوى على هذا المحور',
    },
  },

  graph: {
    title: { en: 'Evidence Graph', ar: 'رسم الأدلة' },
    subtitle: {
      en: 'How each signal relates to the others',
      ar: 'العلاقة بين كل إشارة والأخرى',
    },
    hoverHint: {
      en: 'Select a node to trace its connections',
      ar: 'اختر عقدة لتتبّع علاقاتها',
    },
    selectNode: { en: 'Select node', ar: 'اختر عقدة' },
    clearSelection: { en: 'Clear selection', ar: 'إلغاء التحديد' },
  },

  timeline: {
    title: { en: 'Investigation timeline', ar: 'الخط الزمني للتحقيق' },
    emptyState: {
      en: 'No investigation has been run yet.',
      ar: 'لم يُجرَ أي تحقيق بعد.',
    },
    contentHistory: { en: 'Content history (C2PA)', ar: 'سجل المحتوى (C2PA)' },
  },

  explanation: {
    title: { en: 'Why BASIRAH flagged this', ar: 'لماذا أبلغت بصيرة عن هذا' },
    primaryLabel: { en: 'Primary signal', ar: 'الإشارة الرئيسية' },
    secondaryLabel: { en: 'Secondary signals', ar: 'الإشارات الثانوية' },
    noPrimary: {
      en: 'No single dominant indicator — findings are distributed across axes.',
      ar: 'لا يوجد مؤشر واحد مهيمن — النتائج موزعة على المحاور.',
    },
    metrics: {
      domainStructure: { en: 'Domain structure', ar: 'بنية النطاق' },
      provenance: { en: 'Provenance', ar: 'مصدر المحتوى' },
      urlEntropy: { en: 'URL entropy', ar: 'عشوائية الرابط' },
      syntheticConfidence: { en: 'Synthetic confidence', ar: 'ثقة التوليد' },
      brandMatch: { en: 'Brand match', ar: 'تطابق العلامة' },
    },
    values: {
      high: { en: 'High', ar: 'مرتفع' },
      elevated: { en: 'Elevated', ar: 'مرتفع' },
      low: { en: 'Low', ar: 'منخفض' },
      unavailable: { en: 'Unavailable', ar: 'غير متاح' },
      partial: { en: 'Partial', ar: 'جزئي' },
      mismatch: { en: 'Mismatch', ar: 'عدم تطابق' },
    },
  },

  /* ------------------------------------------------------------------ */
  image: {
    verdict: {
      label: { en: 'Classification', ar: 'التصنيف' },
      titleLikelySynthetic: {
        en: 'Likely Synthetic',
        ar: 'يُرجّح أن الصورة اصطناعية',
      },
      titleLikelyAuthentic: {
        en: 'Likely Authentic',
        ar: 'يُرجّح أن الصورة أصلية',
      },
      titleUncertain: { en: 'Uncertain', ar: 'غير مؤكَّد' },
      likelySynthetic: {
        en: 'Indicators associated with synthetic media were detected.',
        ar: 'تم رصد مؤشرات مرتبطة بالمحتوى الاصطناعي.',
      },
      likelyAuthentic: {
        en: 'No strong synthetic-media indicators were detected.',
        ar: 'لم يتم رصد مؤشرات قوية للمحتوى الاصطناعي.',
      },
      uncertain: {
        en: 'Insufficient evidence for a confident classification.',
        ar: 'الأدلة غير كافية للتصنيف بثقة.',
      },
      probabilityLabel: {
        en: 'Synthetic-media likelihood',
        ar: 'احتمال يكون محتوى اصطناعيًا',
      },
      confidenceLabel: { en: 'Model confidence', ar: 'ثقة النموذج' },
      uncertaintyLabel: { en: 'Uncertainty state', ar: 'حالة عدم اليقين' },
      uncertaintyInside: {
        en: 'Falls inside the uncertain band derived from held-out validation, so no directional call is made.',
        ar: 'تقع ضمن النطاق غير المؤكد المشتق من بيانات التحقق والاحتفاظ، لذلك لا يُتَّخذ اتجاه حاسم.',
      },
      uncertaintyResolved: {
        en: 'Outside the uncertain band — the result is reported as a directional likelihood, not a certainty.',
        ar: 'خارج النطاق غير المؤكد — تُعرض النتيجة كانتمال اتجاهي لا كيقين.',
      },
      probabilityUnavailable: {
        en: 'No probability was produced. The detection model was unavailable for this image.',
        ar: 'لم يُنتَج أي احتمال. كان نموذج الكشف غير متاح لهذه الصورة.',
      },
      readSource: { en: 'Not applicable to a still image', ar: 'لا ينطبق على صورة ثابتة' },
    },
    quality: {
      title: { en: 'Evidence quality', ar: 'جودة الأدلة' },
      subtitle: {
        en: 'Limits on how much this image can support',
        ar: 'حدود ما يمكن لهذه الصورة أن تدعمه',
      },
      longEdge: { en: 'Longest edge', ar: 'أطول ضلع' },
      pixels: { en: 'pixels', ar: 'بكسل' },
      titleWarning: { en: 'This image cannot support a reliable reading', ar: 'هذه الصورة لا تدعم قراءة موثوقة' },
      titleAdvisory: {
        en: 'This image has quality limits worth knowing',
        ar: 'لهذه الصورة قيود على الجودة تستحق الاطلاع',
      },
    },
    metadata: {
      title: { en: 'Embedded metadata', ar: 'البيانات الوصفية المضمّنة' },
      subtitle: {
        en: 'What the file itself declares',
        ar: 'ما يعلنه الملف نفسه',
      },
      format: { en: 'Format', ar: 'الصيغة' },
      dimensions: { en: 'Dimensions', ar: 'الأبعاد' },
      colourMode: { en: 'Colour mode', ar: 'نمط الألوان' },
      exif: { en: 'EXIF data', ar: 'بيانات EXIF' },
      camera: { en: 'Camera', ar: 'الكاميرا' },
      software: { en: 'Software', ar: 'البرنامج' },
      created: { en: 'Recorded date', ar: 'التاريخ المسجَّل' },
      orientation: { en: 'Orientation', ar: 'الاتجاه' },
      gps: { en: 'Location data', ar: 'بيانات الموقع' },
      present: { en: 'Present', ar: 'موجود' },
      absent: { en: 'Not present', ar: 'غير موجود' },
      standard: { en: 'Standard', ar: 'قياسي' },
      orientationValue: { en: 'Orientation tag {value}', ar: 'وسم الاتجاه {value}' },
      previewAlt: { en: 'The image that was analysed', ar: 'الصورة التي تم تحليلها' },
      noPreview: {
        en: 'Preview unavailable',
        ar: 'المعاينة غير متاحة',
      },
    },
    forensics: {
      title: { en: 'Forensic characteristics', ar: 'الخصائص الجنائية' },
      subtitle: {
        en: 'Measured signals, each with what it does not establish',
        ar: 'إشارات مقاسة، مع بيان ما لا تثبته كل إشارة',
      },
      supportingLabel: { en: 'Supporting signal', ar: 'إشارة مساندة' },
      observedLabel: { en: 'Observed characteristic', ar: 'خاصية مرصودة' },
      meaningLabel: { en: 'What this indicates', ar: 'ما الذي يدل عليه' },
      doesNotMeanLabel: {
        en: 'What this does not mean',
        ar: 'ما لا يعنيه هذا',
      },
      notMeasured: { en: 'Not measured', ar: 'لم يُقَس' },
      names: {
        compression_anomaly: {
          en: 'Compression block structure',
          ar: 'بنية كتل الضغط',
        },
        high_frequency_energy: {
          en: 'High-frequency energy',
          ar: 'طاقة الترددات العالية',
        },
        noise_floor: { en: 'Noise floor', ar: 'أرضية الضوضاء' },
        spectral_slope: { en: 'Spectral slope', ar: 'ميل الطيف' },
      },
      noSignals: {
        en: 'No forensic characteristics were computed for this image.',
        ar: 'لم تُحسب أي خصائص جنائية لهذه الصورة.',
      },
      latinNote: {
        en: 'Characteristic definitions are supplied by the research pipeline in English.',
        ar: 'تعريفات الخصائص مقدَّمة من خط البحث بالإنجليزية.',
      },
    },
    provenance: {
      title: { en: 'Content provenance', ar: 'مصدر المحتوى' },
      subtitle: {
        en: 'Whether the origin of this file can be established',
        ar: 'هل يمكن إثبات مصدر هذا الملف',
      },
      verified: { en: 'Verified', ar: 'موثَّق' },
      presentUnverified: {
        en: 'Present, not verified',
        ar: 'موجود وغير موثَّق',
      },
      invalid: { en: 'Present but invalid', ar: 'موجود وغير صالح' },
      unavailable: { en: 'Unavailable', ar: 'غير متاح' },
      unavailableBody: {
        en: 'Provenance data is unavailable.',
        ar: 'بيانات إثبات المصدر غير متاحة.',
      },
      credentials: { en: 'Content credentials', ar: 'بيانات الاعتماد' },
      manifest: { en: 'Manifest', ar: 'البيان' },
      notChecked: {
        en: 'No verification was performed on the content itself.',
        ar: 'لم يُجرَ أي تحقق على المحتوى نفسه.',
      },
    },
    model: {
      title: { en: 'Model disclosure', ar: 'الإفصاح عن النموذج' },
      subtitle: {
        en: 'What produced this result, and what it may be used for',
        ar: 'ما الذي أنتج هذه النتيجة، وما يُسمح باستخدامها له',
      },
      name: { en: 'BASIRAH Image Research Candidate', ar: 'بصيرة — مرشّح بحثي للصور' },
      statusLabel: { en: 'Status', ar: 'الحالة' },
      statusValue: { en: 'Research-grade', ar: 'مستوى بحثي' },
      advisoryLabel: { en: 'Advisory only', ar: 'إرشادي فقط' },
      enforcementLabel: {
        en: 'Not fit for automated enforcement',
        ar: 'غير مناسب للتطبيق الآلي',
      },
      unavailable: { en: 'Unavailable', ar: 'غير متاح' },
      unavailableBody: {
        en: 'The detection model was not available, so no probability was produced.',
        ar: 'لم يكن نموذج الكشف متاحًا، لذلك لم يُنتَج أي احتمال.',
      },
      methodologyOpen: { en: 'View methodology', ar: 'عرض المنهجية' },
      methodologyClose: { en: 'Hide methodology', ar: 'إخفاء المنهجية' },
      limitationsTitle: { en: 'Known limitations', ar: 'القيود المعروفة' },
      familiesLabel: { en: 'Generator families in scope', ar: 'عائلات المولّدات المشمولة' },
      heldOutLabel: { en: 'Held-out evaluation family', ar: 'عائلة التقييم المحجوزة' },
      noLimitations: {
        en: 'No limitation statements were supplied for this run.',
        ar: 'لم تُقدَّم أي قيود لهذا التشغيل.',
      },
    },
    safety: {
      notice: {
        en: 'BASIRAH provides advisory, probabilistic analysis and should not be treated as definitive proof or used as the sole basis for a decision.',
        ar: 'تحليل بصيرة استشاري واحتمالي، ولا ينبغي اعتباره دليلاً قاطعًا أو أساسًا منفردًا لاتخاذ قرار.',
      },
      label: { en: 'Advisory analysis', ar: 'تحليل إرشادي' },
    },
    errors: {
      corrupt_image: {
        en: 'This file could not be decoded as an image. It may be damaged or incomplete.',
        ar: 'تعذّر فك ترميز هذا الملف كصورة. قد يكون تالفًا أو ناقصًا.',
      },
      not_an_image: {
        en: 'That file is not a recognisable image, even though its extension suggests one.',
        ar: 'هذا الملف ليس صورة قابلة للتعرّف، على الرغم من أن امتداده يشير إلى ذلك.',
      },
      svg_not_supported: {
        en: 'SVG files are not supported. They are vector descriptions that may execute scripts, and they are not analysed as photographs.',
        ar: 'ملفات SVG غير مدعومة. فهي أوصاف متجهية قد تنفّذ سكربتات، ولا تُحلَّل كصور فوتوغرافية.',
      },
      unsupported_format: {
        en: 'That image format is not supported. Use JPEG, PNG or WEBP.',
        ar: 'صيغة الصورة هذه غير مدعومة. استخدم JPEG أو PNG أو WEBP.',
      },
      empty_file: {
        en: 'The selected file is empty.',
        ar: 'الملف المحدد فارغ.',
      },
      file_too_large: {
        en: 'That image is larger than the upload limit. It was not analysed.',
        ar: 'حجم الصورة يتجاوز حد الرفع. لم يتم تحليلها.',
      },
      network_unavailable: {
        en: 'The analysis service could not be reached, so this image was not analysed.',
        ar: 'تعذّر الوصول إلى خدمة التحليل، لذلك لم يتم تحليل هذه الصورة.',
      },
      analysis_failed: {
        en: 'The analysis could not be completed for this image.',
        ar: 'تعذّر إكمال التحليل لهذه الصورة.',
      },
    },
  },

  /* ------------------------------------------------------------------ */
  actions: {
    newInvestigation: { en: 'New investigation', ar: 'تحقيق جديد' },
    reset: { en: 'Reset', ar: 'إعادة تعيين' },
    analyze: { en: 'Analyze', ar: 'حلّل' },
    close: { en: 'Close', ar: 'إغلاق' },
    exampleUrl: { en: 'Load example link', ar: 'حمّل رابطاً تجريبياً' },
  },

  /* ------------------------------------------------------------------ */
  about: {
    title: { en: 'About & methodology', ar: 'عن المنصة والمنهجية' },
    whatTitle: { en: 'What BASIRAH is', ar: 'ما هي بصيرة' },
    whatBody: {
      en: 'BASIRAH is an AI-powered digital trust platform for analysing suspicious images, risky digital content, encoded signals, digital evidence, and suspicious links. You submit one signal — an image, a screenshot, or a link — and the platform investigates it as a whole, correlating synthetic-media, metadata, provenance, domain and identity indicators into a single explainable assessment.',
      ar: 'بصيرة منصة مدعومة بالذكاء الاصطناعي لتحليل الصور المشبوهة والمحتوى الرقمي المريب والإشارات المشفرة والأدلة الرقمية والروابط المشبوهة. ترسل إشارة واحدة — صورة أو لقطة شاشة أو رابط — فيحققق فيها المنصة ككل، وتربط مؤشرات الوسائط المُولَّدة والبيانات الوصفية ومصدر المحتوى والنطاق والهوية في تقييم واحد قابل للتفسير.',
    },
    objectiveTitle: { en: 'Objective', ar: 'الهدف' },
    objectiveBody: {
      en: 'Build an explainable multimodal trust engine for academic research: transparent, probabilistic and auditable, rather than a black-box verdict.',
      ar: 'بناء محرّك ثقة متعدد الوسائط قابل للتفسير لأغراض البحث الأكاديمي: شفاف واحتمالي وقابل للتدقيق، بدلاً من حكم صندوق أسود.',
    },
    orderTitle: { en: 'Why images come first', ar: 'لماذا الصور أولاً' },
    orderBody: {
      en: 'Manipulated media reached people before phishing links did, and it does its damage without a click. Detecting synthetic or altered images is therefore the platform’s primary task; link analysis extends it to the vector people meet later. Both are advisory, both are probabilistic, and neither replaces judgement.',
      ar: 'وصلت الوسائط المُعدَّلة إلى الناس قبل روابط التصيّد، وهي تُحدث ضررها دون نقرة. لذلك فإن كشف الصور المُولَّدة أو المُعدَّلة هو المهمة الأساسية للمنصة، في حين يمتد تحليل الروابط إلى المتجه الذي يلتقونه الناس لاحقاً. كلاهما إرشادي واحتمالي، ولا يحلّ أيٌّ منهما محل الحكم البشري.',
    },
    methodTitle: { en: 'Methodology', ar: 'المنهجية' },
    methodBody: {
      en: 'A submitted image passes through the research-grade synthetic-media candidate, embedded-metadata extraction, forensic characterisation and provenance inspection. Its findings, plus the domain, identity and metadata signals of the submitted content, are correlated into a trust score and an evidence graph. Every stage is recorded in the investigation timeline, and every measurement ships with an explicit statement of what it does not establish.',
      ar: 'تمرّ الصورة المُرسَلة عبر مرشّح بحثي لكشف الوسائط المُولَّدة، ثم استخراج البيانات الوصفية المضمّنة، ثم التوصيف الجنائي، ثم فحص مصدر المحتوى. تُدمج نتائج ذلك مع إشارات النطاق والهوية والبيانات الوصفية في درجة الثقة ورسم الأدلة. وتُسجَّل كل مرحلة في الخط الزمني للتحقيق، ويُرافِق كل قياس بيان صريح لما لا يثبته.',
    },
    limitsTitle: { en: 'What this platform cannot do', ar: 'ما لا تستطيع هذه المنصة فعله' },
    limitsBody: {
      en: 'BASIRAH cannot establish who created a piece of content, cannot prove that an image is authentic, and cannot be used as evidence in a legal proceeding. A low synthetic-media likelihood means no strong indicator was found — not that the content is verified. The image model is a research candidate, not a production-grade detector.',
      ar: 'لا تستطيع بصيرة إثبات من أنشأ محتوى ما، ولا إثبات أن صورة أصلية، ولا تُستخدم كدليل في إجراء قانوني. وانخفاض احتمال الوسائط المُولَّدة يعني عدم وجود مؤشر قوي — لا أن المحتوى موثَّق. ونموذج الصور مرشّح بحثي، لا كاشف جاهز للإنتاج.',
    },
    contextTitle: { en: 'Academic context', ar: 'السياق الأكاديمي' },
    contextBody: {
      en: 'A graduation project in Artificial Intelligence at the University of Bisha. Image intelligence and URL intelligence are both live and both advisory; the remaining modules are on the roadmap and analyse nothing today.',
      ar: 'مشروع تخرج في الذكاء الاصطناعي بجامعة بيشة. ذكاء الصور وذكاء الروابط يعملان وكلاهما إرشادي؛ أما بقية الوحدات فهي في خارطة الطريق ولا تحلّل شيئاً اليوم.',
    },
    membersTitle: { en: 'Project team', ar: 'فريق المشروع' },
    universityLabel: { en: 'Academic institution', ar: 'الجهة الأكاديمية' },
    advisoryNoticeTitle: { en: 'Advisory only', ar: 'إرشادي فقط' },
    advisoryNoticeBody: {
      en: 'Every result in BASIRAH is advisory, probabilistic and explainable. It is designed to inform a decision that a person then makes — never to replace one.',
      ar: 'كل نتيجة في بصيرة استشارية واحتمالية وقابلة للتفسير. صُمّمت لتُغذّي قراراً يتخذه الإنسان، لا لتحلّ محلّه.',
    },
  },

  footer: {
    academicProject: { en: 'Academic graduation project', ar: 'مشروع تخرج أكاديمي' },
    identity: 'BASIRAH',
    explore: { en: 'Explore', ar: 'تصفّح' },
    taglineLabel: { en: 'What it is', ar: 'ما هي' },
  },

  a11y: {
    skipToContent: { en: 'Skip to main content', ar: 'تخطَّ إلى المحتوى' },
  },

  common: {
    mockBadge: { en: 'Mock', ar: 'محاكاة' },
    liveBadge: { en: 'Live analysis', ar: 'تحليل مباشر' },
    yes: { en: 'Yes', ar: 'نعم' },
    no: { en: 'No', ar: 'لا' },
  },
/* ------------------------------------------------------------------ */
  /* Phase 3.7 — four-mode intake                                       */
  /* ------------------------------------------------------------------ */
  mode: {
    image: { en: 'Image', ar: 'صورة' },
    screenshot: { en: 'Screenshot', ar: 'لقطة شاشة' },
    file: { en: 'File', ar: 'ملف' },
    url: { en: 'URL', ar: 'رابط' },
    imageNote: {
      en: 'Ensemble detection, provenance, forensics and fusion.',
      ar: 'كشف بالكواشف، ومصدر المحتوى، وتحليل جنائي، ودمج للأدلة.',
    },
    screenshotNote: {
      en: 'Adds OCR, QR decoding and destination intelligence.',
      ar: 'يضيف التعرّف الضوئي، وفك رموز QR، واستخبارات الوجهة.',
    },
    fileNote: {
      en: 'Text, structure, URLs and encoded content inside the file.',
      ar: 'النص والبنية والروابط والمحتوى المشفّر داخل الملف.',
    },
    urlNote: {
      en: 'Structure, lexical and identity signals. Nothing is fetched.',
      ar: 'بنية الرابط وإشاراته اللفظية والهوية. لا يُجلب أي شيء.',
    },
    label: { en: 'Analysis mode', ar: 'وسيلة التحليل' },
  },

  /* ------------------------------------------------------------------ */
  /* Phase 3.7 — provenance-first result                                */
  /* ------------------------------------------------------------------ */
  result: {
    finalAssessment: { en: 'Final Assessment', ar: 'التقييم النهائي' },
    finalAssessmentSub: {
      en: 'What the evidence fusion concluded, and on what basis.',
      ar: 'ما الذي توصل إليه دمج الأدلة، وعلى أي أساس.',
    },
    assessmentLikelySynthetic: { en: 'Likely Synthetic', ar: 'يُرجّح أنه اصطناعي' },
    assessmentUncertain: { en: 'Uncertain', ar: 'غير مؤكَّد' },
    assessmentNoStrong: {
      en: 'No Strong Synthetic Indicators',
      ar: 'لا توجد مؤشرات اصطناعية قوية',
    },
    assessmentProvenanceVerified: {
      en: 'Verified Generative Provenance',
      ar: 'مصدر توليد موثَّق',
    },
    assessmentProvenanceUnavailable: {
      en: 'Provenance Unavailable',
      ar: 'المصدر غير متاح',
    },
    notMeasured: { en: 'Not measured', ar: 'لم يُقَس' },
    chain: { en: 'Evidence chain', ar: 'سلسلة الأدلة' },
    chainSub: {
      en: 'Each step ran independently. No step’s number is averaged into another’s.',
      ar: 'كل خطوة عملت باستقلال. لا يُدمج رقم خطوة في رقم أخرى.',
    },

    verdict: { en: 'Verdict', ar: 'الحكم' },
    detectorStatus: { en: 'Detector status', ar: 'حالة الكواشف' },
    detectorA: {
      role: { en: 'RESEARCH ADVISORY ONLY', ar: 'إرشادي بحثي فقط' },
      available: { en: 'Available', ar: 'متاح' },
      unavailable: { en: 'Unavailable', ar: 'غير متاح' },
      disagreed: { en: 'Ran but disagreed', ar: 'عمل ولم يتفق' },
    },
    detectorB: {
      role: { en: 'SHADOW — NEVER PROMOTED', ar: 'ظلّ — لا يُحسَّب أبداً' },
      available: { en: 'Available (shadow only)', ar: 'متاح (ظلّ فقط)' },
      unavailable: { en: 'Not available', ar: 'غير متاح' },
      disagreed: { en: 'Ran but disagreed', ar: 'عمل ولم يتفق' },
    },
    univfd: {
      role: { en: 'BENCHMARK CANDIDATE', ar: 'مرشّح معايير' },
      available: { en: 'Available', ar: 'متاح' },
      unavailable: { en: 'Not available', ar: 'غير متاح' },
      disagreed: { en: 'Ran but disagreed', ar: 'عمل ولم يتفق' },
    },
    synthetic: { en: 'Synthetic Evidence', ar: 'الأدلة الاصطناعية' },
    syntheticSub: {
      en: 'Each detector’s own value. These are never averaged into one number.',
      ar: 'قيمة كل كاشف على حدة. لا تُدمج في رقم واحد أبداً.',
    },
    ocr: { en: 'OCR Findings', ar: 'نتائج التعرّف الضوئي' },
    qr: { en: 'QR Findings', ar: 'نتائج رموز الاستجابة السريعة' },
    urls: { en: 'URL Findings', ar: 'نتائج الروابط' },
    encoding: { en: 'Encoded Content', ar: 'المحتوى المشفّر' },
    metadata: { en: 'Metadata', ar: 'البيانات الوصفية' },
    forensics: { en: 'Forensics', ar: 'التحليل الجنائي' },
    limitations: { en: 'Limitations', ar: 'القيود' },
    trustAssessment: { en: 'Digital Trust Assessment', ar: 'تقييم الثقة الرقمية' },
    trustAssessmentSub: {
      en: 'A composite of agreement, quality, familiarity and provenance. It is not a probability that the content is authentic.',
      ar: 'مركّب من التوافق والجودة والمعرفة والمصدر. ليس احتمالاً لأن المحتوى أصلي.',
    },
    components: { en: 'Components', ar: 'المكوّنات' },
    abstain: { en: 'Abstained', ar: 'امتنع' },
    abstained: { en: 'Abstained', ar: 'امتنع' },
    abstentionReasons: { en: 'Abstention reasons', ar: 'أسباب الامتناع' },
    syntheticLikelihood: { en: 'Synthetic likelihood', ar: 'احتمال اصطناعي' },
    perDetector: { en: 'Per detector', ar: 'لكل كاشف' },
    modelName: { en: 'Model', ar: 'النموذج' },
    architecture: { en: 'Architecture', ar: 'البنية' },
    valueLabel: { en: 'Value', ar: 'القيمة' },
    engine: { en: 'Engine', ar: 'المحرك' },
    latency: { en: 'Latency', ar: 'زمن الاستجابة' },
    notes: { en: 'Notes', ar: 'ملاحظات' },
    unavailable: { en: 'Unavailable', ar: 'غير متاح' },
    sectionUnavailable: {
      en: 'This branch did not run for this upload.',
      ar: 'لم يعمل هذا الفرع لهذا الرفع.',
    },
    fusionFindings: { en: 'Fusion findings', ar: 'نتائج الدمج' },
    fusionHierarchy: { en: 'Evidence hierarchy', ar: 'تسلسل قوة الأدلة' },
    tier: { en: 'Tier', ar: 'الدرجة' },
    polarity: { en: 'Polarity', ar: 'الاتجاه' },

    /* ---- Detector conflict ---- */
    conflict: { en: 'DETECTOR CONFLICT', ar: 'تعارض الكاشفين' },
    conflictSub: {
      en: 'The two detectors reached opposite conclusions. The system declined to decide, and published no combined likelihood.',
      ar: 'وصل الكاشفان إلى نتيجتين متعاكستين. رفض النظام الحسم ولم ينشر احتمالاً مجمعاً.',
    },
    decisionAbstained: { en: 'Decision: Abstained', ar: 'القرار: امتناع' },
    conflictNoLikelihood: {
      en: 'No combined likelihood is shown. Averaging a disagreement would present a total conflict as a neutral midpoint.',
      ar: 'لا يُعرض احتمال مجمع. فمتوسط التعارض يقدّم صراعاً تاماً كنقطة وسط محايدة.',
    },

    /* ---- Provenance ---- */
    prov: {
      title: { en: 'Provenance — Content Credentials', ar: 'المصدر — بيانات الاعتماد' },
      sub: {
        en: 'C2PA is a LIMITED module in this platform. It is never labelled verified unless a signature was actually validated.',
        ar: 'معيار C2PA وحدة محدودة في هذه المنصة. لا تُوصف بأنها موثَّقة إلا إذا جرى التحقق من التوقيع فعلاً.',
      },
      moduleLabel: { en: 'C2PA module', ar: 'وحدة C2PA' },
      moduleLimited: { en: 'Limited', ar: 'محدودة' },
      status: { en: 'Status', ar: 'الحالة' },
      standard: { en: 'Standard', ar: 'المعيار' },
      manifest: { en: 'Manifest present', ar: 'البيان موجود' },
      signature: { en: 'Signature verified', ar: 'التوقيع موثَّق' },
      credentialTrust: { en: 'Credential trust', ar: 'ثقة بيانات الاعتماد' },
      signer: { en: 'Signer', ar: 'الموقِّع' },
      issuer: { en: 'Issuer', ar: 'الجهة المُصدِرة' },
      aiGenerated: { en: 'AI generation assertion', ar: 'إقرار التوليد بالذكاء الاصطناعي' },
      aiEdited: { en: 'AI editing assertion', ar: 'إقرار التعديل بالذكاء الاصطناعي' },
      capture: { en: 'Capture assertion', ar: 'إقرار الالتقاط' },
      validationWarnings: { en: 'Validation warnings', ar: 'تحذيرات التحقق' },
      validationErrors: { en: 'Validation errors', ar: 'أخطاء التحقق' },
      noCredentials: {
        en: 'No verifiable Content Credentials were found.',
        ar: 'لم يُعثر على بيانات اعتماد محتوى قابلة للتحقق.',
      },
      absenceNote: {
        en: 'The absence of Content Credentials does not prove that the content is authentic or synthetic.',
        ar: 'غياب بيانات الاعتماد لا يثبت أن المحتوى أصلي أو اصطناعي.',
      },
      statusVerified: { en: 'Verified', ar: 'موثَّق' },
      statusPresentUnverified: { en: 'Present, not verified', ar: 'موجود وغير موثَّق' },
      statusInvalid: { en: 'Present but invalid', ar: 'موجود وغير صالح' },
      statusUnavailable: { en: 'Unavailable', ar: 'غير متاح' },
      evidenceStrength: { en: 'Evidence strength', ar: 'قوة الدليل' },
      asserted: { en: 'Asserted', ar: 'مُقَرَّر' },
      notAsserted: { en: 'Not asserted', ar: 'غير مُقَرَّر' },
    },

    /* ---- Canonical image verdict copy ---- */
    verdictUncertain: {
      en: 'UNCERTAIN',
      ar: 'غير مؤكّد',
    },
    verdictUncertainSecondary: {
      en: 'BASIRAH could not reach a reliable conclusion from the available evidence. The available signals are conflicting, incomplete, or outside the validated distribution.',
      ar: 'لم تتمكن بصيرة من الوصول إلى نتيجة موثّقة من الأدلة المتاحة. فقد تكون الإشارات المتاحة متضاربة أو غير مكتملة أو خارج التوزيع المتحقق.',
    },
    verdictLikelySynthetic: {
      en: 'LIKELY SYNTHETIC',
      ar: 'يُرجّح أنه اصطناعي',
    },
    verdictLikelySyntheticSecondary: {
      en: 'The available evidence contains indicators consistent with AI-generated content. This is an advisory assessment and should be reviewed together with the supporting evidence.',
      ar: 'تحتوي الأدلة المتاحة على مؤشرات مطابقة للمحتوى المُولَّد بالذكاء الاصطناعي. هذا تقييم استشاري يجب مراجعته مع الأدلة الداعمة.',
    },
    verdictNoSynthetic: {
      en: 'NO SYNTHETIC INDICATORS DETECTED',
      ar: 'لم تُرصد مؤشرات اصطناعية',
    },
    verdictNoSyntheticSecondary: {
      en: 'No sufficiently strong synthetic-media indicators were detected. This does not verify authenticity.',
      ar: 'لم يُرد رصد مؤشرات اصطناعية قوية. لا يثبت هذا أصليّة المحتوى.',
    },
    /* ---- Fairness & disclosure ---- */
    detectorAvailable: {
      en: 'Available',
      ar: 'متاح',
    },
    detectorUnavailable: {
      en: 'Unavailable',
      ar: 'غير متاح',
    },
    detectorDisagreed: {
      en: 'Ran but disagreed',
      ar: 'عمل ولم يتفق',
    },
    coverageSub: {
      en: 'Which branches ran for this upload. Anything absent was not measured.',
      ar: 'الفروع التي عملت لهذا الرفع. ما غاب منها لم يُقَس.',
    },
    coverageAvailable: { en: 'Ran', ar: 'عمل' },
    coverageN_A: { en: 'N/A', ar: 'غير مقيّس' },
    coverageUnavailable: { en: 'Unavailable', ar: 'غير متاح' },
    coverageFailed: { en: 'Failed', ar: 'فشل' },
    warnings: { en: 'Warnings', ar: 'تنبيهات' },
    missing: {
      title: { en: 'Missing / Unavailable Evidence', ar: 'أدلة مفقودة أو غير متاحة' },
      subtitle: {
        en: 'Shown when it materially affects interpretation. Absence of evidence is not evidence of absence.',
        ar: 'يعرض عندما يؤثر في التفسير بشكل ملموس. غياب الأدلة ليس دليلاً على غياب الشيء.',
      },
      noProvenance: { en: 'No Content Credentials manifest was found.', ar: 'لم يُعثر على بيان بيانات المنشأ.' },
      ocrUnavailable: { en: 'OCR was not performed.', ar: 'لم يُجر التعرّف الضوئي.' },
      noQr: { en: 'No QR symbol was detected.', ar: 'لم يُعثر على رمز QR.' },
      noUrls: { en: 'No URLs were extracted.', ar: 'لم تُستخرج أي روابط.' },
    },
    facts: {
      title: { en: 'Observed Facts', ar: 'الحقائق المرصودة' },
      subtitle: {
        en: 'What the pipeline actually measured or read off the file.',
        ar: 'ما قاسه خط المعالجة فعلياً أو قرأه من الملف.',
      },
      findingTitle: { en: 'Finding {tier}', ar: 'نتيجة {tier}' },
    },
    inferences: {
      title: { en: 'Model Inferences', ar: 'استنتاجات النماذج' },
      subtitle: {
        en: 'Probabilistic conclusions drawn from those measurements. Neither is proof.',
        ar: 'استنتاجات احتمالية مستخلصة من تلك القياسات. لا شيء منها دليل قاطع.',
      },
      preamble: {
        en: 'These are the models’ own readings, kept separate and never averaged.',
        ar: 'هذه قراءة النماذج ذاتها، حُفظت منفصلة ولم تُجمَع أبداً في رقم واحد.',
      },
      probability: { en: 'Probability', ar: 'الاحتمال' },
    },
    uncertainties: {
      title: { en: 'Uncertainties', ar: 'حالات عدم اليقين' },
      subtitle: {
        en: 'What could not be established. Missing evidence is shown, not hidden.',
        ar: 'ما تعذّر إثباته. حُفظ الأدلة المفقودة، ولم تُخفي.',
      },
      noProvenance: { en: 'No Content Credentials manifest was found.', ar: 'لم يُعثر على بيان بيانات المنشأ.' },
      abstained: { en: 'The detectors abstained.', ar: 'امتنع الكواشف.' },
    },
  },
  agreement: {
    quality: {
      high: { en: 'High', ar: 'عالية' },
      medium: { en: 'Medium', ar: 'متوسطة' },
      low: { en: 'Low', ar: 'منخفضة' },
    },
    distributionStatus: {
      in_distribution: { en: 'In distribution', ar: 'داخل النطاق' },
      borderline: { en: 'Borderline', ar: 'على الحد' },
      out_of_distribution: { en: 'Out of distribution', ar: 'خارج النطاق' },
    },
    ood: {
      warning: {
        en: 'Out-of-distribution content carries less detector weight: the models were not validated on material like this.',
        ar: 'المحتوى خارج النطاق يحمل وزناً أقل للكاشفين: فالنماذج لم تُتحقق على مادة كهذه.',
      },
    },
    coverageYes: { en: 'Ran', ar: 'عمل' },
    coverageNo: { en: 'Did not run', ar: 'لم يعمل' },

    /* ---- Detector agreement & canonical verdict copy ---- */
    whyThisResult: { en: 'Why this result', ar: 'سبب هذا النتيجة' },
    strong: { en: 'Strong agreement', ar: 'اتفاق قوي' },
    moderate: { en: 'Moderate agreement', ar: 'اتفاق متوسط' },
    insufficient: { en: 'Insufficient agreement', ar: 'اتفاق غير كافٍ' },
    conflict: { en: 'Detector conflict', ar: 'تعارض الكاشفين' },
    unavailable: { en: 'Unavailable', ar: 'غير متاح' },

    /* ---- Detector roles & disclosures ---- */
    detectorRole: { en: 'Detector role', ar: 'دور الكاشف' },
    researchAdvisory: { en: 'Research advisory', ar: 'إرشادي بحثي' },
    shadowDiagnosticsOnly: { en: 'Shadow diagnostics only', ar: 'للتشخيص البحثي فقط' },
    doesNotAffectDecision: { en: 'Does not affect the final decision', ar: 'لا يؤثر على التقييم النهائي' },

    /* ---- OCR ---- */
    ocrEngine: { en: 'OCR engine(s)', ar: 'محرك التعرّف' },
    ocrConfidence: { en: 'OCR confidence', ar: 'ثقة التعرّف' },
    ocrText: { en: 'Extracted text', ar: 'النص المستخرج' },
    ocrArabic: { en: 'Arabic detected', ar: 'تم رصد نص عربي' },
    ocrLatin: { en: 'No Arabic detected', ar: 'لم يُرصد نص عربي' },
    ocrArabicLimitation: {
      en: 'Arabic OCR is available but weaker than English, especially on low-contrast or small type. Confidence figures reflect the engine, not the script.',
      ar: 'التعر الضوئي للعربية متاح لكنه أضعف من الإنجليزية، خاصة مع خط صغير أو تباين منخفض. أرقام الثقة تخص المحرك لا اللغة.',
    },
    ocrNoText: { en: 'No text was extracted.', ar: 'لم يُستخرج أي نص.' },

    /* ---- QR ---- */
    qrStatus: { en: 'Decode status', ar: 'حالة فك الترميز' },
    qrPayload: { en: 'Payload', ar: 'المحتوى' },
    qrAttempt: { en: 'Decode attempt', ar: 'محاولة فك الترميز' },
    qrIsUrl: { en: 'Payload is a URL', ar: 'المحتوى رابط' },
    qrNone: { en: 'No QR symbol was found in this content.', ar: 'لم يُعثر على رمز استجابة سريعة في هذا المحتوى.' },

    /* ---- URLs ---- */
    urlCandidate: { en: 'Candidate', ar: 'مرشّح' },
    urlOrigin: { en: 'Found via', ar: 'مصدر الرصد' },
    urlRepaired: { en: 'Repaired', ar: 'أُصلح' },
    urlRisk: { en: 'Risk band', ar: 'فئة الخطورة' },
    urlHighRisk: { en: 'High-Risk Destination', ar: 'وجهة عالية الخطورة' },
    urlTrust: { en: 'URL trust', ar: 'ثقة الرابط' },
    urlNotFetched: {
      en: 'Scored as a string. No URL in this result was fetched, resolved or opened.',
      ar: 'قيّم كنص. لم يُجلب أي رابط في هذه النتيجة ولا حُلّ ولا فُتح.',
    },
    urlUnavailable: { en: 'URL intelligence unavailable', ar: 'استخبارات الروابط غير متاحة' },

    /* ---- Encoding ---- */
    encodingType: { en: 'Encoding', ar: 'الترميز' },
    encodingRaw: { en: 'Raw preview', ar: 'معاينة خام' },
    encodingDecoded: { en: 'Decoded preview', ar: 'معاينة مفكوكة' },
    encodingRisk: { en: 'Risk indicators', ar: 'مؤشرات الخطورة' },
    encodingNone: { en: 'No encoded content was detected.', ar: 'لم يُرصد محتوى مشفّر.' },

    /* ---- File intelligence ---- */
    fileKind: { en: 'File type', ar: 'نوع الملف' },
    fileAccepted: { en: 'File accepted', ar: 'قُبل الملف' },
    fileRefused: { en: 'File refused', ar: 'رُفض الملف' },
    fileRefusedNote: {
      en: 'The file was not analysed. That is not a clean result — it means no measurement was taken.',
      ar: 'لم يُحلَّل الملف. هذه ليست نتيجة نظيفة، بل تعني أنه لم يُؤخذ أي قياس.',
    },
    fileReason: { en: 'Backend reason', ar: 'السبب من المحرك' },
    fileText: { en: 'Extracted text', ar: 'النص المستخرج' },
    fileTextChars: { en: 'Text characters', ar: 'عدد حروف النص' },
    fileUrls: { en: 'Detected URLs', ar: 'الروابط المرصودة' },
    fileEmails: { en: 'Detected emails', ar: 'البريد المرصود' },
    fileIps: { en: 'Detected IPs', ar: 'عناوين IP المرصودة' },
    fileStructure: { en: 'Structure', ar: 'البنية' },
    fileSuspicious: { en: 'Risk findings', ar: 'نتائج الخطورة' },
    fileCoverage: { en: 'Coverage', ar: 'التغطية' },
    fileCoverageText: {
      en: 'File intelligence is active for supported safe text formats. Unsupported formats are refused with a reason and are not analysed.',
      ar: 'ذكاء الملفات نشط لصيغ النص الآمنة المدعومة. أما الصيغ غير المدعومة فتُرفض مع ذكر السبب ولا تُحلَّل.',
    },
    fileNone: { en: 'No file-intelligence block was produced.', ar: 'لم يُنتج كتلة ذكاء ملفات.' },

    /* ---- Metadata / forensics ---- */
    metaFormat: { en: 'Format', ar: 'الصيغة' },
    metaDimensions: { en: 'Dimensions', ar: 'الأبعاد' },
    metaSoftware: { en: 'Software', ar: 'البرنامج' },
    metaCamera: { en: 'Camera', ar: 'الكاميرا' },
    metaExif: { en: 'EXIF data', ar: 'بيانات EXIF' },
    metaGps: { en: 'Location data', ar: 'بيانات الموقع' },
    metaValue: { en: 'Value', ar: 'القيمة' },
    forensicsMeaning: { en: 'What this indicates', ar: 'ما الذي يدل عليه' },
    forensicsNotMean: { en: 'What this does not mean', ar: 'ما لا يعنيه هذا' },
    forensicsNone: { en: 'No forensic characteristics were computed.', ar: 'لم تُحسب أي خصائص جنائية.' },

    /* ---- Risk words ---- */

    suspicious: { en: 'Suspicious Characteristics', ar: 'خصائص مشبوهة' },
  },

  /* ---- Provenance ---- */

  /* ------------------------------------------------------------------ */
  /* Phase 3.7 — screenshot intelligence chain                          */
  /* ------------------------------------------------------------------ */
  chain: {
    title: { en: 'Screenshot Intelligence Chain', ar: 'سلسلة استخبارات لقطة الشاشة' },
    sub: {
      en: 'Each arrow is a real step. Where a step abstained, this page says so rather than borrowing the next step’s conclusion.',
      ar: 'كل سهم خطوة حقيقية. وحين تمتنع خطوة، تذكر الصفحة ذلك بدلاً من استعارة نتيجة الخطوة التالية.',
    },
    stepScreenshot: { en: 'Screenshot', ar: 'لقطة الشاشة' },
    stepOcr: { en: 'OCR', ar: 'التعرّف الضوئي' },
    stepQr: { en: 'QR', ar: 'رمز QR' },
    stepUrlExtract: { en: 'URL Extraction', ar: 'استخراج الروابط' },
    stepUrlIntel: { en: 'URL Intelligence', ar: 'استخبارات الروابط' },
    stepFusion: { en: 'Evidence Fusion', ar: 'دمج الأدلة' },
    independentLines: { en: 'Independent findings', ar: 'نتائج مستقلة' },
    independentLinesSub: {
      en: 'These disagree by design and are reported that way. Reconciling them here would hide the disagreement the committee needs.',
      ar: 'هذه النتائج تختلف عن قصدها وتُعرض هكذا. تسويتها هنا يحجب التعارض الذي يحتاجه اللجنة.',
    },
    imageDetectors: { en: 'Image detectors', ar: 'كاشفا الصور' },
    urlEvidence: { en: 'URL evidence', ar: 'دليل الروابط' },
    finalAssessmentLine: { en: 'Final assessment', ar: 'التقييم النهائي' },
  },

  /* ------------------------------------------------------------------ */
  /* Phase 3.7 — Challenge / internal defence mode                     */
  /* ------------------------------------------------------------------ */
  challenge: {
    nav: { en: 'Challenge', ar: 'التحدي' },
    title: { en: 'Challenge — Internal Defence Mode', ar: 'التحدي — وضع الدفاع الداخلي' },
    sub: {
      en: 'A working surface for adversarial testing. It uses the same live pipeline as the public Analyze section and adds a ground-truth comparison that stays hidden until it is explicitly revealed.',
      ar: 'سطح عمل للاختبار العدائي. يستخدم خط المعالجة الحي نفسه في قسم التحليل العام، ويضيف مقارنة بالحقيقة الأرضية تبقى مخفية حتى يُطلب كشفها صراحةً.',
    },
    input: { en: 'Input', ar: 'المُدخل' },
    inputSub: {
      en: 'Upload a prepared fixture to compare a known ground truth against the live pipeline.',
      ar: 'ارفع عينة مُجهَّزة لمقارنة حقيقة أرضية معروفة بخط المعالجة الحي.',
    },
    uploadFixture: { en: 'Upload fixture', ar: 'ارفع عينة' },
    runAnalysis: { en: 'Run analysis', ar: 'شغّل التحليل' },
    groundTruth: { en: 'Ground Truth (Hidden)', ar: 'الحقيقة الأرضية (مخفية)' },
    groundTruthHidden: {
      en: 'Ground truth is hidden.',
      ar: 'الحقيقة الأرضية مخفية.',
    },
    groundTruthLocked: {
      en: 'Ground truth is withheld. Reveal it only after the pipeline has run, so the comparison means something.',
      ar: 'الحقيقة الأرضية محجوزة. اكشفها بعد تشغيل الخط فقط، حتى تكون المقارنة ذات معنى.',
    },
    revealTruth: { en: 'Reveal Ground Truth', ar: 'اكشف الحقيقة الأرضية' },
    hideTruth: { en: 'Hide Ground Truth', ar: 'أخفِ الحقيقة الأرضية' },
    truthRevealed: { en: 'Ground truth revealed', ar: 'تم كشف الحقيقة الأرضية' },
    truthAgreement: { en: 'Pipeline vs ground truth', ar: 'خط المعالجة مقابل الحقيقة الأرضية' },
    truthMatches: { en: 'Agrees with ground truth', ar: 'يطابق الحقيقة الأرضية' },
    truthDiffers: { en: 'Differs from ground truth', ar: 'يختلف عن الحقيقة الأرضية' },
    sectionInput: { en: 'Input', ar: 'المُدخل' },
    sectionDetectorA: { en: 'Detector A', ar: 'الكاشف أ' },
    sectionDetectorB: { en: 'Detector B', ar: 'الكاشف ب' },
    sectionAgreement: { en: 'Agreement', ar: 'التوافق' },
    sectionOod: { en: 'OOD', ar: 'خارج النطاق' },
    sectionQuality: { en: 'Evidence Quality', ar: 'جودة الأدلة' },
    sectionProvenance: { en: 'Provenance', ar: 'المصدر' },
    sectionOcr: { en: 'OCR', ar: 'التعرّف الضوئي' },
    sectionQr: { en: 'QR', ar: 'رمز QR' },
    sectionUrls: { en: 'URLs', ar: 'الروابط' },
    sectionEncoding: { en: 'Encoding', ar: 'الترميز' },
    sectionMetadata: { en: 'Metadata', ar: 'البيانات الوصفية' },
    sectionForensics: { en: 'Forensics', ar: 'التحليل الجنائي' },
    sectionFusion: { en: 'Final Fusion', ar: 'الدمج النهائي' },
    sectionTrust: { en: 'Trust Assessment', ar: 'تقييم الثقة' },
    awaitingRun: {
      en: 'No fixture analysed yet. Upload a prepared fixture and run the analysis.',
      ar: 'لم تُحلَّل أي عينة بعد. ارفع عينة مُجهَّزة وشغّل التحليل.',
    },

    /* ---- Blind test panel ---- */
    blindTitle: { en: 'Blind Defence Test', ar: 'اختبار الدفاع الأعمى' },
    blindSub: {
      en: 'Measured results from the project’s own held-out evaluation. These are the only accuracy figures BASIRAH has.',
      ar: 'نتائج مقاسة من التقييم المحجوز الخاص بالمشروع. هذه هي نسب الدقة الوحيدة المتاحة في بصيرة.',
    },
    blindSampleCount: { en: 'Samples', ar: 'العينة' },
    blindFalseAuthentic: { en: 'False authentic rate', ar: 'نسبة «أصلية» الخاطئة' },
    blindDetectorA: { en: 'Detector A false authentic', ar: 'كاشف أ: «أصلية» خاطئة' },
    blindDetectorB: { en: 'Detector B false authentic', ar: 'كاشف ب: «أصلية» خاطئة' },
    blindDisagreements: { en: 'Detector disagreements', ar: 'تعارضات الكاشفين' },
    blindAbstention: { en: 'Abstention rate', ar: 'نسبة الامتناع' },
    blindOod: { en: 'Out-of-distribution', ar: 'خارج النطاق' },
    blindLatency: { en: 'Mean latency', ar: 'متوسط زمن الاستجابة' },
    blindNote: {
      en: 'This evaluation is a controlled defense set and does not represent universal real-world accuracy.',
      ar: 'هذا التقييم مجموعة دفاع مضبوطة ولا يمثل دقة حقيقية شاملة.',
    },
    blindLimitations: { en: 'Limitations of this evaluation', ar: 'قيود هذا التقييم' },
    blindLimitSmall: {
      en: 'Small sample size: 51 images is far too few to estimate real-world accuracy.',
      ar: 'حجم عينة صغير: 51 صورة لا تكفي لتقدير الدقة في العالم الحقيقي.',
    },
    blindLimitGenerators: {
      en: 'Most synthetic images come from CommunityForensics, whose generator family is unknown, so per-family performance cannot be stated.',
      ar: 'معظم الصور الاصطناعية من CommunityForensics وعائلة مولّداتها غير معروفة، فلا يمكن ذكر أداء لكل عائلة.',
    },
    blindLimitReal: {
      en: 'The real class is Flickr30k, a captioning dataset — not a distribution of real-world forensic captures.',
      ar: 'الفئة الحقيقية هي Flickr30k، وهي مجموعة وصف صور، لا توزيع لالتقاطات جنائية حقيقية.',
    },
    blindLimitNotValidation: {
      en: 'This is not independent real-world deployment validation.',
      ar: 'هذا ليس تحقّقاً مستقلاً من النشر في العالم الحقيقي.',
    },
  },

  /* ------------------------------------------------------------------ */
  /* Phase 3.7 — report fact / inference separation                     */
  /* ------------------------------------------------------------------ */
  reportSections: {
    verifiedFacts: { en: 'VERIFIED FACTS', ar: 'حقائق متحقَّق منها' },
    verifiedFactsSub: {
      en: 'Measurements and observations. These are what the pipeline read.',
      ar: 'قياسات ومشاهدات. هذا ما قرأه خط المعالجة.',
    },
    modelInferences: { en: 'MODEL INFERENCES', ar: 'استنتاجات النموذج' },
    modelInferencesSub: {
      en: 'Probabilistic conclusions drawn from those measurements. Neither is proof.',
      ar: 'استنتاجات احتمالية مستخلصة من تلك القياسات. لا شيء منها دليل قاطع.',
    },
    heuristicSignals: { en: 'HEURISTIC SIGNALS', ar: 'إشارات استدلالية' },
    heuristicSignalsSub: {
      en: 'Weak, structural indicators that support but never decide.',
      ar: 'مؤشرات بنيوية ضعيفة تسند لكنها لا تحسم أبداً.',
    },
    unavailableEvidence: { en: 'UNAVAILABLE EVIDENCE', ar: 'أدلة غير متاحة' },
    unavailableEvidenceSub: {
      en: 'What could not be established, and why its absence proves nothing.',
      ar: 'ما تعذّر إثباته، ولماذا غيابها لا يثبت شيئاً.',
    },
    limitationsSection: { en: 'LIMITATIONS', ar: 'القيود' },
    fusionExplanation: { en: 'How the fusion decided', ar: 'كيف حسم الدمج' },
    empty: { en: 'Nothing was recorded in this category.', ar: 'لم يُسجَّل شيء في هذه الفئة.' },
  },
} as const
export type TranslationTree = typeof translations
export type Language = 'en' | 'ar'
export type Direction = 'ltr' | 'rtl'

/** A bilingual leaf value. */
export type Bilingual = { en: string; ar: string };

/** Dotted-path key resolution: 'journey.stages.acquire' -> that leaf.
 *  Accepts both leaf keys and dotted paths into the tree. */
export type TranslationKey = string;

/**
 * Type-safe dotted-key resolver: given a key, returns the leaf value.
 * Falls back to the key itself if the path does not exist.
 */
export function resolveTranslationKey<T>(tree: T, key: string): unknown {
  return key.split('.').reduce<unknown>((node, part) => {
    if (node && typeof node === 'object') {
      return (node as Record<string, unknown>)[part];
    }
    return undefined;
  }, tree);
}

