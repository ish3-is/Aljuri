/* ============================================================
   BASIRAH domain types

   These shapes describe the ANALYSIS CONTRACT, not the mock. A real
   backend (Phase 6) or an ML service (Phase 2-5) must be able to
   return this same structure for the UI to consume unchanged.
   ============================================================ */

import type { TranslationKey } from '../i18n/translations'

/**
 * What the user submitted through Universal Input.
 *
 * `file` is Phase 3.7: a non-image upload goes through the same
 * evidence endpoint as an image, but the file-intelligence branch
 * runs instead of the image branch.
 */
export type SignalKind = 'url' | 'image' | 'screenshot' | 'file' | 'qr' | 'text'

/** Lifecycle of one investigation. */
export type InvestigationState =
  | 'idle'
  | 'dragging'
  | 'input_received'
  | 'analyzing'
  | 'result'
  /** The analysis could not be completed. Never a fabricated result. */
  | 'error'

/** Risk classification — probabilistic bands, never a verdict. */
export type RiskLevel = 'trusted' | 'caution' | 'high_risk'

/** The five Trust DNA axes. Fixed set: the fingerprint is meaningless
    if dimensions change between investigations. */
export type DnaAxis = 'synthetic' | 'identity' | 'domain' | 'provenance' | 'behavior'

/**
 * One measured axis, 0-100.
 *
 * `null` means NOT APPLICABLE for this signal type — e.g. a plain URL has
 * no synthetic-media evidence and no content provenance, so those axes
 * carry no measurement at all. Phase 2 introduced this because inventing
 * a number for an axis nothing was measured on is exactly the kind of
 * fabricated intelligence the product exists to avoid.
 */
export type DnaValue = number | null

export type TrustDna = Record<DnaAxis, DnaValue>

/** Analysis branch selected by the intelligence layer. */
export type AnalysisLane =
  | 'url_intelligence'
  | 'synthetic_media'
  | 'metadata'
  | 'provenance'
  | 'identity'
  /** Cross-modal evidence fusion — every real modality runs it. */
  | 'fusion'

/** A single forensic record in the timeline. */
export interface TimelineEntry {
  id: string
  /** Machine-readable stage id; drives icons and lane grouping. */
  stage: TimelineStageId
  /** Seconds since the investigation began. */
  offsetSeconds: number
}

export type TimelineStageId =
  | 'acquire'
  | 'identify'
  | 'visual'
  | 'url'
  | 'metadata'
  | 'provenance'
  | 'synthetic'
  | 'correlate'
  | 'score'

/** One node in the evidence graph. */
export interface EvidenceNode {
  id: string
  labelEn: string
  labelAr: string
  /** Short explanation surfaced on hover/selection. */
  detailEn: string
  detailAr: string
  /** Visual weight: primary findings read heavier than supporting ones. */
  weight: 'primary' | 'secondary'
  /** Signal polarity. Drives node colour. */
  polarity: 'risk' | 'neutral' | 'trust'
  /** Layout position in the graph's own coordinate space (0-100). */
  x: number
  y: number
}

/** A directed relationship between two evidence nodes. */
export interface EvidenceEdge {
  from: string
  to: string
  /** Edge character: `asserts`, `contradicts`, or `derives`. */
  relation: 'asserts' | 'contradicts' | 'derives'
}

export interface EvidenceGraph {
  nodes: EvidenceNode[]
  edges: EvidenceEdge[]
}

/** A secondary finding in the explanation panel. */
export interface EvidenceSignal {
  id: string
  metricKey: TranslationKey
  /** Pre-formatted display value (e.g. "72%", "Unavailable"). */
  valueEn: string
  valueAr: string
  severity: RiskLevel | 'neutral'
}

