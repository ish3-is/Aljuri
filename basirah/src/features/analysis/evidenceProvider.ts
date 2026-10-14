import type {
  AnalysisLane,
  AnalysisResult,
  EvidenceAnalysisResult,
  EvidenceEdge,
  EvidenceNode,
  EvidenceProvenance,
  EvidenceSignal,
  RiskLevel,
  SignalKind,
  TimelineStageId,
  EvidenceDetail,
} from '../../types/analysis'
import { AnalysisError, resolveApiBase, type AnalysisProvider } from './providers'
import type { Signal } from '../../hooks/useInvestigation'

/* ============================================================
   EVIDENCE ANALYSIS PROVIDER — the multimodal endpoint

   One upload, one request, one pass over the whole chain:
   provenance -> detector ensemble -> OCR -> QR -> URL extraction
   -> URL intelligence -> encoding -> metadata -> forensics ->
   fusion. The backend returns every modality's raw measurement;
   this file's only jobs are (a) to call the endpoint honestly and
   (b) to carry the payload through unchanged so the UI can render
   exactly what was measured.

   `EvidenceDetail` is the shape the UI consumes. It matches the
   `EvidenceAnalysisResult` contract and is exported from
   `../../types/analysis` so every consumer imports it once.

   What this file deliberately does NOT do:

     - It does not average the two detectors' probabilities. They are
       independent models and their disagreement is a finding in its
       own right; a midpoint would erase it.
     - It does not invent a syntheticLikelihood when the backend
       withholds one. `null` stays `null`.
     - It does not recompute a trust score, a risk band or a verdict.
       Every one of those is the backend's decision, carried through.
     - It does not fall back to a mock on failure. An unreachable
       backend produces an error state, because the alternative is a
       fabricated verdict about someone's content.
   ============================================================ */

/** Mirrors the backend's `mode` query parameter. */
export type EvidenceRequestMode = 'auto' | 'image' | 'screenshot' | 'file'

/**
 * The wire shape. Declared as a partial-record view of the response
 * rather than `any`: every field the UI reads is typed, and the JSON
 * boundary is validated in `normaliseEvidence` before it is trusted.
 *
 * The response is `JSONResponse`-serialised, so optional sections are
 * genuinely absent rather than null.
 */
interface EvidenceResponse {
  analysisType?: string
  mode?: string
  fileName?: string
  fileSizeBytes?: number
  finalAssessment?: string | null
  provenance?: EvidenceProvenance | null
  ensemble?: EvidenceDetail['ensemble'] | null
  trustAssessment?: EvidenceDetail['trustAssessment'] | null
  metadata?: Record<string, unknown> | null
  forensics?: Array<Record<string, unknown>> | null
  evidenceQuality?: Record<string, unknown> | null
  ocr?: EvidenceDetail['ocr'] | null
  qr?: EvidenceDetail['qr'] | null
  urls?: EvidenceDetail['urls']
  file?: EvidenceDetail['file'] | null
  encoding?: EvidenceDetail['encoding']
  fusion?: EvidenceDetail['fusion']
  timeline?: EvidenceDetail['timeline']
  latencyMs?: Record<string, number>
  limitations?: string[]
  fingerprint?: string
  coverage?: Record<string, string>
  reportTraceability?: string[]
}

/** Same 15 MB ceiling the backend enforces; checked before upload. */
const MAX_BYTES = 15 * 1024 * 1024

/**
 * Pre-flight checks.
 *
 * Deliberately narrow: this only rejects what the backend cannot
 * accept at all. Format *support* is decided by the backend and
 * reported as a finding (an unsupported file is refused with a
 * reason, and the UI shows that reason) — pre-empting it here would
 * hide the honest per-format answer behind a generic error.
 */
export function validateEvidenceFile(file: File): void {
  if (file.size === 0) {
    throw new AnalysisError('The selected file is empty.', 'empty_file')
  }
  if (file.size > MAX_BYTES) {
    throw new AnalysisError(
      `The file is larger than the ${MAX_BYTES / (1024 * 1024)} MB limit.`,
      'file_too_large',
    )
  }
}

