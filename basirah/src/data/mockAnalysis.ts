import type {
  AnalysisResult,
  DnaAxis,
  RiskLevel,
  SignalKind,
  TrustDna,
} from '../types/analysis'

/* ============================================================
   Simulated intelligence payloads.

   IMPORTANT: nothing in this file is real threat intelligence.
   Every value below is hand-authored to demonstrate the interface
   and the fusion model. `isMock: true` and `source: 'mock'` flow
   all the way to the UI, which renders a persistent badge so the
   demonstration is never mistaken for a live assessment.
   ============================================================ */

export const MOCK_ENGINE = 'basirah-fusion-sim'
export const MOCK_ENGINE_VERSION = '0.1.0-sim'

/** The canonical demo signal from the Phase 1 brief. */
export const EXAMPLE_URL = 'https://nafath-secure-login.example'

/** Palette values, kept here so DNA colouring stays consistent. */
export const RISK_COLORS: Record<RiskLevel, string> = {
  trusted: 'var(--color-trusted)',
  caution: 'var(--color-caution)',
  high_risk: 'var(--color-danger)',
}

export const DNA_AXES: DnaAxis[] = [
  'synthetic',
  'identity',
  'domain',
  'provenance',
  'behavior',
]

/* ------------------------------------------------------------------ */
/* URL intelligence — impersonation pattern                             */
/* ------------------------------------------------------------------ */

const urlImpersonationResult: AnalysisResult = {
  lanes: ['url_intelligence', 'identity', 'metadata', 'provenance', 'fusion'],
  durationMs: 2100,
  isMock: true,
  source: 'mock',
  engine: MOCK_ENGINE,
  engineVersion: MOCK_ENGINE_VERSION,
  signal: {
    kind: 'url',
    valueEn: EXAMPLE_URL,
    valueAr: EXAMPLE_URL,
  },
  trustScore: 21,
  finalAssessment: 'uncertain',
  riskLevel: 'high_risk',
  confidence: 89,
  dna: {
    synthetic: 72,
    identity: 21,
    domain: 91,
    provenance: 30,
    behavior: 83,
  },
  graph: {
    nodes: [
      {
        id: 'claimed-brand',
        labelEn: 'Claimed brand',
        labelAr: 'العلامة المُعلَنة',
        detailEn: 'The hostname reported by the analyser matches a registered organisation brand.',
        detailAr: 'عنوان المضيف الذي أبلغ عنه المُحلِّل يتطابق مع علامة تجارية منظمة مسجَّلة.',
        weight: 'primary',
        polarity: 'neutral',
        x: 50,
        y: 13,
      },
      {
        id: 'identity-match',
        labelEn: 'Identity match',
        labelAr: 'تطابق الهوية',
        detailEn: 'Claimed organisation matches the registered domain holder.',
        detailAr: 'الجهة المُعلَنة تطابق مالك النطاق المسجَّل.',
        weight: 'primary',
        polarity: 'trust',
        x: 50,
        y: 62,
      },
      {
        id: 'trust-signal',
        labelEn: 'Trust signal',
        labelAr: 'إشارة ثقة',
        detailEn: 'No high-risk indicators identified on available evidence.',
        detailAr: 'لم تُرصد مؤشرات خطورة عالية على الأدلة المتاحة.',
        weight: 'primary',
        polarity: 'trust',
        x: 88,
        y: 87,
      },
    ],
    edges: [
      { from: 'url-signal', to: 'domain-age', relation: 'derives' },
      { from: 'url-signal', to: 'valid-cert', relation: 'derives' },
      { from: 'domain-age', to: 'identity-match', relation: 'asserts' },
      { from: 'valid-cert', to: 'identity-match', relation: 'asserts' },
      { from: 'identity-match', to: 'trust-signal', relation: 'derives' },
    ],
  },
  timeline: [
    { id: 't1', stage: 'acquire', offsetSeconds: 0 },
    { id: 't2', stage: 'acquire', offsetSeconds: 0.4 },
    { id: 't3', stage: 'identify', offsetSeconds: 0.9 },
    { id: 't4', stage: 'provenance', offsetSeconds: 1.6 },
    { id: 't5', stage: 'score', offsetSeconds: 2.1 },
  ],
  primarySignal: {
    titleEn: 'Elevated impersonation risk',
    titleAr: 'ارتفاع خطر التزيُّف',
    bodyEn:
      'The analyser reports lexical similarity to a registered brand, a mismatch between the displayed domain and the link target, and no cryptographic provenance. The combination is consistent with credential-phishing content.',
    bodyAr:
      'أبلغ المُحلِّل عن تشابه لفظي مع علامة تجارية مسجَّلة، وجود اختلاف بين النطاق المُظهَر والوجهة المُوجَبة، وعدم وجود بيانات منشأ تشفيري. التجميع متوافق مع محتوى خداعcredential.',
  },
  secondarySignals: [
    {
      id: 's1',
      metricKey: 'explanation.metrics.brandMatch',
      valueEn: 'Partial',
      valueAr: 'جزئي',
      severity: 'caution',
    },
    {
      id: 's2',
      metricKey: 'explanation.metrics.registryFreshness',
      valueEn: 'Recent',
      valueAr: 'حديث',
      severity: 'caution',
    },
  ],
}

