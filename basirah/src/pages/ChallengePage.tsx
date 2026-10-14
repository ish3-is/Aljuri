import { useCallback, useRef, useState } from 'react'
import { motion } from 'motion/react'
import { Eye, EyeOff, ShieldAlert, Upload } from 'lucide-react'
import { Panel } from '../components/ui/primitives'
import { Magnetic } from '../components/ui/primitives'
import { apiEvidenceAnalysisProvider } from '../features/analysis/evidenceProvider'
import { AnalysisError } from '../features/analysis/providers'
import {
  BLIND_TEST_CAVEAT,
  blindDefenseTest,
} from '../data/blindDefenseTest'
import { useI18n } from '../i18n/useI18n'
import { cn, formatScore } from '../lib/utils'
import type {
  DetectorEnsemble,
  EvidenceDetail,
  EvidenceProvenance,
  OcrFinding,
  TrustAssessment,
} from '../types/analysis'
import {
  DidNotRun,
  FieldRow,
  NoteBlock,
  ResultSection,
  StatBlock,
} from '../features/result/resultPrimitives'

/* ============================================================
   CHALLENGE — internal defence mode

   A working surface for adversarial testing rather than a demo
   page. It runs the SAME live evidence pipeline the public
   Analyze section uses — no separate "challenge" analysis, no
   privileged mode that sees something a user would not.

   Its distinguishing feature is the GROUND TRUTH comparison. A
   known-answer fixture can be uploaded and analysed, but the
   truth stays locked until the reader explicitly reveals it. That
   ordering is the entire point: if the truth were visible during
   the run, a human would unconsciously steer toward it and the
   comparison would measure nothing but their own expectations.

   So the truth is:
     · hidden by default, every time, with no memory of a
       previous reveal
     · revealed only after a run has actually completed
     · unavailable at all when no fixture has been analysed, since
       there is nothing to compare against
   ============================================================ */

/**
 * A fixture's declared ground truth.
 *
 * Typed as a closed union rather than a free string so the page can
 * only ever compare the pipeline against one of the two labels the
 * evaluation actually uses. A fixture cannot declare itself
 * "authentic" in a way that would invite an authenticity reading of
 * the comparison.
 */
type GroundTruth = 'synthetic' | 'real'

interface ChallengeRun {
  detail: EvidenceDetail
  /** Set only when a fixture declared its own truth. */
  truth: GroundTruth | null
  fixtureName: string
}