/* ============================================================
   IMAGE DETAIL

   The image backend returns far more than the generic analysis
   contract carries: metadata, forensic signals, provenance state,
   evidence-quality warnings, model disclosure and safety flags.

   Rather than flattening all of that into `secondarySignals` — which
   is all the generic explanation rail can express — the image
   provider carries the raw subset on an OPTIONAL field. It is
   optional because the URL pipeline has no such payload, and absent
   on every mock result.

   Nothing here is re-derived by the UI: every value is passed
   through exactly as the backend measured it, including `null`,
   which the UI renders as N/A rather than as a number.
   ============================================================ */

/** Three-way classification. Never binary. */
export type ImageAssessment = 'likely_authentic' | 'uncertain' | 'likely_synthetic'

/** Honest provenance states. Never "C2PA verified" unless it is. */
export type ImageProvenanceStatus =
  | 'verified'
  | 'present_unverified'
  | 'invalid'
  | 'unavailable'

export interface ImageSyntheticDetail {
  /** P(synthetic), or null when the model could not run at all. */
  syntheticProbability: number | null
  authenticProbability: number | null
  /** True when the probability falls inside the uncertain band. */
  uncertain: boolean
  /** Decision thresholds derived from held-out validation. */
  uncertaintyLower: number
  uncertaintyUpper: number
}

export interface ImageModelDetail {
  modelName: string | null
  modelVersion: string | null
  available: boolean
  reason: string | null
  /** e.g. "research_grade" */
  status: string
  advisoryOnly: boolean
  fitForAutomatedEnforcement: boolean
  noticeEn: string
  noticeAr: string
  /** Prose limitation statements. Rendered verbatim. */
  knownLimitations: string[]
  trainedFamilies?: string[]
  evaluatedHeldOutFamily?: string
}

export interface ImageMetadataDetail {
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
  /** BOOLEAN ONLY. Coordinates are never shown. */
  gpsPresent: boolean
  interpretationEn: string
  interpretationAr: string
}

export interface ImageProvenanceDetail {
  status: ImageProvenanceStatus
  contentCredentialsPresent: boolean
  manifestFound: boolean
  limitationEn: string
  limitationAr: string
}

export interface ImageForensicSignal {
  /** Machine name, e.g. "compression_anomaly". */
  name: string
  /** The measurement, or null when it could not be computed. */
  value: number | null
  /** What the measurement establishes. */
  meaningEn: string
  /** What it explicitly does not establish. Always shown beside it. */
  doesNotMeanEn: string
}

export interface ImageQualityWarning {
  code: string
  /** "high" | "medium" | whatever the backend reports. */
  severity: string
  en: string
  ar: string
}

export interface ImageEvidenceQuality {
  longEdge: number
  lowResolution: boolean
  warnings: ImageQualityWarning[]
}

export interface ImageSafetyDetail {
  fitForAutomatedEnforcement: boolean
  status: string
  advisoryOnly: boolean
}

export interface ImageDetail {
  fileName: string
  fileSizeBytes: number
  /**
   * Object URL for the submitted file, carried through so the result
   * can show what was actually analysed without a second upload.
   */
  previewUrl?: string
  assessment: ImageAssessment
  synthetic: ImageSyntheticDetail
  model: ImageModelDetail
  metadata: ImageMetadataDetail
  provenance: ImageProvenanceDetail
  forensics: ImageForensicSignal[]
  evidenceQuality: ImageEvidenceQuality
  safety: ImageSafetyDetail
  /**
   * Evidence fusion / ensemble produced by the image pipeline, and the
   * derived states the result surface reads from. Used by the hero's
   * evidence-status row and detector-transparency panel.
   */
  ensemble?: DetectorEnsemble
  distributionStatus?: DistributionStatus
  detectorAgreement?: DetectorAgreement
}

