/**
 * Image analysis provider — the real backend, not the Phase 1 mock.
 *
 * Phase 3.5 replaces mock image routing entirely. There is deliberately
 * NO fallback to the mock provider: if the backend is unreachable or
 * rejects the file, the user gets an honest error state. Returning a
 * fabricated verdict for an image was never acceptable, and once the real
 * pipeline exists a silent fallback would hide outages.
 *
 * The research-grade status of the image model is carried through to the
 * UI rather than smoothed over. The UI is expected to render the
 * advisory notice and any evidence-quality warnings this returns.
 */

import type {
  AnalysisResult,
  EvidenceEdge,
  EvidenceNode,
  EvidenceSignal,
  ImageAssessment,
  ImageDetail,
  ImageProvenanceStatus,
  RiskLevel,
  SignalKind,
  TimelineStageId,
} from '../../types/analysis'
import { AnalysisError, resolveApiBase, type AnalysisProvider } from './providers'
import type { Signal } from '../../hooks/useInvestigation'

/**
 * Pre-flight upload checks.
 *
 * These deliberately throw plain `AnalysisError` rather than a subclass.
 * An earlier version declared `class ImageUploadError extends
 * AnalysisError`, which created a cycle: providers.ts imports this module
 * to route image signals, so at class-definition time `AnalysisError` was
 * still undefined and the bundle threw
 * "Class extends value undefined is not a constructor" — crashing the
 * whole app before it rendered. TypeScript could not catch it because the
 * types resolve fine; only a real browser could.
 *
 * The subclass never carried extra behaviour, only a distinct name, so
 * removing it is both the fix and a simplification. The stable `code`
 * string is what callers actually branch on.
 */

const SUPPORTED_MIME = ['image/jpeg', 'image/png', 'image/webp']
const SUPPORTED_EXT = ['.jpg', '.jpeg', '.png', '.webp']
const MAX_BYTES = 15 * 1024 * 1024

/** Pre-flight checks that stop obviously-bad uploads before the network. */
export function validateImageFile(file: File): void {
  if (file.size === 0) {
    throw new AnalysisError('The selected file is empty.', 'empty_file')
  }
  if (file.size > MAX_BYTES) {
    throw new AnalysisError(
      `The image is larger than the ${MAX_BYTES / (1024 * 1024)} MB limit.`,
      'file_too_large',
    )
  }
  const lowerName = file.name.toLowerCase()
  const extOk = SUPPORTED_EXT.some((ext) => lowerName.endsWith(ext))
  const mimeOk = SUPPORTED_MIME.includes(file.type)
  if (!extOk && !mimeOk) {
    throw new AnalysisError(
      'That file type is not supported. Use JPEG, PNG or WEBP.',
      'unsupported_format',
    )
  }
}

/** Raw backend payload. Only the fields the UI actually renders. */
export interface ApiImageResponse {
  analysisType: 'image'
  fileName: string
  fileSizeBytes: number
  trustScore: number
  riskLevel: string
  confidence: number
  assessment: 'likely_authentic' | 'uncertain' | 'likely_synthetic'
  finalAssessment?: 'likely_authentic' | 'uncertain' | 'likely_synthetic'
  synthetic: {
    syntheticProbability: number | null
    authenticProbability: number | null
    assessment: string
    uncertain: boolean
    uncertaintyLower: number
    uncertaintyUpper: number
  }
  model: {
    modelName: string | null
    modelVersion: string | null
    available: boolean
    reason: string | null
    status: string
    advisoryOnly: boolean
    fitForAutomatedEnforcement: boolean
    noticeEn: string
    noticeAr: string
    knownLimitations: string[]
    trainedFamilies?: string[]
    evaluatedHeldOutFamily?: string
  }
  metadata: {
    format: string
    width: number
    height: number
    colorMode: string
    exifPresent: boolean
    cameraMake: string | null
    cameraModel: string | null
    software: string | null
    createdAt: string | null
    orientation: number | null
    gpsPresent: boolean
    interpretationEn: string
    interpretationAr: string
  }
  provenance: {
    status: 'verified' | 'present_unverified' | 'invalid' | 'unavailable'
    contentCredentialsPresent: boolean
    manifestFound: boolean
    limitationEn: string
    limitationAr: string
  }
  forensics: Array<{
    name: string
    value: number | null
    meaningEn: string
    doesNotMeanEn: string
  }>
  evidenceQuality: {
    longEdge: number
    lowResolution: boolean
    warnings: Array<{ code: string; severity: string; en: string; ar: string }>
  }
  timeline: Array<{ stage: string; evidence: string; status: string }>
  safety: {
    fitForAutomatedEnforcement: boolean
    status: string
    advisoryOnly: boolean
  }
  durationMs: number
}