/* ------------------------------------------------------------------ */
/* Image intelligence — known AI image                                  */
/* ------------------------------------------------------------------ */

const syntheticImageResult: AnalysisResult = {
  lanes: ['synthetic_media', 'metadata', 'provenance', 'identity', 'fusion'],
  durationMs: 3620,
  isMock: true,
  source: 'mock',
  engine: MOCK_ENGINE,
  engineVersion: MOCK_ENGINE_VERSION,
  signal: {
    kind: 'image',
    valueEn: 'signal-sample-01.png',
    valueAr: 'إشارة-عيّنة-01.png',
  },
  trustScore: 44,
  finalAssessment: 'uncertain',
  riskLevel: 'caution',
  confidence: 74,
  dna: {
    synthetic: 88,
    identity: 58,
    domain: 12,
    provenance: 41,
    behavior: 37,
  },
  graph: {
    nodes: [
      {
        id: 'image-signal',
        labelEn: 'Image signal',
        labelAr: 'إشارة الصورة',
        detailEn: 'Pre-scoring metadata and rendered-tone analysis for the uploaded image.',
        detailAr: 'بيانات معرفية قبل التصنيف وتحليل تدرج الألوان للصورة المرفقة.',
        weight: 'primary',
        polarity: 'neutral',
        x: 50,
        y: 13,
      },
      {
        id: 'synthetic-ind',
        labelEn: 'Synthetic indicators',
        labelAr: 'مؤشرات التوليد',
        detailEn: 'Intentional compression anomalies and frequency-domain deviation from camera noise.',
        detailAr: 'شذوذ إحصائي في الضغط والانحراف في المجال الترددي عن ضوضاء الكاميرا.',
        weight: 'primary',
        polarity: 'risk',
        x: 12,
        y: 44,
      },
      {
        id: 'metadata-gap',
        labelEn: 'Metadata gap',
        labelAr: 'ثغرة البيانات الوصفية',
        detailEn: 'No capture source, no software chain, no maker metadata.',
        detailAr: 'لا يوجد مُصدر التقاط ولا سلسلة البرمجيات ولا بيانات صنع.',
        weight: 'secondary',
        polarity: 'neutral',
        x: 50,
        y: 87,
      },
      {
        id: 'caution-signal',
        labelEn: 'Caution signal',
        labelAr: 'إشارة تحذير',
        detailEn: 'Consistent with AI generation but too weak to classify.',
        detailAr: 'متوافق مع التوليد الاصطناعي ولكنه محدود للاستنتاج.',
        weight: 'secondary',
        polarity: 'risk',
        x: 88,
        y: 76,
      },
      {
        id: 'entity-unverified',
        labelEn: 'Entity unverified',
        labelAr: 'مُصطلح غير مؤكَّد',
        detailEn: 'Synthetic-specific entities are present but not verified.',
        detailAr: 'مُصطلحات محدَّثة موجودة لكنها لم تُؤكَّد.',
        weight: 'secondary',
        polarity: 'neutral',
        x: 27,
        y: 87,
      },
      {
        id: 'provenance-unverified',
        labelEn: 'Provenance unverified',
        labelAr: 'المنشأ غير مؤكَّد',
        detailEn: 'No C2PA manifest available.',
        detailAr: 'لا يتوفر ملف م manifest C2PA.',
        weight: 'secondary',
        polarity: 'neutral',
        x: 88,
        y: 12,
      },
    ],
    edges: [
      { from: 'image-signal', to: 'synthetic-ind', relation: 'derives' },
      { from: 'image-signal', to: 'metadata-gap', relation: 'derives' },
      { from: 'synthetic-ind', to: 'caution-signal', relation: 'derives' },
      { from: 'metadata-gap', to: 'caution-signal', relation: 'derives' },
      { from: 'entity-unverified', to: 'caution-signal', relation: 'derives' },
      { from: 'provenance-unverified', to: 'caution-signal', relation: 'derives' },
    ],
  },
  timeline: [
    { id: 't1', stage: 'acquire', offsetSeconds: 0 },
    { id: 't2', stage: 'acquire', offsetSeconds: 0.3 },
    { id: 't3', stage: 'visual', offsetSeconds: 1.0 },
    { id: 't4', stage: 'metadata', offsetSeconds: 1.6 },
    { id: 't5', stage: 'synthetic', offsetSeconds: 2.3 },
    { id: 't6', stage: 'provenance', offsetSeconds: 2.8 },
    { id: 't7', stage: 'correlate', offsetSeconds: 3.2 },
    { id: 't8', stage: 'score', offsetSeconds: 3.6 },
  ],
  primarySignal: {
    titleEn: 'Elevated synthetic-media indicators',
    titleAr: 'ارتفاع مؤشرات الوسائط المُولَّدة',
    bodyEn:
      'Texture statistics in the submitted image deviate from expected camera output, and the file carries no capture provenance. On simulated evidence this is consistent with generated or heavily processed media.',
    bodyAr:
      'إحصائيات النسيج في الصورة المُرسلة تنحرف عن مخرجات الكاميرا المتوقعة، ولا يحمل الملف أي مصدر التقاط. على الأدلة المحاكاة يتّسق ذلك مع وسائط مُولَّدة أو مُعالَجة بشدة.',
  },
  secondarySignals: [
    {
      id: 's1',
      metricKey: 'explanation.metrics.syntheticConfidence',
      valueEn: '88%',
      valueAr: '٨٨٪',
      severity: 'caution',
    },
    {
      id: 's2',
      metricKey: 'explanation.metrics.provenance',
      valueEn: 'Unavailable',
      valueAr: 'غير متاح',
      severity: 'caution',
    },
    {
      id: 's3',
      metricKey: 'explanation.metrics.brandMatch',
      valueEn: 'Partial',
      valueAr: 'جزئي',
      severity: 'neutral',
    },
  ],
}