/** The complete result payload — the boundary between mock and real. */
export interface AnalysisResult {
  /** True whenever the payload is simulated. Rendered as a badge. */
  isMock: boolean
  /** Provenance of the data, surfaced in the UI and in later API responses. */
  source: 'mock' | 'live'
  /** Model/service that produced the payload, once real services exist. */
  engine: string
  engineVersion: string
  /** What was analyzed, echoed back for the report header. */
  signal: {
    kind: SignalKind
    /** Display string: the URL, or the filename for image signals. */
    valueEn: string
    valueAr: string
  }
  /** 0-100. Higher = more trustworthy. */
  trustScore: number
  riskLevel: RiskLevel
  /**
   * Model confidence in the score itself, 0-100 — or null when the
   * pipeline published no such figure.
   *
   * Null rather than 0: a printed "Model confidence: 0" asserts that
   * the model had no confidence, which is a different claim from "no
   * confidence figure was reported".
   */
  confidence: number | null
  dna: TrustDna
  graph: EvidenceGraph
  timeline: TimelineEntry[]
  /** The final assessment string from the evidence fusion, for the
   *  legacy image stack (not the evidence path, which has its own
   *  authoritative assessment). */
  finalAssessment: string | null
  /** Evidence fusion / ensemble produced by the image pipeline, and the
   *  derived states the result surface reads from. */
  ensemble?: DetectorEnsemble
  distributionStatus?: DistributionStatus
  detectorAgreement?: DetectorAgreement
  /** The dominant finding, given narrative weight over the rest. */
  primarySignal: {
    titleEn: string
    titleAr: string
    bodyEn: string
    bodyAr: string
  } | null
  secondarySignals: EvidenceSignal[]
  /**
     * Raw image-pipeline payload, present only on image results.
     *
     * Optional by design: the URL pipeline has no equivalent payload and
     * mock results never fabricate one. Consumers must check for its
     * presence rather than assume an image analysis.
     */
    imageDetail?: ImageDetail
    /**
     * Which backend pipeline produced this result.
     *
     * Discriminates the three real providers — url, image, evidence —
     * from a mock, so a consumer can narrow to `EvidenceAnalysisResult`
     * without probing for optional fields.
     */
    analysisSource?: 'url' | 'image' | 'evidence'
  /** Which analysis lanes actually ran for this signal type. */
  lanes: AnalysisLane[]
  /** Wall-clock duration of the simulated analysis, in ms. */
  durationMs: number
}

/** Progressive stage emitted while the investigation runs. */
export interface AnalysisProgress {
  completed: number
  total: number
  activeStage: TimelineStageId | null
  lanes: AnalysisLane[]
}

/* ============================================================
   EVIDENCE ANALYSIS (Phase 3.7)

   The multimodal endpoint (`POST /api/analyze/evidence`) runs the
   whole chain in one pass and returns every modality's raw
   measurement side by side. The types below mirror that payload
   EXACTLY as the backend produces it.

   The single most important property of this block is that
   `syntheticLikelihood` is `number | null`, and that null means
   "the detectors conflicted and the decision was abstained". It is
   not a missing measurement and it is not zero. Nothing in the UI
   may substitute a value for it, and nothing may average
   per-detector probabilities: the two detectors are independent
   models whose disagreement is itself the finding.
   ============================================================ */

/** Which pipeline the backend actually ran for the upload. */
export type EvidenceMode = 'image' | 'screenshot' | 'file'

/**
 * How the two detectors relate.
 * `conflict` means they landed on opposite sides of the decision
 * margin — the ensemble then abstains and publishes no likelihood.
 */
export type DetectorAgreement =
  | 'strong_agreement'
  | 'moderate_agreement'
  | 'insufficient'
  | 'conflict'

export type EvidenceQualityLevel = 'high' | 'medium' | 'low'

export type DistributionStatus =
  | 'in_distribution'
  | 'borderline'
  | 'out_of_distribution'

/** C2PA states. `verified` requires a real signature check. */
export type C2paStatus =
  | 'verified'
  | 'present_unverified'
  | 'invalid'
  | 'unavailable'

