import type {
  AnalysisResult,
  DnaAxis,
  ImageAssessment,
  RiskLevel,
} from '../../types/analysis'
import { projectMembers } from '../../data/projectMembers'
import {
  buildEvidenceClaims,
  fusionExplanation,
  reportLimitations,
} from './evidenceReportMapper'
import type {
  ReportDocument,
  ReportEvidenceItem,
  ReportModality,
  ReportUrlSignalRow,
} from '../../types/report'

/* ============================================================
   ANALYSIS RESULT -> REPORT DOCUMENT

   One mapper per modality family, all producing the same
   modality-neutral `ReportDocument`. A Phase 4 modality adds a
   mapper here and nothing else: the report layout, the print
   stylesheet and the Excel workbook all read the neutral shape.

   Two invariants this file must not break:

     1. NOTHING IS INVENTED. Every value is read from the analysis
        result the backend actually returned. Where a modality
        cannot measure something, the array is left empty and the
        report says "not measured". No placeholder zeros, no
        "N/A" strings masquerading as measurements.
     2. BILINGUAL BY CONSTRUCTION. Every row carries both
        languages, because the report must render in Arabic as a
        first-class document and not as a translated afterthought.
   ============================================================ */

/** Map a signal kind onto the report's modality vocabulary. */
export function toReportModality(kind: AnalysisResult['signal']['kind']): ReportModality {
  switch (kind) {
    case 'image':
      return 'image'
    case 'screenshot':
      return 'screenshot'
    case 'qr':
      return 'qr'
    case 'url':
      return 'url'
    case 'text':
      return 'text'
    case 'file':
      return 'file'
  }
}

/** Short uppercase tag used in the report id: BASIRAH-<TAG>-<date>-<rand>. */
const MODALITY_TAG: Record<ReportModality, string> = {
  image: 'IMG',
  screenshot: 'SHOT',
  qr: 'QR',
  url: 'URL',
  text: 'TXT',
  file: 'FILE',
}

/**
 * Local report identifier.
 *
 * The suffix is random, NOT a hash of the content and NOT a
 * signature: this identifier makes one document referable, and
 * nothing more. The report states that explicitly so it can never be
 * mistaken for cryptographic provenance.
 */
export function makeReportId(modality: ReportModality, when: Date): string {
  const y = when.getFullYear()
  const m = String(when.getMonth() + 1).padStart(2, '0')
  const d = String(when.getDate()).padStart(2, '0')
  // crypto.getRandomValues is available in every browser context the
  // app supports, and Math.random would make collisions more likely.
  const bytes = new Uint8Array(2)
  crypto.getRandomValues(bytes)
  const suffix = Array.from(bytes)
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('')
    .toUpperCase()
  return `BASIRAH-${MODALITY_TAG[modality]}-${y}${m}${d}-${suffix}`
}

const ASSESSMENT_EN: Record<ImageAssessment, string> = {
  likely_authentic: 'Likely authentic',
  uncertain: 'Uncertain',
  likely_synthetic: 'Likely synthetic',
}

const ASSESSMENT_AR: Record<ImageAssessment, string> = {
  likely_authentic: 'يُرجّح أنها أصلية',
  uncertain: 'غير مؤكَّد',
  likely_synthetic: 'يُرجّح أنها اصطناعية',
}

const DNA_LABEL_KEYS = {
  synthetic: 'dna.axes.synthetic',
  identity: 'dna.axes.identity',
  domain: 'dna.axes.domain',
  provenance: 'dna.axes.provenance',
  behavior: 'dna.axes.behavior',
} as const

const AXIS_ORDER: DnaAxis[] = [
  'synthetic',
  'identity',
  'domain',
  'provenance',
  'behavior',
]

/** Secondary signals are advisory URL/structure metrics. */
function toUrlSignals(result: AnalysisResult): ReportUrlSignalRow[] {
  return result.secondarySignals.map((signal) => ({
    labelKey: signal.metricKey,
    valueEn: signal.valueEn,
    valueAr: signal.valueAr,
    severity: signal.severity,
  }))
}

