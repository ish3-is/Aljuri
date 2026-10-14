import type {
  DetectorAgreement,
  EvidenceAnalysisResult,
  EvidenceProvenance,
  RiskLevel,
  TrustDna,
} from '../../types/analysis'

/* ============================================================
   STATIC SHOWCASE FIXTURE — sample analysis result
   Used ONLY in VITE_APP_MODE=showcase. Never served from a live
   backend, never presented as live inference.
   ============================================================ */

export const SHOWCASE_FINGERPRINT = 'static-showcase-demo'

/** The sample signal that the fixture represents. */
export const SHOWCASE_SIGNAL_LABEL = 'https://nafath-secure-login.example'

/** The final assessment vocabulary the UI forces. */
export const SAMPLE_ASSESSMENT = 'uncertain'

/** Conservative values per the demo-data policy. */
export const SAMPLE_RISK: RiskLevel = 'caution'

export const SAMPLE_COVERAGE = 'partial'

export const SAMPLE_AGREEMENT: DetectorAgreement = 'conflict'

export const SAMPLE_PROVENANCE: EvidenceProvenance = {
  status: 'unavailable',
  standard: null,
  manifestPresent: false,
  signatureVerified: null,
  signer: null,
  issuer: null,
  aiGeneratedAssertion: null,
  aiEditedAssertion: null,
  captureAssertion: null,
  validationWarnings: [],
  validationErrors: [],
  evidenceStrength: 'none',
  sdkAvailable: false,
  notes: ['limited/invalid-example'],
}

export const SAMPLE_DNA: TrustDna = {
  synthetic: 0.32,
  identity: 0.61,
  domain: 0.44,
  provenance: 0.1,
  behavior: 0.29,
}

/** Static showcase fixture matching the evidence analysis payload. */
export const SHOWCASE_RESULT: EvidenceAnalysisResult = {
  analysisSource: 'evidence',
  lanes: ['url_intelligence', 'identity', 'metadata', 'provenance', 'fusion'],
  durationMs: 2100,
  isMock: true,
  source: 'mock',
  engine: 'basirah-fusion-sim',
  engineVersion: '0.1.0-sim',
  signal: {
    kind: 'url',
    valueEn: SHOWCASE_SIGNAL_LABEL,
    valueAr: 'https://nafath-secure-login.example',
  },
  trustScore: 52,
  riskLevel: SAMPLE_RISK,
  confidence: null,
  dna: SAMPLE_DNA,
  graph: {
    nodes: [],
    edges: [],
  },
  timeline: [],
  finalAssessment: SAMPLE_ASSESSMENT,
  ensemble: {
    detectors: [],
    detectorAgreement: SAMPLE_AGREEMENT,
    evidenceQuality: 'low',
    distributionStatus: 'out_of_distribution',
    syntheticLikelihood: null,
    abstained: true,
    abstentionReasons: ['demo/static fixture'],
    notes: ['static showcase fixture — no detectors run'],
    latencyMs: {},
  },
  distributionStatus: undefined,
  detectorAgreement: SAMPLE_AGREEMENT,
  primarySignal: {
    titleEn: 'Domain impersonation pattern',
    titleAr: 'نمط التقشم في المجال',
    bodyEn: 'The domain impersonates a well-known login portal to harvest credentials.',
    bodyAr: 'يقلد المجال منصة تسجيل دخول معروفة لسرقة بيانات الاعتماد.',
  },
  secondarySignals: [],
  imageDetail: undefined,
  evidence: {
    analysisType: 'evidence',
    mode: 'url',
    fileName: 'sample-analysis.example',
    fileSizeBytes: 1024,
    finalAssessment: null,
    provenance: SAMPLE_PROVENANCE,
    ensemble: null,
    trustAssessment: null,
    metadata: null,
    forensics: null,
    evidenceQuality: null,
    ocr: null,
    qr: null,
    urls: [],
    file: null,
    encoding: [],
    fusion: {
      finalAssessment: SAMPLE_ASSESSMENT,
      findings: [],
      evidenceHierarchy: [],
      limitations: ['static showcase fixture — no fusion performed'],
      note: 'demo/sample result, not live inference',
    },
    timeline: [],
    latencyMs: {},
    limitations: [
      'DEMO — sample analysis result (static, not live).',
      'Live analysis requires the local BASIRAH backend.',
    ],
    fingerprint: SHOWCASE_FINGERPRINT,
    coverage: {
      imagePixels: 0,
      provenance: 'none',
      ocr: 'none',
      qr: 'none',
      url: 'not-executed',
      encoding: 'none',
      fileStructure: 'none',
    },
    reportTraceability: [],
  },
}