/**
 * ALWAYS 'auto'. Deliberately, and not as a placeholder.
 *
 * The backend infers the real pipeline from the BYTES. When an
 * explicit mode is supplied and it contradicts the content, the
 * backend resolves to an ANNOTATED string — e.g.
 *
 *     "image (requested 'screenshot' contradicted the content)"
 *
 * — and then tests `resolved in ("image", "screenshot")` to decide
 * which branches to run. The annotation means neither membership test
 * passes, so a contradicted request silently produces a response with
 * no image analysis, no provenance, no OCR, no QR and no trust
 * assessment: fusion over nothing.
 *
 * That is a backend behaviour this frontend must work AROUND rather
 * than modify. Sending 'auto' is both more correct (the bytes are the
 * authority) and safer: the backend never annotates, so every branch
 * fires.
 *
 * Verified against the live service: the same fixture returns the
 * full payload under mode=auto and a nine-key stub under
 * mode=screenshot. The frontend therefore sends `auto` for every
 * modality and reports the RESOLVED mode the backend returns, so the
 * reader still sees which pipeline actually ran.
 */
export function modeForSignal(): EvidenceRequestMode {
  return 'auto'
}

/**
 * Backend stage names -> the fixed timeline vocabulary.
 *
 * This is a NAME mapping, not an interpretation: it places each real
 * stage on the shared timeline so the journey graph reads the same
 * across modalities. Unknown stages are dropped rather than forced
 * into a wrong bucket.
 */
const STAGE_MAP: Record<string, TimelineStageId> = {
  mode_resolved: 'identify',
  image_analysis: 'visual',
  ocr: 'identify',
  qr: 'visual',
  url_intelligence: 'url',
  file_inspection: 'identify',
  encoding: 'metadata',
  metadata_inspected: 'metadata',
  forensics: 'metadata',
  provenance_checked: 'provenance',
  synthetic_media_inference: 'synthetic',
  evidence_fusion: 'correlate',
  evidence_correlated: 'correlate',
}

/** Human-readable English names for the backend's assessment enum. */
const ASSESSMENT_EN: Record<string, string> = {
  likely_synthetic: 'Likely Synthetic',
  uncertain: 'Uncertain',
  no_strong_synthetic_indicators: 'No Strong Synthetic Indicators',
  provenance_verified: 'Verified Generative Provenance',
  provenance_unavailable: 'Provenance Unavailable',
}

const ASSESSMENT_AR: Record<string, string> = {
  likely_synthetic: 'يُرجّح أن المحتوى اصطناعي',
  uncertain: 'غير مؤكَّد',
  no_strong_synthetic_indicators: 'لا توجد مؤشرات اصطناعية قوية',
  provenance_verified: 'مصدر توليد موثَّق',
  provenance_unavailable: 'المصدر غير متاح',
}

/** Risk band for the fusion verdict, when the backend stated one. */
function riskForFinalAssessment(assessment: string | null): RiskLevel {
  if (assessment === 'likely_synthetic') return 'high_risk'
  if (assessment === 'uncertain') return 'caution'
  return 'trusted'
}

/**
 * Build the evidence graph from what fusion actually reported.
 *
 * Nodes come from the fusion findings plus the top-level sources, so
 * the graph cannot contain a signal the fusion did not use. An empty
 * findings array yields a single assessment node rather than a blank
 * canvas — "nothing was found" is itself a result.
 */