/** Map a backend risk string onto the frontend union, defaulting safely. */
function toRiskLevel(value: string): RiskLevel {
  switch (value) {
    case 'low_risk':
      return 'trusted'
    case 'high_risk':
      return 'high_risk'
    case 'caution':
    default:
      // 'elevated' from the backend has no distinct level in the frontend
      // union, so it maps to 'caution' rather than being invented.
      return 'caution'
  }
}

/** Backend stage names -> the frontend's fixed stage vocabulary. */
const STAGE_MAP: Record<string, TimelineStageId> = {
  image_validated: 'acquire',
  image_decoded: 'acquire',
  metadata_inspected: 'metadata',
  provenance_checked: 'provenance',
  forensic_signals_computed: 'metadata',
  synthetic_media_inference: 'synthetic',
  synthetic_model_unavailable: 'synthetic',
  evidence_correlated: 'correlate',
  trust_assessment_generated: 'score',
}

/**
 * Adapt the backend payload to the frontend contract.
 *
 * Only Synthetic and Provenance are informed by a still image, so the
 * other three DNA axes stay null and the UI renders them as N/A. Turning
 * an unmeasured axis into 0 would present "we did not check" as "we
 * measured zero", which is exactly the fabrication to avoid here.
 */
export function toImageAnalysisResult(
  payload: ApiImageResponse,
  previewUrl?: string,
): AnalysisResult {
  const p = payload.synthetic.syntheticProbability
  const uncertain = payload.synthetic.uncertain

  // Three-way headline. A binary "fake / not fake" label would present a
  // probabilistic detector as an oracle.
  const headlineEn =
    payload.assessment === 'likely_synthetic'
      ? 'Indicators associated with synthetic media were detected.'
      : payload.assessment === 'likely_authentic'
        ? 'No strong synthetic-media indicators were detected.'
        : 'Insufficient evidence for a confident classification.'
  const headlineAr =
    payload.assessment === 'likely_synthetic'
      ? 'تم رصد مؤشرات مرتبطة بالمحتوى الاصطناعي.'
      : payload.assessment === 'likely_authentic'
        ? 'لم يتم رصد مؤشرات قوية للمحتوى الاصطناعي.'
        : 'الأدلة غير كافية للتصنيف بثقة.'

  const titleEn =
    payload.assessment === 'likely_synthetic'
      ? 'Likely Synthetic'
      : payload.assessment === 'likely_authentic'
        ? 'Likely Authentic'
        : 'Uncertain'
  const titleAr =
    payload.assessment === 'likely_synthetic'
      ? 'يُرجّح أن الصورة اصطناعية'
      : payload.assessment === 'likely_authentic'
        ? 'يُرجّح أن الصورة أصلية'
        : 'غير مؤكَّد'

  // Evidence-quality warnings come FIRST so a low-resolution image can
  // never read as a confident verdict.
  const signals: EvidenceSignal[] = payload.evidenceQuality.warnings.map((warning) => ({
    id: `quality-${warning.code}`,
    metricKey: 'explanation.metrics.syntheticConfidence',
    valueEn: warning.en,
    valueAr: warning.ar,
    severity: warning.severity === 'high' ? 'high_risk' : 'neutral',
  }))

  signals.push({
    id: 'image-metadata',
    metricKey: 'explanation.metrics.domainStructure',
    valueEn: payload.metadata.interpretationEn,
    valueAr: payload.metadata.interpretationAr,
    severity: 'neutral',
  })

  signals.push({
    id: 'image-provenance',
    metricKey: 'explanation.metrics.provenance',
    valueEn: payload.provenance.limitationEn,
    valueAr: payload.provenance.limitationAr,
    severity: 'neutral',
  })

  // Report only what the backend actually measured. A count of measured
  // characteristics is honest; implying all four were available is not.
  const measured = payload.forensics.filter((f) => f.value !== null).length
  if (measured > 0) {
    signals.push({
      id: 'image-forensics',
      metricKey: 'explanation.metrics.brandMatch',
      valueEn: `${measured} measured forensic characteristic(s). Supporting signals only, not proof.`,
      valueAr: `${measured} خاصية جنائية مقاسة. إشارات مساندة فقط وليست دليلاً قاطعًا.`,
      severity: 'neutral',
    })
  }

  const probabilityEn =
    p === null ? 'Model unavailable' : `Synthetic likelihood ${(p * 100).toFixed(0)}%`
  const probabilityAr =
    p === null ? 'النموذج غير متاح' : `احتمال أصطناعي ${(p * 100).toFixed(0)}٪`

  const polarity: 'risk' | 'trust' | 'neutral' =
    payload.assessment === 'likely_synthetic'
      ? 'risk'
      : payload.assessment === 'likely_authentic'
        ? 'trust'
        : 'neutral'

  const nodes: EvidenceNode[] = [
    {
      id: 'image',
      labelEn: 'Uploaded image',
      labelAr: 'الصورة المرفوعة',
      detailEn: `${payload.metadata.width}×${payload.metadata.height} ${payload.metadata.format}`,
      detailAr: `${payload.metadata.width}×${payload.metadata.height} ${payload.metadata.format}`,
      weight: 'primary',
      polarity: 'neutral',
      x: 50,
      y: 12,
    },
    {
      id: 'synthetic',
      labelEn: probabilityEn,
      labelAr: probabilityAr,
      detailEn: uncertain
        ? 'Falls inside the uncertain band derived from validation data.'
        : 'Research-grade detector output. Probabilistic, not proof.',
      detailAr: uncertain
        ? 'تقع ضمن النطاق غير المؤكد المشتق من بيانات التحقق.'
        : 'مخرجات نموذج بحثي. النتيجة احتمالية وليست دليلاً قاطعًا.',
      weight: 'primary',
      polarity,
      x: 20,
      y: 45,
    },
    {
      id: 'metadata',
      labelEn: payload.metadata.exifPresent ? 'EXIF present' : 'No EXIF metadata',
      labelAr: payload.metadata.exifPresent ? 'بيانات EXIF موجودة' : 'لا توجد بيانات EXIF',
      detailEn: payload.metadata.interpretationEn,
      detailAr: payload.metadata.interpretationAr,
      weight: 'secondary',
      polarity: 'neutral',
      x: 62,
      y: 45,
    },
    {
      id: 'provenance',
      labelEn: `Provenance: ${payload.provenance.status.replace(/_/g, ' ')}`,
      labelAr: `المصدر: ${payload.provenance.status}`,
      detailEn: payload.provenance.limitationEn,
      detailAr: payload.provenance.limitationAr,
      weight: 'secondary',
      polarity: 'neutral',
      x: 84,
      y: 45,
    },
    {
      id: 'assessment',
      labelEn: titleEn,
      labelAr: titleAr,
      detailEn: headlineEn,
      detailAr: headlineAr,
      weight: 'primary',
      polarity,
      x: 50,
      y: 82,
    },
  ]

  const edges: EvidenceEdge[] = [
    { from: 'image', to: 'synthetic', relation: 'derives' },
    { from: 'image', to: 'metadata', relation: 'derives' },
    { from: 'image', to: 'provenance', relation: 'derives' },
    { from: 'synthetic', to: 'assessment', relation: 'asserts' },
    { from: 'metadata', to: 'assessment', relation: 'derives' },
    { from: 'provenance', to: 'assessment', relation: 'derives' },
  ]

  const step = payload.durationMs / 1000 / Math.max(payload.timeline.length, 1)

  /**
   * The raw image subset, carried through untouched so the dedicated
   * panels can render what the pipeline actually measured. The generic
   * `secondarySignals` rail above flattens all of this into prose;
   * it cannot express a per-signal "does not mean", so that half of
   * each forensic signal would otherwise be dropped from the UI.
   *
   * `checkpoint` from the model payload is deliberately NOT copied:
   * the checkpoint filename is an internal artefact and is not shown.
   */
  const imageDetail: ImageDetail = {
    fileName: payload.fileName,
    fileSizeBytes: payload.fileSizeBytes,
    previewUrl,
    assessment: payload.assessment as ImageAssessment,
    synthetic: {
      syntheticProbability: payload.synthetic.syntheticProbability,
      authenticProbability: payload.synthetic.authenticProbability,
      uncertain: payload.synthetic.uncertain,
      uncertaintyLower: payload.synthetic.uncertaintyLower,
      uncertaintyUpper: payload.synthetic.uncertaintyUpper,
    },
    model: {
      modelName: payload.model.modelName,
      modelVersion: payload.model.modelVersion,
      available: payload.model.available,
      reason: payload.model.reason,
      status: payload.model.status,
      advisoryOnly: payload.model.advisoryOnly,
      fitForAutomatedEnforcement: payload.model.fitForAutomatedEnforcement,
      noticeEn: payload.model.noticeEn,
      noticeAr: payload.model.noticeAr,
      knownLimitations: payload.model.knownLimitations,
      trainedFamilies: payload.model.trainedFamilies,
      evaluatedHeldOutFamily: payload.model.evaluatedHeldOutFamily,
    },
    metadata: {
      format: payload.metadata.format,
      width: payload.metadata.width,
      height: payload.metadata.height,
      colorMode: payload.metadata.colorMode,
      exifPresent: payload.metadata.exifPresent,
      cameraMake: payload.metadata.cameraMake,
      cameraModel: payload.metadata.cameraModel,
      software: payload.metadata.software,
      createdAt: payload.metadata.createdAt,
      orientation: payload.metadata.orientation,
      gpsPresent: payload.metadata.gpsPresent,
      interpretationEn: payload.metadata.interpretationEn,
      interpretationAr: payload.metadata.interpretationAr,
    },
    provenance: {
      status: payload.provenance.status as ImageProvenanceStatus,
      contentCredentialsPresent: payload.provenance.contentCredentialsPresent,
      manifestFound: payload.provenance.manifestFound,
      limitationEn: payload.provenance.limitationEn,
      limitationAr: payload.provenance.limitationAr,
    },
    forensics: payload.forensics.map((signal) => ({
      name: signal.name,
      value: signal.value,
      meaningEn: signal.meaningEn,
      doesNotMeanEn: signal.doesNotMeanEn,
    })),
    evidenceQuality: {
      longEdge: payload.evidenceQuality.longEdge,
      lowResolution: payload.evidenceQuality.lowResolution,
      warnings: payload.evidenceQuality.warnings.map((warning) => ({
        code: warning.code,
        severity: warning.severity,
        en: warning.en,
        ar: warning.ar,
      })),
    },
    safety: {
      fitForAutomatedEnforcement: payload.safety.fitForAutomatedEnforcement,
      status: payload.safety.status,
      advisoryOnly: payload.safety.advisoryOnly,
    },
  }

  return {
    isMock: false,
    source: 'live',
    engine: payload.model.modelName ?? 'BASIRAH Image',
    engineVersion: payload.model.modelVersion ?? 'unknown',
    signal: {
      kind: 'image',
      valueEn: payload.fileName,
      valueAr: payload.fileName,
    },
    // The canonical decision is authoritative. A research-grade detector
    // can never present trustScore=100 / "trusted" as the verdict for a
    // known-AI synthetic case. Trust score is authoritative for image
    // analysis — use 0 (not null) so the gauge renders "0/100" honestly
    // and runs the count-up for a genuine result, but is suppressed
    // entirely for uncertainty.
    trustScore: payload.assessment === 'uncertain' ? 0 : Math.round(payload.trustScore ?? 0),
    finalAssessment: payload.finalAssessment ?? null,
    riskLevel: toRiskLevel(payload.riskLevel),
    confidence: Math.round(payload.confidence),
    dna: {
      synthetic: p === null ? null : Math.round((1 - p) * 100),
      provenance: payload.provenance.status === 'verified' ? 100 : null,
      identity: null,
      domain: null,
      behavior: null,
    },
    graph: { nodes, edges },
    timeline: payload.timeline.map((event, index) => ({
      id: `image-stage-${index}`,
      stage: STAGE_MAP[event.stage] ?? 'acquire',
      offsetSeconds: Number((step * index).toFixed(3)),
    })),
    primarySignal: { titleEn, titleAr, bodyEn: headlineEn, bodyAr: headlineAr },
    secondarySignals: signals,
    imageDetail,
    lanes: ['synthetic_media', 'metadata', 'provenance'],
    durationMs: payload.durationMs,
  }
}

