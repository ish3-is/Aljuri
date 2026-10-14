import { AlertTriangle, ShieldAlert } from 'lucide-react'
import { useI18n } from '../../i18n/useI18n'
import type {
  DetectorEnsemble,
  DetectorVote,
  EncodingFinding,
  EvidenceDetail,
  EvidenceProvenance,
  FileFinding,
  OcrFinding,
  QrFinding,
  TrustAssessment,
  UrlCandidate,
} from '../../types/analysis'
import { cn } from '../../lib/utils'
import {
  DidNotRun,
  FieldRow,
  NoteBlock,
  ResultSection,
  StatBlock,
} from './resultPrimitives'
import { TimelineView, buildTimelineEntries } from './TimelineView'

/* ============================================================
   PROVENANCE-FIRST RESULT VIEW

   The reading order below is a deliberate product decision and it
   is not the one a score-first dashboard would choose:

     1. Final Assessment          the conclusion, in words
     2. Provenance                the only cryptographic evidence
     3. Detector Agreement        did the models agree at all
     4. Evidence Quality          how much this can support
     5. Distribution / OOD        is this material familiar
     6. Analysis Coverage         what actually ran
     7. Synthetic Evidence        per-detector, separately
     8. OCR / QR / URL / Encoding what was read out
     9. Metadata / Forensics      file-level characteristics
    10. Limitations               what none of the above establishes
    11. Digital Trust Assessment  a small secondary card

   The trust assessment is LAST and small on purpose. It is a
   composite of agreement, quality, familiarity and provenance — not
   a probability that the content is authentic, and it is explicitly
   not an authenticity probability. Leading with it would let a single
   number outrank the cryptographic evidence and the abstention that
   the reader most needs to see.

   NOTHING here computes a score, a threshold or a verdict. Every
   number, word and band is read straight off the backend payload.
   ============================================================ */

export interface EvidenceResultViewProps {
  evidence: EvidenceDetail
}

/* ------------------------------------------------------------------ */
/* Assessment vocabulary                                               */
/* ------------------------------------------------------------------ */

/**
 * Allowed wordings, and only these.
 *
 * The enum the backend returns is mapped to the approved vocabulary
 * rather than displayed raw, because an unmapped passthrough would
 * put whatever the pipeline happens to call it into the UI. There is
 * deliberately NO mapping to "authentic", "verified" or "real": no
 * non-provenance finding can support that claim.
 */
function useAssessment() {
  const { t } = useI18n()

  return (value: string | null) => {
    switch (value) {
      case 'likely_synthetic':
        return {
          label: t('result.assessmentLikelySynthetic'),
          tone: 'danger' as const,
        }
      case 'uncertain':
        return {
          label: t('result.assessmentUncertain'),
          tone: 'caution' as const,
        }
      case 'no_strong_synthetic_indicators':
        return {
          label: t('result.assessmentNoStrong'),
          tone: 'default' as const,
        }
      case 'provenance_verified':
        return {
          label: t('result.assessmentProvenanceVerified'),
          tone: 'trust' as const,
        }
      case 'provenance_unavailable':
        return {
          label: t('result.assessmentProvenanceUnavailable'),
          tone: 'caution' as const,
        }
      default:
        // An unmapped value is shown as itself, never upgraded.
        return { label: value ?? '—', tone: 'default' as const }
    }
  }
}

/* ------------------------------------------------------------------ */
/* 1. Final Assessment                                                 */
/* ------------------------------------------------------------------ */