/**
 * Optional Arabic counterparts, supplied by the caller.
 *
 * They are passed in rather than re-derived inside the mapper so
 * that both languages provably come from ONE result object: there is
 * no second read of the analysis and therefore no way for the two
 * renderings to disagree.
 */
export interface ReportLanguageOverrides {
  summaryAr: string
  assessmentAr: string | null
}

export function buildReportDocument(
  result: AnalysisResult,
  language: ReportLanguageOverrides = {
    summaryAr: '',
    assessmentAr: null,
  },
  when: Date = new Date(),
): ReportDocument {
  const modality = toReportModality(result.signal.kind)
  const detail = result.imageDetail ?? null

  const evidence: ReportEvidenceItem[] = result.graph.nodes.map((node) => ({
    id: node.id,
    label: node.labelEn,
    detail: node.detailEn,
    polarity: node.polarity,
    weight: node.weight,
  }))

  const urlSignals =
    detail === null && result.secondarySignals.length > 0
      ? toUrlSignals(result)
      : []

  return {
    reportId: makeReportId(modality, when),
    createdAt: when.toISOString(),
    modality,
    inputSummary: detail ? detail.fileName : result.signal.valueEn,

    overallAssessment:
      result.primarySignal !== null
        ? result.primarySignal.bodyEn
        : result.isMock
          ? 'This result was produced by a demonstration provider and does not represent an analysis of any real signal.'
          : 'The pipeline returned no single dominant finding for this signal. Individual measurements are reported below.',

    overallAssessmentAr: language.summaryAr,

    // A three-way classification exists only where the modality
    // actually computes one. A URL analysis reports its trust band
    // and nothing else, rather than being forced into "authentic".
    assessment: detail ? ASSESSMENT_EN[detail.assessment] : null,
    assessmentAr: detail ? ASSESSMENT_AR[detail.assessment] : null,

    trust: result.trustScore,
    riskLevel: result.riskLevel,
    confidence: result.confidence,

    dna: AXIS_ORDER.map((axis) => ({
      axis,
      labelKey: DNA_LABEL_KEYS[axis],
      value: result.dna[axis],
    })),

    evidence,

    // ---- image-modality sections; empty for everything else ----
    metadata:
      detail === null
        ? []
        : [
            { labelKey: 'image.metadata.format', valueEn: detail.metadata.format, valueAr: detail.metadata.format },
            {
              labelKey: 'image.metadata.dimensions',
              valueEn: `${detail.metadata.width} × ${detail.metadata.height}`,
              valueAr: `${detail.metadata.width} × ${detail.metadata.height}`,
            },
            { labelKey: 'image.metadata.colourMode', valueEn: detail.metadata.colorMode, valueAr: detail.metadata.colorMode },
            {
              labelKey: 'image.metadata.exif',
              valueEn: detail.metadata.exifPresent ? 'Present' : 'Not present',
              valueAr: detail.metadata.exifPresent ? 'موجود' : 'غير موجود',
            },
            { labelKey: 'image.metadata.camera', valueEn: detail.metadata.cameraMake ?? '—', valueAr: detail.metadata.cameraMake ?? '—' },
            { labelKey: 'image.metadata.software', valueEn: detail.metadata.software ?? '—', valueAr: detail.metadata.software ?? '—' },
            {
              labelKey: 'image.metadata.created',
              valueEn: detail.metadata.createdAt ?? '—',
              valueAr: detail.metadata.createdAt ?? '—',
            },
            {
              labelKey: 'image.metadata.gps',
              // BOOLEAN ONLY, matching the panel: coordinates are
              // never surfaced, in the app or in a report.
              valueEn: detail.metadata.gpsPresent ? 'Present' : 'Not present',
              valueAr: detail.metadata.gpsPresent ? 'موجود' : 'غير موجود',
            },
          ],

    forensics:
      detail === null
        ? []
        : detail.forensics.map((signal) => ({
            name: signal.name,
            value: signal.value,
            meaningEn: signal.meaningEn,
            // The pipeline supplies these definitions in English;
            // they are rendered verbatim rather than paraphrased.
            meaningAr: signal.meaningEn,
            doesNotMeanEn: signal.doesNotMeanEn,
            doesNotMeanAr: signal.doesNotMeanEn,
          })),

    provenance:
      detail === null
        ? []
        : [
            {
              statusKey: 'image.provenance.title',
              statusEn: detail.provenance.status.replace(/_/g, ' '),
              statusAr: detail.provenance.status,
              limitationEn: detail.provenance.limitationEn,
              limitationAr: detail.provenance.limitationAr,
            },
          ],

    urlSignals,

    timeline: result.timeline.map((entry) => ({
      stage: entry.stage,
      offsetSeconds: entry.offsetSeconds,
    })),

    /* ---- Phase 3.7: fact / inference separation ----
        The claims are bucketed by epistemic status rather than
        merged into one evidence list, so the rendered document can
        keep "we measured X" apart from "the model concluded Y". */
    claims: buildEvidenceClaims(result),
    fusionExplanationEn: fusionExplanation(result).en,
    fusionExplanationAr: fusionExplanation(result).ar,

    modelInfo: {
      engine: result.engine,
      engineVersion: result.engineVersion,
      /*
        An evidence result has no single model to disclose: it is a
        pipeline of two independent detectors, provenance inspection,
        OCR, QR, URL and encoding modules, each with its own status.
        Labelling the whole thing "advisory" would be a fabricated
        claim about components that were never asked, so the status is
        stated as what it actually is — a research-grade, advisory
        PIPELINE — and the per-detector statuses live in the claims
        above it.
      */
      statusEn: detail
        ? detail.model.status.replace(/_/g, ' ')
        : result.analysisSource === 'evidence'
          ? 'research-grade pipeline, advisory'
          : 'advisory',
      statusAr: detail ? detail.model.status.replace(/_/g, ' ') : 'إرشادي',
      advisoryOnly: detail ? detail.model.advisoryOnly : true,
      fitForAutomatedEnforcement: detail
        ? detail.model.fitForAutomatedEnforcement
        : false,
      // An evidence result carries the pipeline's OWN limitation
      // strings, which are strictly more informative than a generic
      // per-modality sentence. Both are bilingual by construction:
      // the backend writes its limitations in English, so the Arabic
      // column receives the same text rather than an invented
      // translation that might say something weaker.
      limitationsEn: detail
        ? detail.model.knownLimitations
        : reportLimitations(result).en,
      limitationsAr: detail
        ? detail.model.knownLimitations
        : reportLimitations(result).ar,
    },

    safety:
      'BASIRAH provides advisory, probabilistic analysis. This report should not be considered definitive proof or used as the sole basis for a decision.',

    team: projectMembers,
  }
}

/** Arabic executive summary, derived from the same result. */
export function buildArabicSummary(result: AnalysisResult): string {
  if (result.primarySignal !== null) return result.primarySignal.bodyAr
  return 'لم يُرجع المحرك نتيجة واحدة مهيمنة لهذه الإشارة. القياسات الفردية مدرجة أدناه.'
}

/** Arabic three-way classification, where one exists. */
export function assessmentAr(result: AnalysisResult): string | null {
  const detail = result.imageDetail
  return detail ? ASSESSMENT_AR[detail.assessment] : null
}

/** Arabic risk band label keys, indexed by the domain risk level. */
export const RISK_LABEL_KEYS = {
  trusted: 'score.trusted',
  caution: 'score.caution',
  high_risk: 'score.highRisk',
} as const satisfies Record<RiskLevel, string>

export type RiskLabelKey = keyof typeof RISK_LABEL_KEYS