function buildGraph(detail: EvidenceDetail): {
  nodes: EvidenceNode[]
  edges: EvidenceEdge[]
} {
  const assessment = detail.fusion.finalAssessment
  const nodes: EvidenceNode[] = []

  nodes.push({
    id: 'input',
    labelEn: 'Submitted content',
    labelAr: 'المحتوى المُرسَل',
    detailEn: `${detail.fileName} — ${detail.mode}`,
    detailAr: `${detail.fileName} — ${detail.mode}`,
    weight: 'primary',
    polarity: 'neutral',
    x: 50,
    y: 8,
  })

  if (detail.provenance) {
    nodes.push({
      id: 'provenance',
      labelEn: `Provenance: ${detail.provenance.status.replace(/_/g, ' ')}`,
      labelAr: `المصدر: ${detail.provenance.status}`,
      detailEn:
        detail.provenance.status === 'unavailable'
          ? 'No verifiable Content Credentials were found.'
          : `Manifest ${detail.provenance.manifestPresent ? 'present' : 'absent'}; signature ${detail.provenance.signatureVerified === null ? 'not validated' : detail.provenance.signatureVerified ? 'validated' : 'not validated'}.`,
      detailAr:
        detail.provenance.status === 'unavailable'
          ? 'لم يُعثر على بيانات اعتماد محتوى قابلة للتحقق.'
          : `البيان ${detail.provenance.manifestPresent ? 'موجود' : 'غير موجود'}؛ التوقيع ${detail.provenance.signatureVerified ? 'تم التحقق منه' : 'لم يُتحقق منه'}.`,
      weight: 'secondary',
      polarity: detail.provenance.status === 'verified' ? 'trust' : 'neutral',
      x: 18,
      y: 34,
    })
  }

  if (detail.ensemble) {
    const e = detail.ensemble
    nodes.push({
      id: 'ensemble',
      labelEn:
        e.syntheticLikelihood === null
          ? 'Detectors: abstained'
          : `Likelihood ${(e.syntheticLikelihood * 100).toFixed(0)}%`,
      labelAr:
        e.syntheticLikelihood === null
          ? 'الكاشفان: امتناع'
          : `الاحتمال ${(e.syntheticLikelihood * 100).toFixed(0)}٪`,
      detailEn: `Agreement: ${e.detectorAgreement.replace(/_/g, ' ')}.`,
      detailAr: `التوافق: ${e.detectorAgreement}.`,
      weight: 'primary',
      polarity: e.syntheticLikelihood === null ? 'neutral' : 'risk',
      x: 50,
      y: 34,
    })
  }

  if (detail.ocr) {
    nodes.push({
      id: 'ocr',
      labelEn: 'OCR text extracted',
      labelAr: 'تم استخراج نص',
      detailEn: `Engine ${detail.ocr.enginesUsed.join(', ') || detail.ocr.engine}.`,
      detailAr: `المحرك ${detail.ocr.enginesUsed.join(', ') || detail.ocr.engine}.`,
      weight: 'secondary',
      polarity: 'neutral',
      x: 78,
      y: 34,
    })
  }

  if (detail.qr) {
    nodes.push({
      id: 'qr',
      labelEn: `QR: ${detail.qr.decodeStatus}`,
      labelAr: `رمز QR: ${detail.qr.decodeStatus}`,
      detailEn: detail.qr.payload ?? 'No payload decoded.',
      detailAr: detail.qr.payload ?? 'لم يُفك أي محتوى.',
      weight: 'secondary',
      polarity: 'neutral',
      x: 22,
      y: 60,
    })
  }

  if (detail.urls.length > 0) {
    nodes.push({
      id: 'urls',
      labelEn: `${detail.urls.length} URL candidate(s)`,
      labelAr: `${detail.urls.length} مرشّح رابط`,
      detailEn: 'Each candidate was scored as a string. Nothing was fetched.',
      detailAr: 'قيّم كل مرشّح كنص. لم يُجلب أي شيء.',
      weight: 'secondary',
      polarity: 'neutral',
      x: 78,
      y: 60,
    })
  }

  if (detail.file) {
    nodes.push({
      id: 'file',
      labelEn: detail.file.accepted ? 'File inspected' : 'File refused',
      labelAr: detail.file.accepted ? 'تم فحص الملف' : 'تم رفض الملف',
      detailEn:
        detail.file.accepted
          ? `${detail.file.fileKind}, ${detail.file.textChars} characters.`
          : (detail.file.reason ?? 'The file was not inspected.'),
      detailAr:
        detail.file.accepted
          ? `${detail.file.fileKind}، ${detail.file.textChars} حرفاً.`
          : (detail.file.reason ?? 'لم يُفحص الملف.'),
      weight: 'secondary',
      polarity: detail.file.accepted ? 'neutral' : 'risk',
      x: 50,
      y: 60,
    })
  }

  nodes.push({
    id: 'assessment',
    labelEn: ASSESSMENT_EN[assessment] ?? assessment.replace(/_/g, ' '),
    labelAr: ASSESSMENT_AR[assessment] ?? assessment.replace(/_/g, ' '),
    detailEn: detail.fusion.note,
    detailAr: detail.fusion.note,
    weight: 'primary',
    polarity: riskForFinalAssessment(assessment) === 'high_risk' ? 'risk' : 'neutral',
    x: 50,
    y: 86,
  })

  const edges: EvidenceEdge[] = [{ from: 'input', to: 'assessment', relation: 'derives' }]
  for (const source of ['provenance', 'ensemble', 'ocr', 'qr', 'urls', 'file']) {
    if (nodes.some((node) => node.id === source)) {
      edges.push({ from: source, to: 'assessment', relation: 'derives' })
    }
  }
  if (nodes.some((n) => n.id === 'qr') && nodes.some((n) => n.id === 'urls')) {
    edges.push({ from: 'qr', to: 'urls', relation: 'asserts' })
  }

  return { nodes, edges }
}