/** One detector's own opinion. Never combined with another's. */
export interface DetectorVote {
  modelName: string
  architecture: string
  /** PER-DETECTOR synthetic probability, 0-1. */
  syntheticProbability: number
  status: 'available' | 'unavailable'
  unavailableReason: string | null
  limitations: string[]
}

export interface DetectorEnsemble {
  detectors: DetectorVote[]
  detectorAgreement: DetectorAgreement
  evidenceQuality: EvidenceQualityLevel
  distributionStatus: DistributionStatus
  /**
   * null on conflict, by design. The backend withholds the mean
   * rather than publish a reassuring midpoint for a total
   * disagreement. Rendering 0.5 here would be a lie.
   */
  syntheticLikelihood: number | null
  abstained: boolean
  abstentionReasons: string[]
  notes: string[]
  latencyMs: Record<string, number | null>
}

/**
 * Content Credentials.
 *
 * Note the deliberate absence of a `verified` convenience flag:
 * `status === 'verified'` is the only thing that may ever be called
 * verified, and only because the backend performed signature
 * validation to produce it.
 */
export interface EvidenceProvenance {
  status: C2paStatus
  standard: string | null
  manifestPresent: boolean
  /**
   * null, not false, when no manifest exists to validate.
   *
   * Verified against a live response: with status `unavailable` the
   * backend returns `signatureVerified: null`. That is a meaningfully
   * different fact from `false` — nothing was checked, as opposed to
   * something being checked and rejected — and the UI renders the
   * three states separately rather than collapsing null into "no".
   */
  signatureVerified: boolean | null
  signer: string | null
  issuer: string | null
  aiGeneratedAssertion: boolean | null
  aiEditedAssertion: boolean | null
  captureAssertion: boolean | null
  validationWarnings: string[]
  validationErrors: string[]
  /** Backend's own strength call, e.g. "none" / "moderate" / "strong". */
  evidenceStrength: string
  sdkAvailable: boolean
  notes: string[]
}

export interface OcrFinding {
  engine: string
  /** Every engine that ran, in order. A single-engine run is shown too. */
  enginesUsed: string[]
  text: string
  normalizedText: string
  /** null when the engine produced no confidence figure. */
  confidence: number | null
  containsArabic: boolean
  /** One entry per detected line, with its own box and confidence. */
  lines: Array<{
    text: string
    bbox: number[] | null
    confidence: number | null
  }>
  urls: UrlCandidate[]
  notes: string[]
}

export interface QrFinding {
  payload: string | null
  decodeStatus: string
  /** [x, y, w, h] when a symbol was located. */
  bbox: number[] | null
  attemptUsed: string | null
  isUrl: boolean
  notes: string[]
}

export interface UrlIntelligence {
  available: boolean
  reason?: string
  riskLevel?: string
  trustScore?: number
  confidence?: number
  modelStatus?: string
  note?: string
}

export interface UrlCandidate {
  rawExtractedText: string
  normalizedCandidate: string
  repairApplied: boolean
  repairNotes: string[]
  confidence: number
  /** "qr" | "ocr" | "file_text" — where in the chain it was found. */
  origin: string
  urlIntelligence: UrlIntelligence
}

export interface EncodingFinding {
  encodingType: string
  rawPreview: string
  decodedPreview: string
  confidence: number
  riskIndicators: string[]
  depth: number
}

/**
 * File-intelligence result for a non-image upload.
 *
 * `accepted: false` means the file was NOT analysed. That must never
 * be rendered as a clean result: the UI states the backend's own
 * `reason` and says the file was not inspected.
 */
export interface FileFinding {
  accepted: boolean
  fileKind: string
  reason: string | null
  sizeBytes: number
  textChars: number
  encodingGuess: string | null
  structure: Record<string, unknown>
  urls: string[]
  emails: string[]
  ips: string[]
  suspicious: string[]
  notes: string[]
  /**
   * Encoded payloads the file inspector found.
   *
   * An ARRAY of findings, not a single string: the file inspector
   * reports every encoding it recognised, and a file can easily
   * contain more than one. Verified against a live
   * `/api/analyze/evidence?mode=file` response, which returns the
   * same `EncodingFinding[]` shape as the top-level `encoding` list.
   */
  encodedPreview: EncodingFinding[] | null
}