export function ChallengePage() {
  const { t } = useI18n()
  const inputRef = useRef<HTMLInputElement>(null)

  const [run, setRun] = useState<ChallengeRun | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [fileName, setFileName] = useState<string | null>(null)
  /**
   * Reset to false on every new run. A previous reveal must not
   * carry over, or the truth would be readable on the next run
   * before the reader ever analysed it.
   */
  const [truthRevealed, setTruthRevealed] = useState(false)

  const runAnalysis = useCallback(async (file: File) => {
    setBusy(true)
    setError(null)
    setTruthRevealed(false)
    setFileName(file.name)
    try {
      const result = await apiEvidenceAnalysisProvider.analyze({
        kind: 'image',
        label: file.name,
        file,
      })
      // The provider returns the shared contract; narrow to the
      // evidence payload this page is built around.
      const detail = (result as { evidence?: EvidenceDetail }).evidence
      if (!detail) {
        setError('The pipeline returned no evidence payload for this fixture.')
        setRun(null)
      } else {
        setRun({
          detail,
          // No ground truth is inferred from a filename or from
          // anything in the payload. A fixture that does not declare
          // its own truth simply has none.
          truth: null,
          fixtureName: file.name,
        })
      }
    } catch (cause) {
      setRun(null)
      setError(
        cause instanceof AnalysisError
          ? cause.message
          : 'The analysis could not be completed for this fixture.',
      )
    } finally {
      setBusy(false)
    }
  }, [])

  const handleFile = useCallback(
    (file: File | undefined) => {
      if (!file) return
      void runAnalysis(file)
    },
    [runAnalysis],
  )

  return (
    <div className="px-5 pt-28 pb-10 sm:px-8 sm:pt-32">
      <div className="mx-auto max-w-[1400px]">
        {/* ================= HEADER ================= */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        >
          <p className="mono-label text-signal/70">{t('challenge.nav')}</p>
          <h1 className="mt-3 text-2xl leading-tight font-light tracking-tight sm:text-3xl">
            {t('challenge.title')}
          </h1>
          <p className="font-arabic-body mt-3 max-w-3xl text-[0.84rem] leading-relaxed text-text-dim">
            {t('challenge.sub')}
          </p>
        </motion.div>

        {/* ================= BLIND TEST PANEL ================= */}
        <section className="mt-10">
          <BlindTestPanel />
        </section>

        {/* ================= INPUT ================= */}
        <section className="mt-8">
          <Panel accent className="p-6">
            <div className="flex flex-wrap items-center gap-3">
              <span className="mono-label text-signal/70">01</span>
              <h2 className="text-sm text-text">{t('challenge.input')}</h2>
              <span aria-hidden className="hairline h-px flex-1" />
            </div>
            <p className="font-arabic-body mt-3 text-[0.78rem] leading-relaxed text-text-dim">
              {t('challenge.inputSub')}
            </p>

            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              className="sr-only"
              onChange={(event) => {
                handleFile(event.target.files?.[0])
                event.target.value = ''
              }}
            />

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <Magnetic strength={5}>
                <button
                  type="button"
                  onClick={() => inputRef.current?.click()}
                  disabled={busy}
                  className={cn(
                    'inline-flex items-center gap-2 rounded-full border border-signal/35 bg-signal/10 px-4 py-2 text-[0.78rem] text-signal',
                    'transition-colors duration-200 hover:border-signal/55 hover:bg-signal/15 disabled:opacity-40',
                  )}
                >
                  <Upload size={13} />
                  {t('challenge.uploadFixture')}
                </button>
              </Magnetic>

              {fileName && (
                <span className="ltr-embed text-[0.72rem] text-text-dim" dir="ltr">
                  {fileName}
                </span>
              )}
            </div>

            {error && (
              <NoteBlock tone="danger" className="mt-4">
                {error}
              </NoteBlock>
            )}

            {!run && !busy && (
              <NoteBlock className="mt-4">{t('challenge.awaitingRun')}</NoteBlock>
            )}
          </Panel>
        </section>

        {/* ================= GROUND TRUTH ================= */}
        {run && (
          <section className="mt-6">
            <GroundTruthPanel
              run={run}
              revealed={truthRevealed}
              onReveal={() => setTruthRevealed(true)}
            />
          </section>
        )}

        {/* ================= THE SAME PANELS, IN DEFENCE ORDER =================
            The section list is fixed by the brief and follows the
            evidence hierarchy rather than the prose order: what was
            submitted, what each detector said on its own, whether
            they agreed, whether the material was familiar, how good
            the evidence was, then each channel in turn, and only
            last the fused conclusion and the trust composite. */}
        {run && (
          <div className="mt-8 space-y-5">
            <ChallengeInputPanel run={run} />

            <div className="grid gap-5 lg:grid-cols-2">
              <DetectorPanel
                index="02"
                title={t('challenge.sectionDetectorA')}
                ensemble={run.detail.ensemble}
                which={0}
              />
              <DetectorPanel
                index="03"
                title={t('challenge.sectionDetectorB')}
                ensemble={run.detail.ensemble}
                which={1}
              />
            </div>

            <AgreementPanel ensemble={run.detail.ensemble} />
            <OodPanel ensemble={run.detail.ensemble} />
            <QualityPanel ensemble={run.detail.ensemble} />
            <ProvenancePanelSimple provenance={run.detail.provenance} />

            <div className="grid gap-5 lg:grid-cols-2">
              <OcrPanelSimple ocr={run.detail.ocr} />
              <QrPanelSimple qr={run.detail.qr} />
            </div>

            <UrlsPanelSimple urls={run.detail.urls} />
            <EncodingPanelSimple findings={run.detail.encoding} />
            <MetadataPanelSimple metadata={run.detail.metadata} />
            <ForensicsPanelSimple forensics={run.detail.forensics} />
            <FusionPanel detail={run.detail} />
            <TrustPanelSimple trust={run.detail.trustAssessment} />
          </div>
        )}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Blind test panel                                                    */
/* ------------------------------------------------------------------ */

/**
 * The only accuracy figures BASIRAH has.
 *
 * Every number is transcribed from the project's own held-out
 * evaluation; nothing here is computed at render time, rounded, or
 * derived. The four limitations are rendered ON THE PANEL rather
 * than behind a link, because a 0/26 false-authentic rate with no
 * visible caveats is a claim this product must never make in a
 * reader's eyes.
 */
function BlindTestPanel() {
  const { t } = useI18n()
  const data = blindDefenseTest

  const figures = [
    {
      label: t('challenge.blindSampleCount'),
      value: String(data.sampleCount),
      hint: `${data.syntheticCount} synthetic / ${data.realCount} real`,
    },
    {
      label: t('challenge.blindFalseAuthentic'),
      value: `${data.falseAuthenticCount}/${data.falseAuthenticDenominator}`,
    },
    {
      label: t('challenge.blindDetectorA'),
      value: `${data.detectorAFalseAuthentic}/${data.detectorDenominator}`,
      tone: 'caution' as const,
    },
    {
      label: t('challenge.blindDetectorB'),
      value: `${data.detectorBFalseAuthentic}/${data.detectorDenominator}`,
    },
    {
      label: t('challenge.blindDisagreements'),
      value: String(data.disagreements),
    },
    {
      label: t('challenge.blindAbstention'),
      value: `${(data.abstentionRate * 100).toFixed(2)}%`,
      tone: 'caution' as const,
    },
    {
      label: t('challenge.blindOod'),
      value: String(data.outOfDistribution),
    },
    {
      label: t('challenge.blindLatency'),
      value: `${data.meanLatencyMs} ms`,
    },
  ]

  const limitations = [
    t('challenge.blindLimitSmall'),
    t('challenge.blindLimitGenerators'),
    t('challenge.blindLimitReal'),
    t('challenge.blindLimitNotValidation'),
  ]

  return (
    <Panel accent className="p-6 sm:p-8">
      <div className="flex flex-wrap items-center gap-3">
        <span className="mono-label text-signal/70">00</span>
        <h2 className="text-sm text-text">{t('challenge.blindTitle')}</h2>
        <span aria-hidden className="hairline h-px flex-1" />
      </div>
      <p className="font-arabic-body mt-3 max-w-3xl text-[0.78rem] leading-relaxed text-text-dim">
        {t('challenge.blindSub')}
      </p>

      <ul className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {figures.map((figure) => (
          <li key={figure.label}>
            <StatBlock
              label={figure.label}
              value={figure.value}
              hint={figure.hint}
              tone={'tone' in figure ? figure.tone : 'default'}
            />
          </li>
        ))}
      </ul>

      {/* The exact, non-paraphrasable caveat. */}
      <NoteBlock tone="caution" className="mt-5" >
        {BLIND_TEST_CAVEAT}
      </NoteBlock>

      <div className="mt-5">
        <p className="mono-label mb-2.5 text-text-dim">
          {t('challenge.blindLimitations')}
        </p>
        <ul className="space-y-2">
          {limitations.map((limitation) => (
            <li
              key={limitation}
              className="font-arabic-body flex gap-2.5 border-s border-line-bright ps-3 text-[0.76rem] leading-relaxed text-text-muted"
            >
              <span aria-hidden className="text-text-dim">
                ·
              </span>
              <span>{limitation}</span>
            </li>
          ))}
        </ul>
      </div>
    </Panel>
  )
}

/* ------------------------------------------------------------------ */
/* Ground truth                                                        */
/* ------------------------------------------------------------------ */

/**
 * The locked truth.
 *
 * Two states, and both matter:
 *
 *   · no run yet — there is nothing to compare against, so the
 *     reveal action does not exist at all rather than existing and
 *     doing nothing
 *   · a run without declared truth — the panel says the fixture
 *     declared none, instead of inventing a comparison
 *
 * Once revealed, the comparison is stated in words. It is not
 * turned into a score: a human judge agreeing or disagreeing with a
 * 26-image set is worth less than a measurement, and dressing it up
 * as one would overstate it.
 */
function GroundTruthPanel({
  run,
  revealed,
  onReveal,
}: {
  run: ChallengeRun
  revealed: boolean
  onReveal: () => void
}) {
  const { t } = useI18n()
  const value = run.detail.fusion?.finalAssessment ?? run.detail.finalAssessment

  return (
    <Panel className="p-6">
      <div className="flex flex-wrap items-center gap-3">
        <span className="mono-label text-signal/70">{t('challenge.groundTruth')}</span>
        <span aria-hidden className="hairline h-px flex-1" />

        <Magnetic strength={4}>
          <button
            type="button"
            onClick={onReveal}
            data-testid="reveal-ground-truth"
            className={cn(
              'inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-[0.74rem] transition-colors duration-200',
              revealed
                ? 'border-line text-text-dim'
                : 'border-signal/35 bg-signal/10 text-signal hover:border-signal/55',
            )}
          >
            {revealed ? <EyeOff size={12} /> : <Eye size={12} />}
            {t('challenge.revealTruth')}
          </button>
        </Magnetic>
      </div>

      {!revealed ? (
        <NoteBlock tone="caution" className="mt-4">
          {run.truth
            ? t('challenge.groundTruthLocked')
            : t('challenge.groundTruthHidden')}
        </NoteBlock>
      ) : run.truth ? (
        <div className="mt-4 space-y-3">
          <dl>
            <FieldRow
              label={t('challenge.groundTruth')}
              value={run.truth === 'synthetic' ? t('result.assessmentLikelySynthetic') : t('result.assessmentNoStrong')}
              latin={false}
            />
            <FieldRow
              label={t('challenge.sectionFusion')}
              value={value ?? '—'}
              latin={false}
            />
          </dl>
          <NoteBlock
            tone={
              run.truth === 'synthetic' && value === 'likely_synthetic'
                ? 'trust'
                : run.truth === 'real' && value !== 'likely_synthetic'
                  ? 'trust'
                  : 'caution'
            }
          >
            {run.truth === 'synthetic' && value === 'likely_synthetic'
              ? t('challenge.truthMatches')
              : run.truth === 'real' && value !== 'likely_synthetic'
                ? t('challenge.truthMatches')
                : t('challenge.truthDiffers')}
          </NoteBlock>
        </div>
      ) : (
        <NoteBlock className="mt-4">{t('challenge.groundTruthHidden')}</NoteBlock>
      )}
    </Panel>
  )
}

/* ------------------------------------------------------------------ */
/* Input                                                               */
/* ------------------------------------------------------------------ */

function ChallengeInputPanel({ run }: { run: ChallengeRun }) {
  const { t } = useI18n()
  return (
    <ResultSection index="01" title={t('challenge.sectionInput')}>
      <dl>
        <FieldRow label={t('reports.item')} value={run.fixtureName} latin wrap />
        <FieldRow label={t('result.engine')} value={run.detail.mode} latin />
        <FieldRow
          label={t('result.latency')}
          value={
            run.detail.latencyMs.total === undefined
              ? t('result.notMeasured')
              : `${run.detail.latencyMs.total} ms`
          }
        />
      </dl>
    </ResultSection>
  )
}

/* ------------------------------------------------------------------ */
/* Detectors, one panel each                                           */
/* ------------------------------------------------------------------ */

/**
 * A single detector's own reading.
 *
 * Defence mode splits the ensemble into two separate panels rather
 * than showing one card per detector. In a review setting the useful
 * question is not "what did the ensemble say" but "which model was
 * wrong, and how", and that question needs the two answers side by
 * side in separate frames to be answerable at all.
 */
function DetectorPanel({
  index,
  title,
  ensemble,
  which,
}: {
  index: string
  title: string
  ensemble: DetectorEnsemble | null
  which: 0 | 1
}) {
  const { t } = useI18n()

  if (!ensemble || ensemble.detectors.length <= which) {
    return (
      <ResultSection index={index} title={title}>
        <DidNotRun />
      </ResultSection>
    )
  }

  const detector = ensemble.detectors[which]

  return (
    <ResultSection index={index} title={title}>
      <dl>
        <FieldRow label={t('result.modelName')} value={detector.modelName} latin wrap />
        <FieldRow label={t('result.architecture')} value={detector.architecture} latin wrap />
        <FieldRow
          label={t('result.valueLabel')}
          value={
            detector.status !== 'available'
              ? (detector.unavailableReason ?? t('result.abstain'))
              : `${(detector.syntheticProbability * 100).toFixed(1)}%`
          }
          tone={detector.syntheticProbability >= 0.5 ? 'risk' : 'trust'}
        />
      </dl>

      {detector.limitations.length > 0 && (
        <ul className="mt-4 space-y-1">
          {detector.limitations.map((limitation, i) => (
            <li
              key={i}
              className="font-arabic-body text-[0.72rem] leading-relaxed text-text-dim"
            >
              · {limitation}
            </li>
          ))}
        </ul>
      )}
    </ResultSection>
  )
}

/* ------------------------------------------------------------------ */
/* Agreement / OOD / quality                                           */
/* ------------------------------------------------------------------ */

function AgreementPanel({ ensemble }: { ensemble: DetectorEnsemble | null }) {
  const { t } = useI18n()

  if (!ensemble) {
    return (
      <ResultSection index="04" title={t('challenge.sectionAgreement')}>
        <DidNotRun />
      </ResultSection>
    )
  }

  const conflict = ensemble.detectorAgreement === 'conflict'

  return (
    <ResultSection
      index="04"
      title={t('challenge.sectionAgreement')}
      className={conflict ? 'border-danger/35' : undefined}
    >
      <dl>
        <FieldRow
          label={t('result.detectorAgreement')}
          value={ensemble.detectorAgreement.replace(/_/g, ' ')}
          latin
          tone={conflict ? 'risk' : 'default'}
        />
        <FieldRow
          label={t('result.syntheticLikelihood')}
          // null here is an abstention, not a zero and not 50%.
          value={
            ensemble.syntheticLikelihood === null
              ? t('result.abstained')
              : `${(ensemble.syntheticLikelihood * 100).toFixed(1)}%`
          }
          tone={conflict ? 'caution' : 'default'}
        />
        <FieldRow
          label={t('result.abstain')}
          value={ensemble.abstained ? t('common.yes') : t('common.no')}
          tone={ensemble.abstained ? 'caution' : 'default'}
        />
      </dl>

      {conflict && (
        <div className="mt-4 space-y-2">
          <NoteBlock tone="danger">
            <span className="inline-flex items-center gap-2">
              <ShieldAlert size={13} />
              {t('result.conflict')}
            </span>
          </NoteBlock>
          <NoteBlock tone="caution">{t('result.decisionAbstained')}</NoteBlock>
        </div>
      )}

      {ensemble.abstentionReasons.length > 0 && (
        <ul className="mt-4 space-y-1">
          {ensemble.abstentionReasons.map((reason) => (
            <li key={reason} className="ltr-embed text-[0.72rem] text-text-dim">
              · {reason.replace(/_/g, ' ')}
            </li>
          ))}
        </ul>
      )}
    </ResultSection>
  )
}

function OodPanel({ ensemble }: { ensemble: DetectorEnsemble | null }) {
  const { t } = useI18n()

  if (!ensemble) {
    return (
      <ResultSection index="05" title={t('challenge.sectionOod')}>
        <DidNotRun />
      </ResultSection>
    )
  }

  const ood = ensemble.distributionStatus === 'out_of_distribution'

  return (
    <ResultSection index="05" title={t('challenge.sectionOod')}>
      <FieldRow
        label={t('result.distribution')}
        value={ensemble.distributionStatus.replace(/_/g, ' ')}
        latin
        tone={ood ? 'caution' : 'default'}
      />
      {ood && <NoteBlock tone="caution" className="mt-3">{t('result.ood.warning')}</NoteBlock>}
    </ResultSection>
  )
}

function QualityPanel({ ensemble }: { ensemble: DetectorEnsemble | null }) {
  const { t } = useI18n()

  if (!ensemble) {
    return (
      <ResultSection index="06" title={t('challenge.sectionQuality')}>
        <DidNotRun />
      </ResultSection>
    )
  }

  return (
    <ResultSection index="06" title={t('challenge.sectionQuality')}>
      <FieldRow
        label={t('result.evidenceQuality')}
        value={ensemble.evidenceQuality}
        latin
        tone={ensemble.evidenceQuality === 'low' ? 'caution' : 'default'}
      />
    </ResultSection>
  )
}

/* ------------------------------------------------------------------ */
/* Provenance                                                          */
/* ------------------------------------------------------------------ */

/**
 * Provenance in defence mode.
 *
 * Reuses the result view's wording rules — the module is labelled
 * LIMITED, and the two mandatory sentences appear when status is
 * unavailable — because the honesty requirements of C2PA do not
 * change just because the audience is an internal reviewer.
 */
function ProvenancePanelSimple({
  provenance,
}: {
  provenance: EvidenceProvenance | null
}) {
  const { t } = useI18n()

  if (!provenance) {
    return (
      <ResultSection index="07" title={t('challenge.sectionProvenance')}>
        <DidNotRun />
      </ResultSection>
    )
  }

  return (
    <ResultSection index="07" title={t('challenge.sectionProvenance')}>
      <dl>
        <FieldRow label={t('result.prov.status')} value={provenance.status.replace(/_/g, ' ')} latin />
        <FieldRow
          label={t('result.prov.moduleLabel')}
          value={t('result.prov.moduleLimited')}
          latin={false}
          tone="caution"
        />
        <FieldRow
          label={t('result.prov.manifest')}
          value={provenance.manifestPresent ? t('common.yes') : t('common.no')}
        />
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
      </dl>
      {provenance.status === 'unavailable' && (
        <div className="mt-4 space-y-2">
          <NoteBlock tone="caution">{t('result.prov.noCredentials')}</NoteBlock>
          <NoteBlock>{t('result.prov.absenceNote')}</NoteBlock>
        </div>
      )}
    </ResultSection>
  )
}

/* ------------------------------------------------------------------ */
/* Content channels                                                    */
/* ------------------------------------------------------------------ */

function OcrPanelSimple({ ocr }: { ocr: OcrFinding | null }) {
  const { t } = useI18n()

  if (!ocr) {
    return (
      <ResultSection index="08" title={t('challenge.sectionOcr')}>
        <DidNotRun />
      </ResultSection>
    )
  }

  return (
    <ResultSection index="08" title={t('challenge.sectionOcr')}>
      <dl>
        <FieldRow
          label={t('result.ocrEngine')}
          value={ocr.enginesUsed.length > 0 ? ocr.enginesUsed.join(', ') : ocr.engine}
          latin
          wrap
        />
        <FieldRow
          label={t('result.ocrConfidence')}
          value={ocr.confidence === null ? t('result.notMeasured') : ocr.confidence.toFixed(2)}
        />
      </dl>
      {ocr.text && (
        <pre
          dir="auto"
          className="bidi-auto mt-4 max-h-[150px] overflow-auto rounded border border-line/60 bg-surface-inset/50 p-3 text-[0.72rem] leading-relaxed text-text-muted"
        >
          {ocr.text}
        </pre>
      )}
      <NoteBlock tone="caution" className="mt-3">{t('result.ocrArabicLimitation')}</NoteBlock>
    </ResultSection>
  )
}

function QrPanelSimple({ qr }: { qr: EvidenceDetail['qr'] }) {
  const { t } = useI18n()

  if (!qr) {
    return (
      <ResultSection index="09" title={t('challenge.sectionQr')}>
        <DidNotRun />
      </ResultSection>
    )
  }

  return (
    <ResultSection index="09" title={t('challenge.sectionQr')}>
      <dl>
        <FieldRow label={t('result.qrStatus')} value={qr.decodeStatus} latin wrap />
        <FieldRow
          label={t('result.qrPayload')}
          value={qr.payload ?? t('result.qrNone')}
          latin
          wrap
        />
        <FieldRow
          label={t('result.qrIsUrl')}
          value={qr.isUrl ? t('common.yes') : t('common.no')}
        />
      </dl>
    </ResultSection>
  )
}

function UrlsPanelSimple({ urls }: { urls: EvidenceDetail['urls'] }) {
  const { t } = useI18n()

  return (
    <ResultSection index="10" title={t('challenge.sectionUrls')}>
      {urls.length === 0 ? (
        <DidNotRun />
      ) : (
        <dl>
          {urls.map((url, index) => (
            <FieldRow
              key={`${url.normalizedCandidate}-${index}`}
              label={`${url.origin}`}
              value={url.normalizedCandidate}
              latin
              wrap
              tone={url.urlIntelligence.riskLevel === 'high_risk' ? 'risk' : 'default'}
            />
          ))}
        </dl>
      )}
      <NoteBlock className="mt-3">{t('result.urlNotFetched')}</NoteBlock>
    </ResultSection>
  )
}

function EncodingPanelSimple({ findings }: { findings: EvidenceDetail['encoding'] }) {
  const { t } = useI18n()

  return (
    <ResultSection index="11" title={t('challenge.sectionEncoding')}>
      {findings.length === 0 ? (
        <DidNotRun />
      ) : (
        <dl>
          {findings.map((finding, index) => (
            <FieldRow
              key={`${finding.encodingType}-${index}`}
              label={finding.encodingType}
              value={finding.decodedPreview}
              latin
              wrap
            />
          ))}
        </dl>
      )}
    </ResultSection>
  )
}

function MetadataPanelSimple({
  metadata,
}: {
  metadata: Record<string, unknown> | null
}) {
  const { t } = useI18n()

  if (!metadata) {
    return (
      <ResultSection index="12" title={t('challenge.sectionMetadata')}>
        <DidNotRun />
      </ResultSection>
    )
  }

  const readString = (key: string): string | null => {
    const value = metadata[key]
    return typeof value === 'string' && value.length > 0 ? value : null
  }
  const readNumber = (key: string): string | null => {
    const value = metadata[key]
    return typeof value === 'number' && Number.isFinite(value) ? String(value) : null
  }

  return (
    <ResultSection index="12" title={t('challenge.sectionMetadata')}>
      <dl>
        <FieldRow
          label={t('result.metaFormat')}
          value={readString('format') ?? t('result.notMeasured')}
          latin
        />
        <FieldRow
          label={t('result.metaDimensions')}
          value={
            readNumber('width') && readNumber('height')
              ? `${readNumber('width')} × ${readNumber('height')}`
              : t('result.notMeasured')
          }
        />
        <FieldRow
          label={t('result.metaSoftware')}
          value={readString('software') ?? t('result.notMeasured')}
          latin
          wrap
        />
      </dl>
    </ResultSection>
  )
}

function ForensicsPanelSimple({
  forensics,
}: {
  forensics: Array<Record<string, unknown>> | null
}) {
  const { t } = useI18n()

  return (
    <ResultSection index="13" title={t('challenge.sectionForensics')}>
      {forensics && forensics.length > 0 ? (
        <dl>
          {forensics.map((signal, index) => {
            const name = typeof signal.name === 'string' ? signal.name : `signal-${index}`
            const value =
              typeof signal.value === 'number' && Number.isFinite(signal.value)
                ? signal.value.toFixed(3)
                : t('image.forensics.notMeasured')
            return (
              <FieldRow
                key={`${name}-${index}`}
                label={name.replace(/_/g, ' ')}
                value={value}
                latin
              />
            )
          })}
        </dl>
      ) : (
        <DidNotRun />
      )}
    </ResultSection>
  )
}

function FusionPanel({ detail }: { detail: EvidenceDetail }) {
  const { t } = useI18n()
  const fusion = detail.fusion

  return (
    <ResultSection index="14" title={t('challenge.sectionFusion')}>
      <dl>
        <FieldRow
          label={t('result.finalAssessment')}
          value={fusion.finalAssessment.replace(/_/g, ' ')}
          latin={false}
          tone={fusion.finalAssessment === 'likely_synthetic' ? 'risk' : fusion.finalAssessment === 'uncertain' ? 'caution' : 'default'}
        />
      </dl>

      {fusion.note && (
        <NoteBlock tone="info" className="mt-4">{fusion.note}</NoteBlock>
      )}

      {fusion.limitations.length > 0 && (
        <div className="mt-4">
          <p className="mono-label mb-2 text-text-dim">{t('result.limitations')}</p>
          <ul className="space-y-1.5">
            {fusion.limitations.map((limitation, index) => (
              <li
                key={index}
                className="font-arabic-body text-[0.74rem] leading-relaxed text-text-muted"
              >
                · {limitation}
              </li>
            ))}
          </ul>
        </div>
      )}
    </ResultSection>
  )
}

function TrustPanelSimple({ trust }: { trust: TrustAssessment | null }) {
  const { t } = useI18n()

  if (!trust) {
    return (
      <ResultSection index="15" title={t('challenge.sectionTrust')}>
        <DidNotRun />
      </ResultSection>
    )
  }

  return (
    <ResultSection index="15" title={t('challenge.sectionTrust')}>
      <StatBlock label={trust.label} value={formatScore(trust.value)} />
      <NoteBlock tone="caution" className="mt-4">{trust.note}</NoteBlock>
    </ResultSection>
  )
}