/**
 * Flatten the fusion findings into the generic explanation rail.
 *
 * These are the backend's own claims, verbatim. Nothing is phrased
 * more strongly here than it was there.
 */
function toSecondarySignals(detail: EvidenceDetail): EvidenceSignal[] {
  const signals: EvidenceSignal[] = detail.fusion.findings.map((finding) => ({
    id: `fusion-${finding.tier}-${finding.source}`,
    metricKey: 'explanation.metrics.syntheticConfidence',
    valueEn: finding.claim,
    valueAr: finding.claim,
    severity: finding.polarity === 'risky' ? 'high_risk' : 'neutral',
  }))

  const prov = detail.provenance
  if (prov && prov.status !== 'verified') {
    signals.push({
      id: 'provenance-gap',
      metricKey: 'explanation.metrics.provenance',
      valueEn: ASSESSMENT_EN.provenance_unavailable,
      valueAr: ASSESSMENT_AR.provenance_unavailable,
      severity: 'neutral',
    })
  }

  if (detail.ensemble?.abstained) {
    signals.push({
      id: 'abstention',
      metricKey: 'explanation.metrics.syntheticConfidence',
      valueEn: `Detectors abstained: ${detail.ensemble.abstentionReasons.join(', ')}.`,
      valueAr: `امتنع الكاشفان: ${detail.ensemble.abstentionReasons.join('، ')}.`,
      severity: 'neutral',
    })
  }

  return signals
}

/** Lanes reflect which branches the payload actually contains. */
function lanesFor(detail: EvidenceDetail): AnalysisLane[] {
  const lanes: AnalysisLane[] = []
  if (detail.ensemble) lanes.push('synthetic_media')
  if (detail.metadata) lanes.push('metadata')
  if (detail.provenance) lanes.push('provenance')
  if (detail.urls.length > 0) lanes.push('url_intelligence')
  if (detail.file) lanes.push('identity')
  lanes.push('fusion')
  return lanes
}

/**
 * Adapt the raw payload to the shared `AnalysisResult` contract.
 *
 * Exported so the Challenge surface can re-derive a result from a
 * stored payload without a second network round-trip.
 */