export interface FusionFinding {
  tier: number
  source: string
  strength: string
  claim: string
  polarity: string
}

export interface EvidenceFusion {
  finalAssessment: string
  findings: FusionFinding[]
  evidenceHierarchy: string[]
  limitations: string[]
  note: string
}

/**
 * "Digital Trust Assessment" — the backend's own label for its score.
 *
 * `isAuthenticityProbability` is always false and `note` says why.
 * The UI must render the label it returns and must never rename it
 * to "Authenticity" or "Verified".
 */
export interface TrustAssessment {
  value: number
  components: Record<string, number>
  label: string
  isAuthenticityProbability: false
  authenticityVerified: boolean
  note: string
}

export interface EvidenceStageEvent {
  stage: string
  status: string
  detail: string
}

/**
 * Everything the evidence endpoint measured, carried through
 * untouched. Every field here is OPTIONAL because the pipeline is
 * modality-dependent: a text file has no QR symbol, a screenshot has
 * no file-intelligence block. Absence is rendered as "not measured",
 * never as a zero or an empty string.
 */
export interface EvidenceDetail {
  analysisType: 'evidence'
  /** Backend-resolved mode; may carry a contradiction note. */
  mode: string
  fileName: string
  fileSizeBytes: number

  image?: Record<string, unknown>
  /** null when the image pipeline failed; the reason is in `image`. */
  finalAssessment: string | null
  provenance: EvidenceProvenance | null
  ensemble: DetectorEnsemble | null
  trustAssessment: TrustAssessment | null
  metadata: Record<string, unknown> | null
  forensics: Array<Record<string, unknown>> | null
  evidenceQuality: Record<string, unknown> | null

  ocr: OcrFinding | null
  qr: QrFinding | null
  urls: UrlCandidate[]
  file: FileFinding | null
  encoding: EncodingFinding[]

  fusion: EvidenceFusion
  timeline: EvidenceStageEvent[]
  latencyMs: Record<string, number>
  limitations: string[]

  /** SHA-256 of the original uploaded bytes. Do not call it blockchain or notarization. */
  fingerprint: string
  /** Content coverage model (coveragePercent is not trust). */
  coverage: {
    imagePixels: number
    provenance: string
    ocr: string
    qr: string
    url: string
    encoding: string
    fileStructure: string
  }
  /** Report traceability references. */
  reportTraceability: string[]
}

/**
 * An analysis result produced by the multimodal evidence endpoint.
 *
 * This is the DISCRIMINATED form of the shared `AnalysisResult`: the
 * base contract is what every existing panel reads, and this narrows
 * it to say specifically that an `EvidenceDetail` is present and
 * authoritative. Consumers narrow with `isEvidenceResult` rather than
 * testing optional fields by hand.
 */
export interface EvidenceAnalysisResult extends AnalysisResult {
  analysisSource: 'evidence'
  evidence: EvidenceDetail
  /** Phase 4 content coverage model. Coverage is not trust. */
  coverage?: {
    imagePixels: number
    provenance: string
    ocr: string
    qr: string
    url: string
    encoding: string
    fileStructure: string
    forensicSignals: number
    totalEntities: number
  }
  /** Final assessment from the backend fusion (evidence pipeline only). */
  finalAssessment: string | null
}

/** True when a result carries an evidence-pipeline payload. */
export function isEvidenceResult(
  result: AnalysisResult,
): result is EvidenceAnalysisResult {
  return (
    result.analysisSource === 'evidence' &&
    (result as Partial<EvidenceAnalysisResult>).evidence !== undefined
  )
}