/* ------------------------------------------------------------------ */
/* URL intelligence — benign reference case                             */
/* ------------------------------------------------------------------ */

const trustedUrlResult: AnalysisResult = {
  lanes: ['url_intelligence', 'identity', 'metadata', 'provenance', 'fusion'],
  durationMs: 1850,
  isMock: true,
  source: 'mock',
  engine: MOCK_ENGINE,
  engineVersion: MOCK_ENGINE_VERSION,
  signal: {
    kind: 'url',
    valueEn: 'https://www.university.edu.sa',
    valueAr: 'https://www.university.edu.sa',
  },
  trustScore: 88,
  finalAssessment: 'uncertain',
  riskLevel: 'trusted',
  confidence: 82,
  dna: {
    synthetic: 14,
    identity: 86,
    domain: 22,
    provenance: 79,
    behavior: 18,
  },
  graph: {
    nodes: [
      {
        id: 'url-signal',
        labelEn: 'URL signal',
        labelAr: 'إشارة الرابط',
        detailEn: 'Lexical and structural properties of the submitted URL.',
        detailAr: 'الخصائص اللغوية والبنيوية للرابط المُرسَل.',
        weight: 'primary',
        polarity: 'neutral',
        x: 50,
        y: 13,
      },
      {
        id: 'domain-age',
        labelEn: 'Domain age',
        labelAr: 'عمر النطاق',
        detailEn: 'Registered within the tracked window and not newly spun.',
        detailAr: 'مسجَّل dentro da janela rastreável e não recém-criado.',
        weight: 'primary',
        polarity: 'neutral',
        x: 50,
        y: 44,
      },
      {
        id: 'valid-cert',
        labelEn: 'Valid certificate',
        labelAr: 'شهادة صالحة',
        detailEn: 'Cryptographic identity is consistent with the displayed domain.',
        detailAr: 'الهوية التشفيرية متوافقة مع النطاق المُظهَر.',
        weight: 'primary',
        polarity: 'trust',
        x: 50,
        y: 76,
      },
      {
        id: 'identity-match',
        labelEn: 'Identity match',
        labelAr: 'تطابق الهوية',
        detailEn: 'Claimed organisation matches the registered domain holder.',
        detailAr: 'الجهة المُعلَنة تطابق مالك النطاق المسجَّل.',
        weight: 'primary',
        polarity: 'trust',
        x: 50,
        y: 87,
      },
      {
        id: 'trust-signal',
        labelEn: 'Trust signal',
        labelAr: 'إشارة ثقة',
        detailEn: 'No high-risk indicators identified on available evidence.',
        detailAr: 'لم تُرصد مؤشرات خطورة عالية على الأدلة المتاحة.',
        weight: 'primary',
        polarity: 'trust',
        x: 88,
        y: 87,
      },
    ],
    edges: [
      { from: 'url-signal', to: 'domain-age', relation: 'derives' },
      { from: 'url-signal', to: 'valid-cert', relation: 'derives' },
      { from: 'domain-age', to: 'identity-match', relation: 'asserts' },
      { from: 'valid-cert', to: 'identity-match', relation: 'asserts' },
      { from: 'identity-match', to: 'trust-signal', relation: 'derives' },
    ],
  },
  timeline: [
    { id: 't1', stage: 'acquire', offsetSeconds: 0 },
    { id: 't2', stage: 'acquire', offsetSeconds: 0.4 },
    { id: 't3', stage: 'identify', offsetSeconds: 0.9 },
    { id: 't4', stage: 'correlate', offsetSeconds: 1.4 },
    { id: 't5', stage: 'score', offsetSeconds: 1.9 },
  ],
  primarySignal: {
    titleEn: 'No high-risk indicators identified',
    titleAr: 'لم تُرصد مؤشرات خطورة عالية',
    bodyEn:
      'The analyser reports reasonable lexicon, a registered domain, and an available certificate. These are positive signals but are not sufficient to assert verified authenticity.',
    bodyAr:
      'أبلغ المُحلِّل عن قاموس معيَّن، ونطاق مسجَّل، وشهادة متاحة. هذه إشارات إيجابية لكنها غير كافية للاستنتاج.',
  },
  secondarySignals: [
    {
      id: 's1',
      metricKey: 'explanation.metrics.domainLexicon',
      valueEn: 'Familiar',
      valueAr: 'مألوف',
      severity: 'trusted',
    },
    {
      id: 's2',
      metricKey: 'explanation.metrics.registryFreshness',
      valueEn: 'Within window',
      valueAr: 'داخل النافذة',
      severity: 'trusted',
    },
  ],
}