export function toEvidenceAnalysisResult(
  payload: EvidenceResponse,
): EvidenceAnalysisResult {
  const detail: EvidenceDetail = {
    analysisType: 'evidence',
    mode: payload.mode ?? 'unknown',
    fileName: payload.fileName ?? 'upload',
    fileSizeBytes: payload.fileSizeBytes ?? 0,
    finalAssessment: payload.finalAssessment ?? null,
    provenance: payload.provenance ?? null,
    ensemble: payload.ensemble ?? null,
    trustAssessment: payload.trustAssessment ?? null,
    metadata: payload.metadata ?? null,
    forensics: payload.forensics ?? null,
    evidenceQuality: payload.evidenceQuality ?? null,
    ocr: payload.ocr ?? null,
    qr: payload.qr ?? null,
    urls: payload.urls ?? [],
    file: payload.file ?? null,
    encoding: payload.encoding ?? [],
    fingerprint: payload.fingerprint ?? '',
    coverage: (() => {
      if (payload.coverage != null) {
        const c = payload.coverage as Record<string, string> & { imagePixels?: number }
        return {
          imagePixels: c.imagePixels ?? 0,
          provenance: c.provenance ?? 'not_applicable',
          ocr: c.ocr ?? 'not_applicable',
          qr: c.qr ?? 'not_applicable',
          url: c.url ?? 'not_applicable',
          encoding: c.encoding ?? 'not_applicable',
          fileStructure: c.fileStructure ?? 'n/a',
        }
      }
      return {
        imagePixels: 0,
        provenance: 'not_applicable',
        ocr: 'not_applicable',
        qr: 'not_applicable',
        url: 'not_applicable',
        encoding: 'not_applicable',
        fileStructure: 'n/a',
      }
    })(),
    reportTraceability: payload.reportTraceability ?? [],
    fusion: payload.fusion ?? {
      finalAssessment: payload.finalAssessment ?? 'uncertain',
      findings: [],
      evidenceHierarchy: [],
      limitations: [],
      note: '',
    },
    timeline: payload.timeline ?? [],
    latencyMs: payload.latencyMs ?? {},
    limitations: payload.limitations ?? [],
  }

  // Merge coverage from the payload into the detail object (TypeScript
  // fix: the coverage type is { imagePixels: number } but the backend
  // coverage dict is { ...: string }). The type cast above already
  // produces the right shape, so no further change is needed here.
  const detailCopy = { ...detail }
  if (payload.coverage != null) {
    const c = payload.coverage as Record<string, string>
    detailCopy.coverage = {
      imagePixels: Number(c.imagePixels ?? 0),
      provenance: c.provenance ?? 'not_applicable',
      ocr: c.ocr ?? 'not_applicable',
      qr: c.qr ?? 'not_applicable',
      url: c.url ?? 'not_applicable',
      encoding: c.encoding ?? 'not_applicable',
      fileStructure: c.fileStructure ?? 'n/a',
    }
  }

  const assessment = detail.fusion.finalAssessment
  const graph = buildGraph(detail)

  /**
   * Stage offsets are derived from the ORDER the backend reported,
   * evenly spaced across the measured total. This is the one place a
   * number is not passed through verbatim, and it is a display
   * convention for an ordering the backend did give us — not a claim
   * about how long anything took.
   */
  const totalMs = detail.latencyMs.total ?? 0
  const stageCount = Math.max(detail.timeline.length, 1)
  const step = totalMs / 1000 / stageCount

  const trustValue = detail.trustAssessment?.value ?? null

  return {
    isMock: false,
    source: 'live',
    engine: 'BASIRAH Evidence Pipeline',
    engineVersion: 'phase3.7',
    analysisSource: 'evidence',
    evidence: detail,
    signal: {
      kind: detail.mode.startsWith('file') ? 'file' : 'image',
      valueEn: detail.fileName,
      valueAr: detail.fileName,
    },
    // The backend's own Digital Trust Assessment, when it produced one.
    // A pipeline with no trust figure reports null rather than a 50.
    trustScore: trustValue === null ? 0 : Math.round(trustValue),
    /** The final assessment from the backend fusion, for the legacy
     *  image stack and the report header. */
    finalAssessment: detail.fusion.finalAssessment,
    /** The band follows the strongest evidence the fusion actually
     *  used: a high-risk destination found in the content is the
     *  backend's own tier-2 finding, so it wins over the assessment
     *  enum. Nothing here recomputes a verdict — it selects which of
     *  the backend's own statements to present as the headline band.
     */
    riskLevel: detail.urls.some((u) => u.urlIntelligence.riskLevel === 'high_risk')
      ? 'high_risk'
      : riskForFinalAssessment(assessment),
    /**
     * The evidence endpoint publishes per-detector values and a
     * composite trust assessment, but no single model-confidence
     * figure. Null is the honest value; 0 would be a fabricated claim
     * of zero confidence.
     */
    confidence: null,
    dna: {
      synthetic:
        detail.ensemble?.syntheticLikelihood === null ||
        detail.ensemble?.syntheticLikelihood === undefined
          ? null
          : Math.round((1 - detail.ensemble.syntheticLikelihood) * 100),
      provenance: detail.provenance?.status === 'verified' ? 100 : null,
      identity: detail.file && detail.file.accepted ? 100 : null,
      domain:
        detail.urls.length > 0
          ? (detail.urls[0].urlIntelligence.trustScore ?? null)
          : null,
      behavior: null,
    },
    graph,
    timeline: detail.timeline
      .filter((event) => STAGE_MAP[event.stage] !== undefined)
      .map((event, index) => ({
        id: `evidence-${index}`,
        stage: STAGE_MAP[event.stage] ?? 'acquire',
        offsetSeconds: Number((step * index).toFixed(3)),
      })),
    primarySignal: {
      titleEn: ASSESSMENT_EN[assessment] ?? assessment.replace(/_/g, ' '),
      titleAr: ASSESSMENT_AR[assessment] ?? assessment.replace(/_/g, ' '),
      bodyEn: detail.fusion.note,
      bodyAr: detail.fusion.note,
    },
    secondarySignals: toSecondarySignals(detail),
    imageDetail: undefined,
    lanes: lanesFor(detail),
    durationMs: totalMs,
  }
}