export class ApiImageAnalysisProvider implements AnalysisProvider {
  readonly name = 'api-image'
  readonly isMock = false

  supports(kind: SignalKind): boolean {
    return kind === 'image' || kind === 'screenshot'
  }

  async analyze(signal: Signal): Promise<AnalysisResult> {
    const file = signal.file
    if (!file) {
      throw new AnalysisError('No image file was attached to this signal.', 'no_file')
    }
    validateImageFile(file)

    // FormData goes to fetch WITHOUT an explicit Content-Type: the browser
    // must generate the multipart boundary itself. Setting it by hand
    // produces an unparsable body.
    const form = new FormData()
    form.append('file', file, file.name)

    let response: Response
    try {
      response = await fetch(`${resolveApiBase()}/api/analyze/image`, {
        method: 'POST',
        body: form,
      })
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
        if (typeof body.error === 'string') detail = body.error
        if (typeof body.code === 'string') code = body.code
      } catch {
        // Non-JSON error body; keep the status message.
      }
      throw new AnalysisError(detail, code)
    }

    const payload = (await response.json()) as ApiImageResponse
        // The signal's object URL is forwarded so the result panel can show
        // the image that was actually analysed. The investigation hook owns
        // and revokes that URL; no second upload and no second decode.
        return toImageAnalysisResult(payload, signal.previewUrl)
  }
}

export const apiImageAnalysisProvider = new ApiImageAnalysisProvider()