/* Public surface                                                      */

/**
 * Resolve a simulated payload for a signal type.
 *
 * This is the ONLY place the UI reaches for mock data. Replacing this
 * with `fetch('/api/analyze')` in Phase 6 requires no component change,
 * because the return type is already the AnalysisResult contract.
 */
export function getMockResult(kind: SignalKind): AnalysisResult {
  switch (kind) {
    case 'image':
    case 'screenshot':
    case 'qr':
      return syntheticImageResult
    case 'url':
    case 'text':
    default:
      // Demo UX: an unfamiliar URL is treated as the impersonation case so
      // the high-risk path is always demonstrable.
      return urlImpersonationResult
  }
}

/** Alternate payloads for the "example signal" affordances. */
export const MOCK_EXAMPLES = {
  impersonationUrl: urlImpersonationResult,
  syntheticImage: syntheticImageResult,
  trustedUrl: trustedUrlResult,
} satisfies Record<string, AnalysisResult>

export type MockExampleKey = keyof typeof MOCK_EXAMPLES

/** DNA colour per risk band, used by the Trust DNA renderer. */
export function dnaColorForValue(value: number): string {
  if (value >= 75) return RISK_COLORS.high_risk
  if (value >= 50) return RISK_COLORS.caution
  return RISK_COLORS.trusted
}

export const MOCK_DNA: TrustDna = urlImpersonationResult.dna