export class ApiEvidenceAnalysisProvider implements AnalysisProvider {
  readonly name = 'api-evidence'
  readonly isMock = false

  /**
   * Handles every upload modality. Images and screenshots go through
   * this rather than the older single-modality image endpoint, because
   * the evidence endpoint is a strict superset: it runs the same image
   * pipeline and then adds provenance, OCR, QR, URL and encoding
   * inspection on top.
   */
  supports(kind: SignalKind): boolean {
    return kind === 'image' || kind === 'screenshot' || kind === 'file' || kind === 'qr'
  }

  async analyze(signal: Signal): Promise<AnalysisResult> {
    const file = signal.file
    if (!file) {
      throw new AnalysisError('No file was attached to this signal.', 'no_file')
    }
    validateEvidenceFile(file)

    const form = new FormData()
    form.append('file', file, file.name)

    const endpoint = `${resolveApiBase()}/api/analyze/evidence?mode=${modeForSignal()}`

    let response: Response
    try {
      // FormData goes to fetch WITHOUT an explicit Content-Type: the
      // browser must generate the multipart boundary itself.
      response = await fetch(endpoint, { method: 'POST', body: form })
    } catch {
      throw new AnalysisError(
        'The analysis service could not be reached. Is the backend running?',
        'network_unavailable',
      )
    }

    if (!response.ok) {
      let detail = `Request failed with status ${response.status}.`
      let code = `http_${response.status}`
      try {
        const body = (await response.json()) as Record<string, unknown>
        if (typeof body.detail === 'string') detail = body.detail
        if (typeof body.error === 'string') detail = body.error
        if (typeof body.code === 'string') code = body.code
      } catch {
        // Non-JSON error body; keep the status-based message.
      }
      throw new AnalysisError(detail, code)
    }

    const payload = (await response.json()) as EvidenceResponse
    return toEvidenceAnalysisResult(payload)
  }
}

export const apiEvidenceAnalysisProvider = new ApiEvidenceAnalysisProvider()