function FinalAssessment({ evidence }: { evidence: EvidenceDetail }) {
  const { t } = useI18n()
  const assessment = useAssessment()

  // The fusion verdict is authoritative; the image branch's own
  // assessment is a fallback for the rare payload where the fusion
  // layer returned nothing.
  const value = evidence.fusion?.finalAssessment ?? evidence.finalAssessment
  const { label, tone } = assessment(value)

  const colour =
    tone === 'danger'
      ? 'text-danger'
      : tone === 'caution'
        ? 'text-caution'
        : tone === 'trust'
          ? 'text-trusted'
          : 'text-text'

  return (
    <ResultSection
      index="01"
      title={t('result.finalAssessment')}
      subtitle={t('result.finalAssessmentSub')}
      className="border-signal/25 bg-signal/[0.04]"
    >
      <p className={cn('font-arabic-display text-2xl leading-snug sm:text-3xl', colour)}>
        {label}
      </p>

      {evidence.fusion?.note && (
        <p className="font-arabic-body mt-4 max-w-3xl text-[0.8rem] leading-relaxed text-text-muted">
          {evidence.fusion.note}
        </p>
      )}

      {/* ---- The findings the fusion actually used, in tier order ----
          A conclusion with no visible basis is the failure mode this
          product exists to prevent, so the basis is never hidden
          behind a summary line. */}
      {evidence.fusion?.findings && evidence.fusion.findings.length > 0 && (
        <div className="mt-6">
          <p className="mono-label mb-2.5 text-text-dim">
            {t('result.fusionFindings')}
          </p>
          <ul className="space-y-2">
            {evidence.fusion.findings.map((finding, index) => (
              <li
                key={`${finding.tier}-${finding.source}-${index}`}
                className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b border-line/40 pb-2 last:border-b-0 last:pb-0"
              >
                <span className="mono-label text-signal/70">
                  {t('result.tier')} {finding.tier}
                </span>
                <span className="mono-label text-text-dim/70">
                  {finding.strength.replace(/_/g, ' ')} · {finding.polarity}
                </span>
                <span className="font-arabic-body basis-full text-[0.78rem] leading-relaxed text-text-muted">
                  {finding.claim}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* The tier order itself, so "why this and not that" is legible. */}
      {evidence.fusion?.evidenceHierarchy && evidence.fusion.evidenceHierarchy.length > 0 && (
        <div className="mt-6">
          <p className="mono-label mb-2.5 text-text-dim">
            {t('result.fusionHierarchy')}
          </p>
          <ol className="flex flex-wrap items-center gap-2">
            {evidence.fusion.evidenceHierarchy.map((tier, index) => (
              <li key={tier} className="flex items-center gap-2">
                <span className="font-arabic-body rounded-full border border-line/70 px-3 py-1 text-[0.7rem] text-text-muted">
                  {tier.replace(/_/g, ' ')}
                </span>
                {index < evidence.fusion.evidenceHierarchy.length - 1 && (
                  <span aria-hidden className="text-text-dim/50">
                    ›
                  </span>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}
    </ResultSection>
  )
}

/* ------------------------------------------------------------------ */
/* 2. Provenance                                                      */
/* ------------------------------------------------------------------ */

/**
 * Content Credentials.
 *
 * Two sentences here are non-negotiable copy and are always shown
 * when status is `unavailable`:
 *
 *   "No verifiable Content Credentials were found."
 *   "The absence of Content Credentials does not prove that the
 *    content is authentic or synthetic."
 *
 * The second sentence is the one that matters. Most real images —
 * including genuine photographs shared through messaging apps — carry
 * no provenance data at all, so "none found" is the common case. If
 * that silence could be read as reassurance, the platform would be
 * handing out free trust it never earned.
 *
 * The module is labelled LIMITED in its own header, because it can
 * locate a manifest and attempt signature validation but is not a
 * full trust-list implementation.
 */
function ProvenancePanel({ provenance }: { provenance: EvidenceProvenance | null }) {
  const { t } = useI18n()

  if (!provenance) {
    return (
      <ResultSection index="02" title={t('result.prov.title')}>
        <DidNotRun />
      </ResultSection>
    )
  }

  const STATUS_KEY = {
    verified: 'result.prov.statusVerified',
    present_unverified: 'result.prov.statusPresentUnverified',
    invalid: 'result.prov.statusInvalid',
    unavailable: 'result.prov.statusUnavailable',
  } as const

  const unavailable = provenance.status === 'unavailable'

  const assertion = (value: boolean | null) =>
    value === null
      ? t('result.notMeasured')
      : value
        ? t('result.prov.asserted')
        : t('result.prov.notAsserted')

  return (
    <ResultSection
      index="02"
      title={t('result.prov.title')}
      subtitle={t('result.prov.sub')}
    >
      <div className="mb-5 flex flex-wrap items-center gap-2.5">
        <span className="font-arabic-body inline-flex items-center gap-1.5 rounded-full border border-caution/30 bg-caution/10 px-3 py-1 text-[0.68rem] text-caution">
          {t('result.prov.moduleLabel')}: {t('result.prov.moduleLimited')}
        </span>
        <span className="font-arabic-body inline-flex items-center gap-1.5 rounded-full border border-line-bright px-3 py-1 text-[0.68rem] text-text-muted">
          {t(STATUS_KEY[provenance.status])}
        </span>
      </div>

      <dl>
        <FieldRow label={t('result.prov.status')} value={t(STATUS_KEY[provenance.status])} />
        <FieldRow
          label={t('result.prov.standard')}
          value={provenance.standard ?? t('result.notMeasured')}
          latin
        />
        <FieldRow
          label={t('result.prov.manifest')}
          value={provenance.manifestPresent ? t('common.yes') : t('common.no')}
        />
        {/* Signature verification has THREE states, not two: null
            means no manifest existed to check, which is a different
            fact from a manifest being checked and rejected. */}
        <FieldRow
          label={t('result.prov.signature')}
          value={
            provenance.signatureVerified === null
              ? t('result.notMeasured')
              : provenance.signatureVerified
                ? t('common.yes')
                : t('common.no')
          }
          tone={provenance.signatureVerified === true ? 'trust' : 'default'}
        />
        <FieldRow
          label={t('result.prov.evidenceStrength')}
          value={provenance.evidenceStrength.replace(/_/g, ' ')}
          latin
        />
        <FieldRow
          label={t('result.prov.signer')}
          value={provenance.signer ?? t('result.notMeasured')}
          latin
          wrap
        />
        <FieldRow
          label={t('result.prov.issuer')}
          value={provenance.issuer ?? t('result.notMeasured')}
          latin
          wrap
        />
        <FieldRow
          label={t('result.prov.aiGenerated')}
          value={assertion(provenance.aiGeneratedAssertion)}
          tone={provenance.aiGeneratedAssertion === true ? 'caution' : 'default'}
        />
        <FieldRow
          label={t('result.prov.aiEdited')}
          value={assertion(provenance.aiEditedAssertion)}
        />
        <FieldRow
          label={t('result.prov.capture')}
          value={assertion(provenance.captureAssertion)}
        />
      </dl>

      {/* ---- Validation warnings ----
          Rendered verbatim from the pipeline. These are the
          validator's own complaints about the manifest, so they are
          never paraphrased into something more or less alarming. */}
      {provenance.validationWarnings.length > 0 && (
        <div className="mt-5">
          <p className="mono-label mb-2 text-text-dim">
            {t('result.prov.validationWarnings')}
          </p>
          <ul className="space-y-1.5">
            {provenance.validationWarnings.map((warning, index) => (
              <li
                key={index}
                className="font-arabic-body border-s border-caution/40 ps-3 text-[0.74rem] leading-relaxed text-caution"
              >
                {warning}
              </li>
            ))}
          </ul>
        </div>
      )}

      {provenance.validationErrors.length > 0 && (
        <div className="mt-4">
          <p className="mono-label mb-2 text-text-dim">
            {t('result.prov.validationErrors')}
          </p>
          <ul className="space-y-1.5">
            {provenance.validationErrors.map((err, index) => (
              <li
                key={index}
                className="font-arabic-body border-s border-danger/40 ps-3 text-[0.74rem] leading-relaxed text-danger"
              >
                {err}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ---- The two mandatory sentences ---- */}
      {unavailable && (
        <div className="mt-5 space-y-2">
          <NoteBlock tone="caution">{t('result.prov.noCredentials')}</NoteBlock>
          <NoteBlock tone="neutral">{t('result.prov.absenceNote')}</NoteBlock>
        </div>
      )}

      {provenance.notes.length > 0 && (
        <div className="mt-5">
          <p className="mono-label mb-2 text-text-dim">{t('result.notes')}</p>
          <ul className="space-y-1.5">
            {provenance.notes.map((note, index) => (
              <li
                key={index}
                className="font-arabic-body text-[0.74rem] leading-relaxed text-text-muted"
              >
                · {note}
              </li>
            ))}
          </ul>
        </div>
      )}
    </ResultSection>
  )
}

/* ------------------------------------------------------------------ */
/* 3. Detector conflict — the most important block on the page         */
/* ------------------------------------------------------------------ */

/**
 * The conflict state.
 *
 * When the two detectors land on opposite sides of the decision
 * margin, the honest answer is "the detectors do not agree" — not a
 * midpoint. A mean of 0.91 and 0.09 is 0.50, which reads as a calm
 * neutral result and would let a reader treat a total disagreement as
 * mild uncertainty. The backend therefore withholds the likelihood
 * entirely, and this block makes that withholding visible rather than
 * leaving an empty space the reader fills in themselves.
 *
 * It states:
 *   · the conflict itself, prominently
 *   · the final assessment as UNCERTAIN
 *   · both detectors, each with its own value, side by side
 *   · "Decision: Abstained"
 * and shows NO combined figure anywhere.
 */
function DetectorConflict({ ensemble }: { ensemble: DetectorEnsemble }) {
  const { t } = useI18n()

  return (
    <div
      role="alert"
      data-testid="detector-conflict"
      className="rounded-lg border-2 border-danger/40 bg-danger/[0.06] p-5 sm:p-6"
    >
      <div className="flex items-start gap-3">
        <ShieldAlert size={20} className="mt-0.5 shrink-0 text-danger" />
        <div className="min-w-0">
          <p className="mono-label text-danger" dir="ltr">
            {t('result.conflict')}
          </p>
          <p className="font-arabic-body mt-2 text-[0.82rem] leading-relaxed text-text">
            {t('result.conflictSub')}
          </p>
          <p className="font-arabic-body mt-2 text-[0.78rem] leading-relaxed text-caution">
            {t('result.conflictNoLikelihood')}
          </p>
        </div>
      </div>

      {/* ---- Each detector, its own value, no combination ---- */}
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {ensemble.detectors.map((detector, index) => (
          <DetectorCard key={detector.modelName + index} detector={detector} />
        ))}
      </div>

      <div className="mt-5 space-y-2">
        <NoteBlock tone="caution">
          {t('result.finalAssessment')}: {t('result.assessmentUncertain')}
        </NoteBlock>
        <NoteBlock tone="danger">{t('result.decisionAbstained')}</NoteBlock>
      </div>

      {ensemble.abstentionReasons.length > 0 && (
        <div className="mt-4">
          <p className="mono-label mb-2 text-text-dim">
            {t('result.abstentionReasons')}
          </p>
          <ul className="flex flex-wrap gap-2">
            {ensemble.abstentionReasons.map((reason) => (
              <li
                key={reason}
                className="ltr-embed rounded-full border border-line-bright px-2.5 py-1 text-[0.68rem] text-text-muted"
              >
                {reason.replace(/_/g, ' ')}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Per-detector card                                                  */
/* ------------------------------------------------------------------ */

/**
 * One detector's own reading.
 *
 * Each card is a separate measurement. The two are NEVER merged into
 * one number on this card, and there is no "combined" row anywhere —
 * the backend's `syntheticLikelihood` is only rendered when it
 * actually published one, which by construction excludes conflicts.
 */
function DetectorCard({ detector }: { detector: DetectorVote }) {
  const { t } = useI18n()
  const unavailable = detector.status !== 'available'

  return (
    <div className="rounded-md border border-line/70 bg-surface-inset/50 p-4">
      <p className="ltr-embed text-[0.8rem] break-words text-text" dir="ltr">
        {detector.modelName}
      </p>
      <p className="mono-label mt-1 text-text-dim/70" dir="ltr">
        {detector.architecture}
      </p>

      <div className="mt-3 flex items-baseline justify-between gap-3">
        <span className="text-[0.72rem] text-text-dim">
          {t('result.valueLabel')}
        </span>
        {unavailable ? (
          <span className="font-arabic-body text-[0.78rem] text-text-dim">
            {detector.unavailableReason ?? t('result.abstain')}
          </span>
        ) : (
          <span className="ltr-embed text-[1.05rem] text-signal" dir="ltr">
            {(detector.syntheticProbability * 100).toFixed(1)}%
          </span>
        )}
      </div>

      {detector.limitations.length > 0 && (
        <ul className="mt-3 space-y-1">
          {detector.limitations.map((limitation, index) => (
            <li
              key={index}
              className="font-arabic-body text-[0.68rem] leading-relaxed text-text-dim"
            >
              · {limitation}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* 3b. Agreement / quality / distribution                             */
/* ------------------------------------------------------------------ */

function AgreementQualityDistribution({ ensemble }: { ensemble: DetectorEnsemble }) {
  const { t } = useI18n()

  const AGREEMENT_KEY = {
    strong_agreement: 'result.agreement.strong',
    moderate_agreement: 'result.agreement.moderate',
    conflict: 'result.agreement.conflict',
    insufficient: 'result.agreement.insufficient',
  } as const

  const QUALITY_KEY = {
    high: 'result.quality.high',
    medium: 'result.quality.medium',
    low: 'result.quality.low',
  } as const

  const DISTRIBUTION_KEY = {
    in_distribution: 'result.distributionStatus.in_distribution',
    borderline: 'result.distributionStatus.borderline',
    out_of_distribution: 'result.distributionStatus.out_of_distribution',
  } as const

  const outOfDistribution = ensemble.distributionStatus === 'out_of_distribution'

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <ResultSection
        index="03"
        title={t('result.detectorAgreement')}
        subtitle={t('result.detectorAgreementSub')}
      >
        <StatBlock
          label={t('result.detectorAgreement')}
          value={t(AGREEMENT_KEY[ensemble.detectorAgreement])}
          latin={false}
          tone={
            ensemble.detectorAgreement === 'strong_agreement'
              ? 'trust'
              : ensemble.detectorAgreement === 'conflict'
                ? 'risk'
                : 'caution'
          }
          hint={t('result.perDetector')}
        />
      </ResultSection>

      <ResultSection
        index="04"
        title={t('result.evidenceQuality')}
        subtitle={t('result.evidenceQualitySub')}
      >
        <StatBlock
          label={t('result.evidenceQuality')}
          value={t(QUALITY_KEY[ensemble.evidenceQuality])}
          latin={false}
          tone={ensemble.evidenceQuality === 'low' ? 'caution' : 'default'}
        />
      </ResultSection>

      <ResultSection
        index="05"
        title={t('result.distribution')}
        subtitle={t('result.distributionSub')}
      >
        <StatBlock
          label={t('result.distribution')}
          value={t(DISTRIBUTION_KEY[ensemble.distributionStatus])}
          latin={false}
          tone={outOfDistribution ? 'caution' : 'default'}
        />
        {outOfDistribution && (
          <NoteBlock tone="caution" className="mt-3">
            {t('result.ood.warning')}
          </NoteBlock>
        )}
      </ResultSection>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* 4. Analysis coverage                                               */
/* ------------------------------------------------------------------ */

/**
 * Which branches actually ran.
 *
 * This exists because "we found nothing" and "we looked for nothing"
 * must never be confused. Every branch in the pipeline is listed with
 * an explicit ran / did-not-run state, so a reader can see the shape
 * of the coverage before reading any finding from it.
 */
const COVERAGE_BRANCHES = [
  { key: 'image', labelKey: 'chain.stepScreenshot' },
  { key: 'ocr', labelKey: 'result.ocr' },
  { key: 'qr', labelKey: 'result.qr' },
  { key: 'urls', labelKey: 'result.urls' },
  { key: 'encoding', labelKey: 'result.encoding' },
  { key: 'file', labelKey: 'result.fileKind' },
  { key: 'provenance', labelKey: 'result.prov.title' },
] as const

function AnalysisCoverage({ evidence }: { evidence: EvidenceDetail }) {
  const { t } = useI18n()

  /**
   * OCR counts as "ran" only when an ENGINE ran.
   *
   * The backend returns an OCR block even when no engine is
   * installed (`engine: "none"`, empty `enginesUsed`, empty text), so
   * testing for the block's presence would report coverage the
   * pipeline does not have. Coverage means a measurement was taken.
   */
  const ran: Record<string, boolean> = {
    image: evidence.ensemble !== null,
    ocr: evidence.ocr !== null && evidence.ocr.enginesUsed.length > 0,
    // QR: a null payload IS a measurement — the decoder ran and
    // reported no symbol, which the QR panel states as a verified
    // fact. So presence of the block is the right test here, unlike
    // OCR above where an engine-less block measured nothing.
    qr: evidence.qr !== null,
    urls: evidence.urls.length > 0,
    encoding: evidence.encoding.length > 0,
    file: evidence.file !== null,
    provenance: evidence.provenance !== null,
  }

  return (
    <ResultSection
      index="06"
      title={t('result.coverage')}
      subtitle={t('result.coverageSub')}
    >
      <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {COVERAGE_BRANCHES.map((branch) => (
          <li
            key={branch.key}
            className="flex items-center justify-between gap-3 rounded-md border border-line/60 bg-surface-inset/40 px-3.5 py-2.5"
          >
            <span className="font-arabic-body text-[0.74rem] text-text-muted">
              {t(branch.labelKey)}
            </span>
            <span
              className={cn(
                'font-arabic-body text-[0.68rem]',
                ran[branch.key] ? 'text-trusted' : 'text-text-dim',
              )}
            >
              {ran[branch.key] ? t('result.coverageYes') : t('result.coverageNo')}
            </span>
          </li>
        ))}
      </ul>
    </ResultSection>
  )
}

/* ------------------------------------------------------------------ */
/* 5. Synthetic evidence — per detector, never merged                  */
/* ------------------------------------------------------------------ */

function SyntheticEvidence({ ensemble }: { ensemble: DetectorEnsemble }) {
  const { t } = useI18n()
  const conflict = ensemble.detectorAgreement === 'conflict'

  return (
    <ResultSection
      index="07"
      title={t('result.synthetic')}
      subtitle={t('result.syntheticSub')}
      className={conflict ? 'border-danger/30' : undefined}
    >
      {/*
        The combined figure is rendered only when the backend actually
        published one. On conflict it is null BY DESIGN — averaging a
        disagreement would launder a total conflict into a calm
        midpoint — so nothing is shown in its place.
      */}
      {ensemble.syntheticLikelihood !== null ? (
        <div className="mb-5">
          <StatBlock
            label={t('result.syntheticLikelihood')}
            value={`${(ensemble.syntheticLikelihood * 100).toFixed(1)}%`}
            tone={ensemble.syntheticLikelihood >= 0.5 ? 'risk' : 'trust'}
          />
        </div>
      ) : (
        <NoteBlock tone="caution" className="mb-5">
          {/* Deliberately distinct from "unavailable": this is an
              abstention, not a missing measurement. */}
          {conflict ? t('result.conflictNoLikelihood') : t('result.abstain')}
        </NoteBlock>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {ensemble.detectors.map((detector, index) => (
          <DetectorCard key={detector.modelName + index} detector={detector} />
        ))}
      </div>

      {ensemble.notes.length > 0 && (
        <div className="mt-5">
          <p className="mono-label mb-2 text-text-dim">{t('result.notes')}</p>
          <ul className="space-y-1.5">
            {ensemble.notes.map((note, index) => (
              <li
                key={index}
                className="font-arabic-body text-[0.74rem] leading-relaxed text-text-muted"
              >
                · {note}
              </li>
            ))}
          </ul>
        </div>
      )}
    </ResultSection>
  )
}

/* ------------------------------------------------------------------ */
/* 6. Screenshot chain                                                */
/* ------------------------------------------------------------------ */

/**
 * Is this upload an image (as opposed to a file)?
 *
 * `mode` can carry a backend annotation — e.g.
 * "screenshot (requested 'file' contradicted the content)" — because
 * the backend reports a contradiction rather than silently obeying.
 * The prefix test handles that without discarding the annotation.
 */
function isImagePipeline(mode: string): boolean {
  const resolved = mode.split(' ')[0]
  return resolved === 'image' || resolved === 'screenshot'
}

/**
 * The screenshot chain, rendered as an explicit sequence.
 *
 * The point of this block is not the arrows — it is the three
 * INDEPENDENT findings at the bottom. On a screenshot the image
 * detectors and the URL evidence routinely disagree: the pixels look
 * fine while a QR code or an on-screen link points somewhere
 * dangerous. Showing one reconciled number would hide exactly the
 * disagreement a reviewer needs.
 *
 * So when they differ, this panel prints three separate lines:
 *
 *   Image detectors: Abstained
 *   URL evidence: High Risk
 *   Final assessment: Likely Synthetic
 *
 * The final assessment is NOT presented as a compromise between them.
 */
export function ScreenshotChain({ evidence }: { evidence: EvidenceDetail }) {
  const { t } = useI18n()
  const assessment = useAssessment()

  const ensemble = evidence.ensemble
  const highRiskUrl = evidence.urls.find(
    (url) => url.urlIntelligence.riskLevel === 'high_risk',
  )

  const imageDetectorsLine = ensemble
    ? ensemble.abstained
      ? t('result.abstained')
      : `${t('result.coverageYes')} · ${t(`result.agreement.${ensemble.detectorAgreement === 'strong_agreement' ? 'strong' : ensemble.detectorAgreement === 'moderate_agreement' ? 'moderate' : 'insufficient'}`)}`
    : t('result.coverageNo')

  const urlEvidenceLine = highRiskUrl
    ? t('result.urlHighRisk')
    : evidence.urls.length > 0
      ? t('result.coverageYes')
      : t('result.coverageNo')

  const finalValue = evidence.fusion?.finalAssessment ?? evidence.finalAssessment
  const finalLine = assessment(finalValue).label

  // The three lines disagreeing is the interesting case, so the block
  // only claims to be a reconciliation when there is nothing to
  // reconcile.
  const diverging =
    Boolean(highRiskUrl) && Boolean(ensemble?.abstained)

  const steps = [
    { key: 'shot', label: t('chain.stepScreenshot'), ran: true },
    { key: 'ocr', label: t('chain.stepOcr'), ran: evidence.ocr !== null },
    { key: 'qr', label: t('chain.stepQr'), ran: evidence.qr !== null },
    {
      key: 'extract',
      label: t('chain.stepUrlExtract'),
      ran: evidence.urls.length > 0,
    },
    {
      key: 'intel',
      label: t('chain.stepUrlIntel'),
      ran: evidence.urls.length > 0,
    },
    { key: 'fusion', label: t('chain.stepFusion'), ran: true },
  ]

  return (
    <ResultSection
      index="S1"
      title={t('result.chain')}
      subtitle={t('result.chainSub')}
    >
      <ol className="flex flex-wrap items-center gap-x-2 gap-y-2">
        {steps.map((step, index) => (
          <li key={step.key} className="flex items-center gap-2">
            <span
              className={cn(
                'font-arabic-body rounded-full border px-3 py-1 text-[0.7rem]',
                step.ran
                  ? 'border-signal/30 bg-signal/[0.06] text-signal'
                  : 'border-line-bright text-text-dim',
              )}
            >
              {step.label}
            </span>
            {index < steps.length - 1 && (
              <span aria-hidden className="text-text-dim/50">
                →
              </span>
            )}
          </li>
        ))}
      </ol>

      {diverging && (
        <NoteBlock tone="caution" className="mt-5">
          {t('chain.independentLinesSub')}
        </NoteBlock>
      )}

      <div className="mt-5">
        <p className="mono-label mb-2.5 text-text-dim">
          {t('chain.independentLines')}
        </p>
        <dl>
          <FieldRow
            label={t('chain.imageDetectors')}
            value={imageDetectorsLine}
            latin={false}
            tone={ensemble?.abstained ? 'caution' : 'default'}
          />
          <FieldRow
            label={t('chain.urlEvidence')}
            value={urlEvidenceLine}
            latin={false}
            tone={highRiskUrl ? 'risk' : 'default'}
          />
          <FieldRow
            label={t('chain.finalAssessmentLine')}
            value={finalLine}
            latin={false}
            tone={
              finalValue === 'likely_synthetic'
                ? 'risk'
                : finalValue === 'uncertain'
                  ? 'caution'
                  : 'default'
            }
          />
        </dl>
      </div>
    </ResultSection>
  )
}

/* ------------------------------------------------------------------ */
/* 7. OCR                                                              */
/* ------------------------------------------------------------------ */

function OcrPanel({ ocr }: { ocr: OcrFinding | null }) {
  const { t } = useI18n()

  if (!ocr) {
    return (
      <ResultSection index="08" title={t('result.ocr')}>
        <DidNotRun />
      </ResultSection>
    )
  }

  return (
    <ResultSection index="08" title={t('result.ocr')}>
      <dl>
        {/* Every engine that ran is named. A single-engine run is
            shown as a single engine rather than implied to be a
            consensus of several. */}
        <FieldRow
          label={t('result.ocrEngine')}
          // An engine-less run is reported as such rather than as
          // the word "none" standing in for an engine name, which
          // reads like a real engine called "none".
          value={
            ocr.enginesUsed.length > 0
              ? ocr.enginesUsed.join(', ')
              : ocr.engine === 'none'
                ? t('result.abstain')
                : ocr.engine
          }
          latin={ocr.enginesUsed.length > 0 || ocr.engine !== 'none'}
          wrap
        />
        <FieldRow
          label={t('result.ocrConfidence')}
          value={ocr.confidence === null ? t('result.notMeasured') : ocr.confidence.toFixed(2)}
        />
        <FieldRow
          label={t('result.ocrArabic')}
          value={ocr.containsArabic ? t('common.yes') : t('common.no')}
        />
      </dl>

      {/*
        The extracted text is the one place in the result page where
        attacker-controlled content is rendered verbatim. It is marked
        as such, kept in a scrollable block so a wall of text cannot
        push every other panel below the fold, and forced LTR-isolated
        so an Arabic screenshot's text does not reorder against the
        Arabic interface around it.
      */}
      <div className="mt-5">
        <p className="mono-label mb-2 text-text-dim">{t('result.ocrText')}</p>
        {ocr.text ? (
          <pre
            dir="auto"
            className="bidi-auto max-h-[220px] overflow-auto rounded-md border border-line/60 bg-surface-inset/50 p-3.5 text-[0.74rem] leading-relaxed text-text-muted"
          >
            {ocr.text}
          </pre>
        ) : (
          <NoteBlock>{t('result.ocrNoText')}</NoteBlock>
        )}
      </div>

      {ocr.lines.length > 0 && (
        <div className="mt-4">
          <p className="mono-label mb-2 text-text-dim">
            {t('image.forensics.observedLabel')} ({ocr.lines.length})
          </p>
          <ul className="max-h-[160px] space-y-1 overflow-auto">
            {ocr.lines.map((line, index) => (
              <li
                key={index}
                dir="auto"
                className="font-arabic-body flex items-baseline justify-between gap-3 text-[0.72rem] leading-relaxed text-text-dim"
              >
                <span className="min-w-0 break-words">{line.text}</span>
                {line.confidence !== null && (
                  <span className="ltr-embed shrink-0 text-[0.66rem] text-text-dim/70" dir="ltr">
                    {line.confidence.toFixed(2)}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/*
        The Arabic limitation is stated unconditionally, not only when
        Arabic was detected: a reader who did NOT get Arabic text out
        of an Arabic screenshot needs to know why, and the reason is a
        known engine weakness rather than an absence of content.
      */}
      <NoteBlock tone="caution" className="mt-4">
        {t('result.ocrArabicLimitation')}
      </NoteBlock>

      {ocr.notes.length > 0 && (
        <div className="mt-4">
          <p className="mono-label mb-2 text-text-dim">{t('result.notes')}</p>
          <ul className="space-y-1">
            {ocr.notes.map((note, index) => (
              <li
                key={index}
                className="font-arabic-body text-[0.72rem] leading-relaxed text-text-dim"
              >
                · {note}
              </li>
            ))}
          </ul>
        </div>
      )}
    </ResultSection>
  )
}

/* ------------------------------------------------------------------ */
/* 8. QR                                                              */
/* ------------------------------------------------------------------ */

function QrPanel({ qr }: { qr: QrFinding | null }) {
  const { t } = useI18n()

  if (!qr) {
    return (
      <ResultSection index="09" title={t('result.qr')}>
        <DidNotRun />
      </ResultSection>
    )
  }

  return (
    <ResultSection index="09" title={t('result.qr')}>
      {qr.payload ? (
        <dl>
          <FieldRow label={t('result.qrStatus')} value={qr.decodeStatus} latin wrap />
          <FieldRow label={t('result.qrPayload')} value={qr.payload} latin wrap />
          <FieldRow
            label={t('result.qrAttempt')}
            value={qr.attemptUsed ?? t('result.notMeasured')}
            latin
          />
          <FieldRow
            label={t('result.qrIsUrl')}
            value={qr.isUrl ? t('common.yes') : t('common.no')}
            tone={qr.isUrl ? 'caution' : 'default'}
          />
        </dl>
      ) : (
        <NoteBlock>{t('result.qrNone')}</NoteBlock>
      )}

      {qr.notes && qr.notes.length > 0 && (
        <ul className="mt-4 space-y-1">
          {qr.notes.map((note, index) => (
            <li
              key={index}
              className="font-arabic-body text-[0.72rem] leading-relaxed text-text-dim"
            >
              · {note}
            </li>
          ))}
        </ul>
      )}
    </ResultSection>
  )
}

/* ------------------------------------------------------------------ */
/* 9. URLs                                                            */
/* ------------------------------------------------------------------ */

function UrlPanel({ urls }: { urls: UrlCandidate[] }) {
  const { t } = useI18n()

  if (urls.length === 0) {
    return (
      <ResultSection index="10" title={t('result.urls')}>
        <NoteBlock>{t('result.sectionUnavailable')}</NoteBlock>
      </ResultSection>
    )
  }

  return (
    <ResultSection index="10" title={t('result.urls')}>
      <div className="space-y-4">
        {urls.map((url, index) => {
          const intel = url.urlIntelligence
          const highRisk = intel.riskLevel === 'high_risk'

          return (
            <div
              key={`${url.normalizedCandidate}-${index}`}
              className={cn(
                'rounded-md border p-4',
                highRisk ? 'border-danger/35 bg-danger/[0.05]' : 'border-line/60 bg-surface-inset/40',
              )}
            >
              <p
                dir="ltr"
                className="ltr-embed text-[0.8rem] break-all text-text"
              >
                {url.normalizedCandidate}
              </p>

              <dl className="mt-3">
                <FieldRow label={t('result.urlOrigin')} value={url.origin} latin />
                <FieldRow
                  label={t('result.urlRepaired')}
                  value={url.repairApplied ? t('common.yes') : t('common.no')}
                />
                <FieldRow
                  label={t('result.urlRisk')}
                  value={highRisk ? t('result.urlHighRisk') : (intel.riskLevel ?? t('result.notMeasured'))}
                  latin={!highRisk}
                  tone={highRisk ? 'risk' : 'default'}
                />
                <FieldRow
                  label={t('result.urlTrust')}
                  value={intel.trustScore === undefined ? t('result.notMeasured') : String(intel.trustScore)}
                />
              </dl>

              {url.repairNotes.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {url.repairNotes.map((note, noteIndex) => (
                    <li
                      key={noteIndex}
                      className="font-arabic-body text-[0.7rem] leading-relaxed text-text-dim"
                    >
                      · {note}
                    </li>
                  ))}
                </ul>
              )}

              {!intel.available && intel.reason && (
                <NoteBlock tone="caution" className="mt-3">
                  {t('result.urlUnavailable')}: {intel.reason}
                </NoteBlock>
              )}
            </div>
          )
        })}
      </div>

      <NoteBlock tone="neutral" className="mt-4">
        {t('result.urlNotFetched')}
      </NoteBlock>
    </ResultSection>
  )
}

/* ------------------------------------------------------------------ */
/* 10. Encoding                                                       */
/* ------------------------------------------------------------------ */

function EncodingPanel({ findings }: { findings: EncodingFinding[] }) {
  const { t } = useI18n()

  if (findings.length === 0) {
    return (
      <ResultSection index="11" title={t('result.encoding')}>
        <NoteBlock>{t('result.encodingNone')}</NoteBlock>
      </ResultSection>
    )
  }

  return (
    <ResultSection index="11" title={t('result.encoding')}>
      <div className="space-y-4">
        {findings.map((finding, index) => (
          <div
            key={`${finding.encodingType}-${finding.depth}-${index}`}
            className="rounded-md border border-line/60 bg-surface-inset/40 p-4"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <span className="ltr-embed text-[0.8rem] text-text" dir="ltr">
                {finding.encodingType}
              </span>
              <span className="ltr-embed text-[0.72rem] text-text-dim" dir="ltr">
                {finding.confidence.toFixed(2)}
              </span>
            </div>

            {/* Raw and decoded side by side, in the order they were
                found. The reader judges the decode rather than
                trusting it — that is the whole point of showing both. */}
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <div>
                <p className="mono-label mb-1.5 text-text-dim">{t('result.encodingRaw')}</p>
                <pre
                  dir="auto"
                  className="bidi-auto max-h-[140px] overflow-auto rounded border border-line/50 bg-surface/40 p-2.5 text-[0.68rem] leading-relaxed text-text-dim"
                >
                  {finding.rawPreview}
                </pre>
              </div>
              <div>
                <p className="mono-label mb-1.5 text-text-dim">
                  {t('result.encodingDecoded')}
                </p>
                <pre
                  dir="auto"
                  className="bidi-auto max-h-[140px] overflow-auto rounded border border-signal/25 bg-signal/[0.04] p-2.5 text-[0.68rem] leading-relaxed text-text"
                >
                  {finding.decodedPreview}
                </pre>
              </div>
            </div>

            {finding.riskIndicators.length > 0 && (
              <div className="mt-3">
                <p className="mono-label mb-1.5 text-caution">
                  {t('result.encodingRisk')}
                </p>
                <ul className="flex flex-wrap gap-2">
                  {finding.riskIndicators.map((indicator) => (
                    <li
                      key={indicator}
                      className="ltr-embed rounded-full border border-caution/30 px-2.5 py-1 text-[0.66rem] text-caution"
                    >
                      {indicator.replace(/_/g, ' ')}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </ResultSection>
  )
}

/* ------------------------------------------------------------------ */
/* 11. File intelligence                                              */
/* ------------------------------------------------------------------ */

/**
 * File intelligence.
 *
 * The refused case is the one that matters most here, and it is
 * rendered in danger tones with the backend's own `reason` quoted
 * verbatim. A refused file is NOT a safe file and NOT an empty
 * result — it is a file nobody looked at, and presenting it in a
 * neutral card is how "we could not analyse this" gets read as
 * "there was nothing to find".
 */
function FileIntelligence({ file }: { file: FileFinding | null }) {
  const { t } = useI18n()

  if (!file) {
    return (
      <ResultSection index="12" title={t('result.fileAccepted')}>
        <DidNotRun />
        <NoteBlock className="mt-3">{t('result.fileCoverageText')}</NoteBlock>
      </ResultSection>
    )
  }

  if (!file.accepted) {
    return (
      <ResultSection
        index="12"
        title={t('result.fileRefused')}
        className="border-danger/30 bg-danger/[0.04]"
      >
        <div className="flex items-start gap-3">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-danger" />
          <div className="min-w-0">
            <NoteBlock tone="danger">{t('result.fileRefusedNote')}</NoteBlock>
            {file.reason && (
              <div className="mt-3">
                <p className="mono-label mb-1.5 text-text-dim">
                  {t('result.fileReason')}
                </p>
                <p className="font-arabic-body text-[0.78rem] leading-relaxed text-danger">
                  {file.reason}
                </p>
              </div>
            )}
          </div>
        </div>

        <dl className="mt-5">
          <FieldRow label={t('result.fileKind')} value={file.fileKind} latin />
          <FieldRow label={t('result.fileAccepted')} value={t('common.no')} tone="risk" />
        </dl>

        <NoteBlock className="mt-4">{t('result.fileCoverageText')}</NoteBlock>
      </ResultSection>
    )
  }

  return (
    <ResultSection index="12" title={t('result.fileAccepted')}>
      <dl>
        <FieldRow label={t('result.fileKind')} value={file.fileKind} latin />
        <FieldRow label={t('result.fileAccepted')} value={t('common.yes')} tone="trust" />
        <FieldRow
          label={t('result.fileTextChars')}
          value={String(file.textChars)}
        />
        <FieldRow
          label={t('result.fileUrls')}
          value={file.urls.length === 0 ? t('result.notMeasured') : String(file.urls.length)}
        />
        <FieldRow
          label={t('result.fileEmails')}
          value={file.emails.length === 0 ? t('common.no') : file.emails.join(', ')}
          latin
          wrap
        />
        <FieldRow
          label={t('result.fileIps')}
          value={file.ips.length === 0 ? t('common.no') : file.ips.join(', ')}
          latin
          wrap
        />
      </dl>

      {/* Risk findings, when the backend raised any. These are its own
          strings, not ours. */}
      {file.suspicious.length > 0 && (
        <div className="mt-5">
          <p className="mono-label mb-2 text-caution">{t('result.fileSuspicious')}</p>
          <ul className="space-y-1.5">
            {file.suspicious.map((item, index) => (
              <li
                key={index}
                className="font-arabic-body border-s border-caution/40 ps-3 text-[0.76rem] leading-relaxed text-caution"
              >
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {file.encodedPreview && file.encodedPreview.length > 0 && (
        <div className="mt-5">
          <p className="mono-label mb-2 text-text-dim">{t('result.encodingRaw')}</p>
          <pre
            dir="auto"
            className="bidi-auto max-h-[160px] overflow-auto rounded border border-line/60 bg-surface-inset/50 p-3 text-[0.7rem] leading-relaxed text-text-muted"
          >
            {file.encodedPreview
              .map((item) => `${item.encodingType}: ${item.rawPreview} → ${item.decodedPreview}`)
              .join('\n')}
          </pre>
        </div>
      )}

      {file.notes.length > 0 && (
        <div className="mt-4">
          <p className="mono-label mb-2 text-text-dim">{t('result.notes')}</p>
          <ul className="space-y-1">
            {file.notes.map((note, index) => (
              <li
                key={index}
                className="font-arabic-body text-[0.72rem] leading-relaxed text-text-dim"
              >
                · {note}
              </li>
            ))}
          </ul>
        </div>
      )}

      <NoteBlock className="mt-4">{t('result.fileCoverageText')}</NoteBlock>
    </ResultSection>
  )
}

/* ------------------------------------------------------------------ */
/* 12. Metadata & forensics                                            */
/* ------------------------------------------------------------------ */

/**
 * Metadata and forensics, read out of the loosely-typed payload.
 *
 * These arrive as `Record<string, unknown>` because the backend
 * serialises its image-analysis block verbatim. Rather than cast the
 * whole object to a concrete type — which would be a lie about what
 * has been checked — each field is read through a small typed
 * accessor that returns null when the key is absent or the wrong
 * shape. A null renders as "not measured", never as a blank cell that
 * reads like an empty string the pipeline produced on purpose.
 */
function readString(source: Record<string, unknown>, key: string): string | null {
  const value = source[key]
  return typeof value === 'string' && value.length > 0 ? value : null
}

function readNumber(source: Record<string, unknown>, key: string): number | null {
  const value = source[key]
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function readBoolean(source: Record<string, unknown>, key: string): boolean | null {
  const value = source[key]
  return typeof value === 'boolean' ? value : null
}

function MetadataForensics({ evidence }: { evidence: EvidenceDetail }) {
  const { t } = useI18n()
  const metadata = evidence.metadata
  const forensics = evidence.forensics

  const width = metadata ? readNumber(metadata, 'width') : null
  const height = metadata ? readNumber(metadata, 'height') : null
  const exif = metadata ? readBoolean(metadata, 'exifPresent') : null
  const gps = metadata ? readBoolean(metadata, 'gpsPresent') : null

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ResultSection index="13" title={t('result.metadata')}>
        {metadata ? (
          <dl>
            <FieldRow
              label={t('result.metaFormat')}
              value={readString(metadata, 'format') ?? t('result.notMeasured')}
              latin
            />
            <FieldRow
              label={t('result.metaDimensions')}
              value={
                width !== null && height !== null
                  ? `${width} × ${height}`
                  : t('result.notMeasured')
              }
            />
            <FieldRow
              label={t('result.metaSoftware')}
              value={readString(metadata, 'software') ?? t('result.notMeasured')}
              latin
              wrap
            />
            <FieldRow
              label={t('result.metaCamera')}
              value={readString(metadata, 'cameraMake') ?? t('result.notMeasured')}
              latin
            />
            <FieldRow
              label={t('result.metaExif')}
              value={exif === null ? t('result.notMeasured') : exif ? t('common.yes') : t('common.no')}
            />
            {/* Location is BOOLEAN ONLY, matching the image panel.
                Coordinates are never surfaced anywhere in this app. */}
            <FieldRow
              label={t('result.metaGps')}
              value={gps === null ? t('result.notMeasured') : gps ? t('common.yes') : t('common.no')}
            />
          </dl>
        ) : (
          <DidNotRun />
        )}
      </ResultSection>

      <ResultSection index="14" title={t('result.forensics')}>
        {forensics && forensics.length > 0 ? (
          <ul className="space-y-4">
            {forensics.map((signal, index) => {
              const name = readString(signal, 'name') ?? `signal-${index}`
              const value = readNumber(signal, 'value')
              const meaning = readString(signal, 'meaningEn')
              const doesNotMean = readString(signal, 'doesNotMeanEn')

              return (
                <li key={`${name}-${index}`} className="border-b border-line/40 pb-4 last:border-b-0">
                  <div className="flex items-baseline justify-between gap-4">
                    <span className="ltr-embed text-[0.78rem] text-text" dir="ltr">
                      {name}
                    </span>
                    <span className="ltr-embed text-[0.78rem] text-signal" dir="ltr">
                      {value === null
                        ? t('image.forensics.notMeasured')
                        : value.toFixed(3)}
                    </span>
                  </div>
                  {meaning && (
                    <p className="font-arabic-body mt-1 text-[0.73rem] leading-relaxed text-text-muted">
                      {meaning}
                    </p>
                  )}
                  {/* The "does not mean" line travels with the
                      finding, on screen exactly as on paper. */}
                  {doesNotMean && (
                    <p className="font-arabic-body mt-0.5 text-[0.71rem] leading-relaxed text-caution">
                      {doesNotMean}
                    </p>
                  )}
                </li>
              )
            })}
          </ul>
        ) : (
          <NoteBlock>{t('result.forensicsNone')}</NoteBlock>
        )}
      </ResultSection>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* 13. Limitations                                                    */
/* ------------------------------------------------------------------ */

function Limitations({ evidence }: { evidence: EvidenceDetail }) {
  const { t } = useI18n()
  const limitations = evidence.limitations ?? []

  return (
    <ResultSection index="15" title={t('result.limitations')}>
      {limitations.length === 0 ? (
        <NoteBlock>{t('reports.noLimitations')}</NoteBlock>
      ) : (
        <ul className="space-y-2">
          {limitations.map((limitation, index) => (
            <li
              key={index}
              className="font-arabic-body flex gap-2.5 border-s border-line-bright ps-3 text-[0.78rem] leading-relaxed text-text-muted"
            >
              <span aria-hidden className="text-text-dim">
                ·
              </span>
              <span>{limitation}</span>
            </li>
          ))}
        </ul>
      )}
    </ResultSection>
  )
}

/* ------------------------------------------------------------------ */
/* 14. Digital Trust Assessment — small, secondary, last              */
/* ------------------------------------------------------------------ */

/**
 * The trust assessment.
 *
 * SMALL and LAST on purpose. It is a composite of detector agreement,
 * evidence quality, distribution familiarity, provenance and any URL
 * risk — a useful summary, but a summary of things the reader has
 * already been shown individually and can therefore judge. Leading
 * with it would let one opaque number outrank the cryptographic
 * provenance evidence and the abstention, which is exactly the
 * inversion this product must not commit.
 *
 * Three copy rules hold here, all enforced by the payload itself:
 *
 *   · The label is the backend's own "Digital Trust Assessment". It is
 *     never renamed to "Authenticity", "Realness" or "Verified".
 *   · `isAuthenticityProbability` is false and the note says why, so
 *     the note is always rendered.
 *   · `authenticityVerified` is only ever true when real signature
 *     verification happened, and it is stated as a boolean, not as a
 *     headline.
 */
function DigitalTrustAssessmentCard({
  trust,
}: {
  trust: TrustAssessment | null
}) {
  const { t } = useI18n()

  if (!trust) {
    return null
  }

  return (
    <section className="rounded-lg border border-line/60 bg-surface/30 p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <div className="min-w-0">
          <p className="mono-label text-text-dim">
            {t('result.trustAssessment')}
          </p>
          {/* The backend's own label, verbatim. */}
          <p className="mt-1.5 text-[0.92rem] text-text">{trust.label}</p>
        </div>
        <p className="ltr-embed text-[1.4rem] leading-none text-text" dir="ltr">
          {trust.value.toFixed(1)}
          <span className="ml-1 text-[0.7rem] text-text-dim">/100</span>
        </p>
      </div>

      <p className="font-arabic-body mt-3 text-[0.74rem] leading-relaxed text-text-dim">
        {t('result.trustAssessmentSub')}
      </p>

      {/* The backend's own explanation, always shown because
          `isAuthenticityProbability` is always false. */}
      <NoteBlock tone="caution" className="mt-3">
        {trust.note}
      </NoteBlock>

      <div className="mt-4">
        <p className="mono-label mb-2 text-text-dim">{t('result.components')}</p>
        <dl>
          {Object.entries(trust.components).map(([name, value]) => (
            <FieldRow
              key={name}
              label={name.replace(/_/g, ' ')}
              value={value.toFixed(3)}
            />
          ))}
          <FieldRow
            label={t('result.prov.signature')}
            value={trust.authenticityVerified ? t('common.yes') : t('common.no')}
            tone={trust.authenticityVerified ? 'trust' : 'default'}
          />
        </dl>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/* The view                                                           */
/* ------------------------------------------------------------------ */

export function EvidenceResultView({ evidence }: EvidenceResultViewProps) {
  const { t } = useI18n()

  const conflict = evidence.ensemble?.detectorAgreement === 'conflict'
  const coverage = evidence.coverage

  // Timeline 2.0 — the ordered record of what was examined
  const timelineEntries = buildTimelineEntries(evidence.timeline || [])

  return (
    <div className="space-y-6">
      {/* 1 — the conclusion */}
      <FinalAssessment evidence={evidence} />

      {/* 2 — the only cryptographic evidence there is */}
      <ProvenancePanel provenance={evidence.provenance} />

      {/* 3 — conflict block, immediately after the verdict it changes */}
      {conflict && evidence.ensemble && <DetectorConflict ensemble={evidence.ensemble} />}

      {/* 3b — agreement / quality / distribution */}
      {evidence.ensemble ? (
        <AgreementQualityDistribution ensemble={evidence.ensemble} />
      ) : (
        <ResultSection index="03" title={t('result.detectorAgreement')}>
          <DidNotRun />
        </ResultSection>
      )}

      {/* 4 — coverage, before any finding from a branch */}
      <AnalysisCoverage evidence={evidence} />

      {/* 5 — per-detector synthetic evidence */}
      {evidence.ensemble ? (
        <SyntheticEvidence ensemble={evidence.ensemble} />
      ) : (
        <ResultSection index="07" title={t('result.synthetic')}>
          <DidNotRun />
        </ResultSection>
      )}

      {/*
        6 — the screenshot chain, with its three independent lines.

        Gated on an IMAGE pipeline, not on "did any channel produce
        output". The backend runs an OCR block on text uploads too
        (often an engine-less one), so testing for its presence would
        render a chain whose first step is "Screenshot" for a .txt
        file — describing a modality that was never involved.
      */}
      {isImagePipeline(evidence.mode) ? <ScreenshotChain evidence={evidence} /> : null}

      {/* 7-9 — what was read out of the content */}
      <OcrPanel ocr={evidence.ocr} />
      <QrPanel qr={evidence.qr} />
      <UrlPanel urls={evidence.urls} />
      <EncodingPanel findings={evidence.encoding} />

      {/* 10 — file intelligence */}
      <FileIntelligence file={evidence.file} />

      {/* 11 — file-level characteristics */}
      <MetadataForensics evidence={evidence} />

      {/* 12 — limitations */}
      <Limitations evidence={evidence} />

      {/* 13 — the small secondary card, last */}
      <DigitalTrustAssessmentCard trust={evidence.trustAssessment} />

      {/* 14 — Investigation Timeline 2.0 — the ordered record */}
      <ResultSection index="14" title={t('timeline.title')} subtitle={t('timeline.subtitle')}>
        <TimelineView entries={timelineEntries} />
      </ResultSection>

      {/* 15 — Analysis Coverage — which branches ran */}
      <ResultSection index="15" title={t('result.coverage')} subtitle={t('result.coverageSub')}>
        {coverage ? (
          <ul>
            {coverage.imagePixels > 0 && <li key="image">{t('coverageYes')} {t('result.image')}</li>}
            {coverage.provenance !== 'not_applicable' && <li>{coverage.provenance === 'available' ? t('coverageYes') : t('coverageNo')} {t('result.provenance')}</li>}
            {coverage.ocr !== 'not_applicable' && <li>{coverage.ocr === 'analyzed' ? t('coverageYes') : t('coverageNo')} {t('result.ocr')}</li>}
            {coverage.qr !== 'not_applicable' && <li>{coverage.qr === 'analyzed' ? t('coverageYes') : t('coverageNo')} {t('result.qr')}</li>}
            {coverage.url !== 'not_applicable' && <li>{coverage.url === 'analyzed' ? t('coverageYes') : t('coverageNo')} {t('result.urls')}</li>}
            {coverage.encoding !== 'not_applicable' && <li>{coverage.encoding === 'analyzed' ? t('coverageYes') : t('coverageNo')} {t('result.encoding')}</li>}
          </ul>
        ) : (
          <NoteBlock>{t('result.sectionUnavailable')}</NoteBlock>
        )}
      </ResultSection>

      {/* 16 — SHA-256 Evidence Fingerprint */}
      <ResultSection index="16" title={t('result.evidenceFingerprint')} subtitle={t('result.evidenceFingerprintSub')}>
        <div className="flex flex-wrap items-baseline gap-x-5 gap-y-1">
          <span className="mono-label text-text-dim">{t('result.evidenceFingerprintLabel')}</span>
          <span className="mono-label text-[0.72rem] text-text-muted">{evidence.fingerprint}</span>
        </div>
        <p className="mt-2 text-[0.68rem] text-text-dim">
          {t('result.evidenceFingerprintNote')}
        </p>
      </ResultSection>

      {/* 17 — Report Traceability */}
      <ResultSection index="17" title={t('result.reportTraceability')} subtitle={t('result.reportTraceabilitySub')}>
        <ul className="space-y-2">
          {evidence.reportTraceability.map((ref, i) => (
            <li key={i} className="font-mono text-[0.72rem] text-text-dim">
              {ref}
            </li>
          ))}
        </ul>
        {evidence.reportTraceability.length === 0 && (
          <NoteBlock>{t('result.reportTraceabilityEmpty')}</NoteBlock>
        )}
      </ResultSection>

      {/* 18 — Digital Trust Assessment — small, secondary, last */}
      <DigitalTrustAssessmentCard trust={evidence.trustAssessment} />
    </div>
  )
}