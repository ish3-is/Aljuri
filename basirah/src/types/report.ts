import type { TranslationKey } from '../i18n/translations'
import type { ProjectMember } from '../data/projectMembers'

/* ============================================================
   REPORT DOCUMENT MODEL

   The report is a modality-NEUTRAL container. It knows nothing
   about images or URLs as such: it holds "the analysed item", "the
   assessment", "evidence", "metadata", "timeline", "model info",
   "limitations" and "safety", and each modality fills what it can
   measure and leaves the rest empty.

   This is what lets Phase 4 modalities (OCR, QR, files, encoded
   content) be added by writing ONE mapper, with no change to the
   report layout, the print stylesheet, the PDF flow or the Excel
   workbook. Every field below is therefore either:

     - measured by the pipeline and carried through, or
     - explicitly null / empty, which renders as "not measured".

   It is never filled with a plausible substitute. A QR analysis that
   measures no metadata reports no metadata row; it does not reuse
   the image metadata shape with blanks pretending to be values.
   ============================================================ */

/** Which kind of signal the report documents. */
export type ReportModality = 'image' | 'screenshot' | 'qr' | 'url' | 'text' | 'file'

/** One row of the Trust DNA table. `value` is null when unmeasured. */
export interface ReportDnaAxis {
  axis: 'synthetic' | 'identity' | 'domain' | 'provenance' | 'behavior'
  labelKey: TranslationKey
  /** 0-100, or null for "this axis does not apply to this modality". */
  value: number | null
}

/** One evidence item in the report's key-evidence section. */
export interface ReportEvidenceItem {
  id: string
  /** The finding, in the language it was produced in. */
  label: string
  detail: string
  /** Drives the printed classification; never colour alone. */
  polarity: 'risk' | 'neutral' | 'trust'
  weight: 'primary' | 'secondary'
}

/** One investigation stage, in the order it actually ran. */
export interface ReportTimelineItem {
  stage: string
  /** Offset from the start of the investigation, in seconds. */
  offsetSeconds: number
}

/** Metadata rows. Both languages, because the report renders in both. */
export interface ReportMetadataRow {
  labelKey: TranslationKey
  valueEn: string
  valueAr: string
}

/** Forensic / provenance rows, image modality only. */
export interface ReportForensicRow {
  name: string
  /** null when the characteristic could not be computed. */
  value: number | null
  meaningEn: string
  meaningAr: string
  doesNotMeanEn: string
  doesNotMeanAr: string
}

export interface ReportProvenanceRow {
  statusKey: TranslationKey
  statusEn: string
  statusAr: string
  limitationEn: string
  limitationAr: string
}

/** URL-modality-only signal rows. */
export interface ReportUrlSignalRow {
  labelKey: TranslationKey
  valueEn: string
  valueAr: string
  severity: 'trusted' | 'caution' | 'high_risk' | 'neutral'
}

export interface ReportModelInfo {
  /** Display name of the pipeline that produced this result. */
  engine: string
  engineVersion: string
  /** Research-grade / advisory / unavailable, verbatim from the model. */
  statusEn: string
  statusAr: string
  advisoryOnly: boolean
  fitForAutomatedEnforcement: boolean
  /** Prose limitation statements, rendered verbatim. */
  limitationsEn: string[]
  limitationsAr: string[]
}

/* ============================================================
   FACT / INFERENCE SEPARATION

   A report that mixes "we measured X" with "the model concluded Y"
   in one flowing list is how a probabilistic output becomes an
   apparent fact by the time it reaches a reader three paragraphs
   down. So the document carries FOUR separate buckets plus the
   fusion explanation, and the layout renders them as distinct
   sections rather than one undifferentiated evidence list.

     verifiedFacts      — measurements and observations. What the
                          pipeline READ. True regardless of which
                          model ran, and separable from any model.
     modelInferences    — probabilistic conclusions drawn from
                          those measurements. Advisory by nature.
     heuristicSignals   — weak structural indicators. They support;
                          they never decide.
     unavailableEvidence — what could NOT be established, stated as
                          plainly as what could. Absence is evidence
                          of nothing, and the report says so.
     limitations        — standing constraints on the whole run.

   Each item carries BOTH languages, because a fact stated in only
   one of them is a fact half-reported.
   ============================================================ */

/** Which epistemic bucket a report line belongs to. */
export type ReportClaimKind =
  | 'verifiedFact'
  | 'modelInference'
  | 'heuristicSignal'
  | 'unavailableEvidence'

export interface ReportClaim {
  id: string
  kind: ReportClaimKind
  /** Short label for the claim's subject. */
  labelEn: string
  labelAr: string
  /** The claim itself, in full sentences. */
  detailEn: string
  detailAr: string
  /**
   * Machine-readable source, e.g. "c2pa", "ensemble", "ocr".
   * Rendered LTR. Lets a reader trace a claim back to the module
   * that produced it without trusting the prose.
   */
  source: string
}

export interface ReportDocument {
  /**
   * Local reference such as BASIRAH-IMG-20261005-4F2A.
   *
   * This is NOT a cryptographic signature, certificate or legal
   * attestation, and the report says so on its face. It exists so a
   * reader can refer to one specific document unambiguously.
   */
  reportId: string
  createdAt: string
  modality: ReportModality
  /** What was analysed — a filename or a URL. Rendered LTR always. */
  inputSummary: string
  /** The one-paragraph executive summary. */
  overallAssessment: string
  /** Arabic rendering of the same summary, derived from the same result. */
  overallAssessmentAr: string
  /** Three-way classification where the modality has one. */
  assessment: string | null
  /** Arabic three-way classification, where one exists. */
  assessmentAr: string | null
  trust: number
  riskLevel: 'trusted' | 'caution' | 'high_risk'
  /**
   * The model's own confidence in the score, or null when the
   * pipeline produced no such figure.
   *
   * The evidence endpoint reports per-detector values and a composite
   * trust assessment but no single "confidence", so this is null for
   * those results. Zero is NOT the substitute: a printed "Model
   * confidence: 0" is a claim that the model had no confidence at
   * all, which is a different statement from "no confidence figure
   * was reported".
   */
  confidence: number | null
  dna: ReportDnaAxis[]
  evidence: ReportEvidenceItem[]
  metadata: ReportMetadataRow[]
  forensics: ReportForensicRow[]
  provenance: ReportProvenanceRow[]
  urlSignals: ReportUrlSignalRow[]
  timeline: ReportTimelineItem[]
  modelInfo: ReportModelInfo

  /* ---- Phase 3.7: the fact / inference split ---- */

  /** Everything bucketed by epistemic status, for the report layout. */
  claims: ReportClaim[]
  /** The backend's own note on how fusion ranked the evidence. */
  fusionExplanationEn: string
  fusionExplanationAr: string

  /** Standing safety statement. Advisory by construction. */
  safety: string
  team: ProjectMember[]
}