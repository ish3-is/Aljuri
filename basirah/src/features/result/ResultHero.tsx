import { useI18n } from '../../i18n/useI18n'
import { cn } from '../../lib/utils'
import type {
  ImageAssessment,
  ImageDetail,
  DistributionStatus,
  DetectorAgreement,
} from '../../types/analysis'
import { EvidenceCompassGauge } from './EvidenceCompassGauge'
import { EvidenceStatusRow } from './EvidenceStatusRow'

/**
 * RESULT HERO — the premium result surface.
 *
 * Leads with the canonical assessment and carries the animated gauge,
 * evidence strength, coverage and detector status above every other
 * panel.
 *
 * Two hardcoded rules govern the copy (not the payload):
 *
 *   1. GAUGE IS CATEGORICAL. The needle never reads a probability.
 *      It points to LIKELY SYNTHETIC / UNCERTAIN /
 *      NO SYNTHETIC INDICATORS. No 0/100, no 44/100, no fake
 *      authenticity percentage.
 *   2. UNCERTAINTY IS A STATE, NOT A MIDDLE. When the result is
 *      UNCERTAIN, the hero says so in words and the needle holds
 *      neutral — it does not move to "half".
 *
 * The assessment is pulled from `imageDetail.assessment` for image
 * results. For non-image results (URL / file / text) the hero is not
 * rendered — the assessment-first view lives in EvidenceResultView.
 */

interface ResultHeroProps {
  detail: ImageDetail | null
  finalAssessment: string | null
  evidenceStrength?: string | null
  coverage?: {
    pixelsAnalyzed?: number
    ocrChars?: number
    qrPayloads?: number
    urlCandidates?: number
  } | null
  detectorAvailability?: {
    detectorA: 'available' | 'unavailable' | 'ran_but_disagreed'
    detectorB: 'available' | 'unavailable' | 'ran_but_disagreed'
    univfd: 'available' | 'unavailable' | 'ran_but_disagreed'
  } | null
  reducedMotion?: boolean
}

const BAND_COLOR: Record<ImageAssessment, string> = {
  likely_synthetic: 'var(--color-caution)',
  uncertain: 'var(--color-text-muted)',
  likely_authentic: 'var(--color-synthetic-signal)',
}

const CATEGORICAL_LABELS: Record<
  ImageAssessment,
  { label: string; detail: string }
> = {
  likely_synthetic: {
    label: 'LIKELY SYNTHETIC',
    detail: 'The available evidence contains indicators consistent with AI-generated content.',
  },
  uncertain: {
    label: 'UNCERTAIN',
    detail: 'BASIRAH could not reach a reliable conclusion from the available evidence.',
  },
  likely_authentic: {
    label: 'NO SYNTHETIC INDICATORS DETECTED',
    detail: 'No sufficiently strong synthetic-media indicators were detected.',
  },
}

export function ResultHero({
  detail,
  finalAssessment,
  evidenceStrength,
  coverage,
  detectorAvailability,
  reducedMotion = false,
}: ResultHeroProps) {
  const { t, language } = useI18n()
  const isArabic = language === 'ar'
  const assessment =
    detail?.assessment ??
    (finalAssessment === 'uncertain' ? 'uncertain' : null)
  const color = assessment ? BAND_COLOR[assessment] : undefined
  const labels = detail
    ? CATEGORICAL_LABELS[detail.assessment]
    : { label: t('result.assessmentUncertain'), detail: '' }

  return (
    <section
      className={cn(
        'relative overflow-hidden rounded-2xl border border-line/70 bg-surface/40 p-6 sm:p-8',
        color ?? 'ring-1 ring-inset',
      )}
      role="status"
      aria-label={`Assessment: ${labels.label}`}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            color === 'var(--color-caution)'
              ? 'linear-gradient(135deg, rgba(13,113,134,0.06) 0%, transparent 60%)'
              : color === 'var(--color-synthetic-signal)'
                ? 'linear-gradient(135deg, rgba(30,122,87,0.06) 0%, transparent 60%)'
                : 'linear-gradient(135deg, rgba(143,100,18,0.06) 0%, transparent 60%)',
        }}
      />

      <div className="relative flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="mono-label text-[0.68rem] uppercase tracking-[0.14em] text-text-dim">
              {t('result.engine')}
            </p>
            <span className="mono-label text-[0.78rem] text-text">
              {detail?.fileName ?? t('result.notMeasured')}
            </span>
            <span className="mono-label text-[0.68rem] text-text-dim">|</span>
            <span className="mono-label text-[0.72rem] text-text-dim">
              {t('result.engine')}: v{detail?.model?.modelVersion ?? t('result.notMeasured')}
            </span>
          </div>

          <h1
            className="mt-3 text-2xl leading-snug font-light sm:text-3xl"
            style={{ color }}
            dir={isArabic ? 'rtl' : 'ltr'}
          >
            {labels.label}
          </h1>

          <p
            className={cn(
              'mt-2.5 max-w-xl text-[0.85rem] leading-relaxed',
              isArabic ? 'text-start' : 'text-start',
            )}
            style={{ color: color ?? 'var(--color-text)' }}
          >
            {labels.detail}
          </p>

          {evidenceStrength && (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="mono-label text-[0.62rem] uppercase tracking-[0.14em] text-text-dim">
                {t('image.evidenceStrength')}
              </span>
              <span
                className={cn(
                  'rounded-full border px-3 py-1 text-[0.72rem] font-normal',
                  evidenceStrength === 'high'
                        ? 'border-synthetic-signal/30 bg-synthetic-signal/8 text-synthetic-signal'
                        : evidenceStrength === 'medium'
                          ? 'border-signal/30 bg-signal/8 text-signal'
                          : 'border-caution/30 bg-caution/8 text-caution',
                )}
              >
                {evidenceStrength === 'high'
                  ? t('image.quality.high')
                  : evidenceStrength === 'medium'
                    ? t('image.quality.medium')
                    : t('image.quality.low')}
              </span>
            </div>
          )}

          {/* Evidence Status Summary — one compact line of evidence quality,
              distribution, provenance and detector agreement. */}
          {detail?.ensemble && (
            <div className="mt-3">
              <EvidenceStatusRow
                evidenceQuality={detail.evidenceQuality}
                distributionStatus={detail.distributionStatus ?? ('in_distribution' as DistributionStatus)}
                provenance={detail.provenance}
                detectorAgreement={detail.detectorAgreement ?? ('strong_agreement' as DetectorAgreement)}
              />
            </div>
          )}

          {coverage && (
            <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {coverage.pixelsAnalyzed !== undefined && (
                <div className="rounded-md border border-line/60 bg-surface-inset/40 px-3 py-2.5">
                  <p className="mono-label text-[0.58rem] uppercase tracking-[0.12em] text-text-dim">
                    {t('result.coveragePixels')}
                  </p>
                  <p className="mt-0.5 font-mono text-[0.82rem] text-text" dir="ltr">
                    {coverage.pixelsAnalyzed.toLocaleString()}
                  </p>
                </div>
              )}
              {coverage.ocrChars !== undefined && (
                <div className="rounded-md border border-line/60 bg-surface-inset/40 px-3 py-2.5">
                  <p className="mono-label text-[0.58rem] uppercase tracking-[0.12em] text-text-dim">
                    {t('result.coverageOcr')}
                  </p>
                  <p className="mt-0.5 font-mono text-[0.82rem] text-text" dir="ltr">
                    {coverage.ocrChars.toLocaleString()}
                  </p>
                </div>
              )}
              {coverage.qrPayloads !== undefined && (
                <div className="rounded-md border border-line/60 bg-surface-inset/40 px-3 py-2.5">
                  <p className="mono-label text-[0.58rem] uppercase tracking-[0.12em] text-text-dim">
                    {t('result.coverageQr')}
                  </p>
                  <p className="mt-0.5 font-mono text-[0.82rem] text-text" dir="ltr">
                    {coverage.qrPayloads}
                  </p>
                </div>
              )}
              {coverage.urlCandidates !== undefined && (
                <div className="rounded-md border border-line/60 bg-surface-inset/40 px-3 py-2.5">
                  <p className="mono-label text-[0.58rem] uppercase tracking-[0.12em] text-text-dim">
                    {t('result.coverageUrls')}
                  </p>
                  <p className="mt-0.5 font-mono text-[0.82rem] text-text" dir="ltr">
                    {coverage.urlCandidates}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex shrink-0 flex-col items-center gap-4">
          <EvidenceCompassGauge
            assessment={assessment}
            reducedMotion={reducedMotion}
          />
          {detectorAvailability && (
            <DetectorStatusCard
              detectorA={detectorAvailability.detectorA}
              detectorB={detectorAvailability.detectorB}
              univfd={detectorAvailability.univfd}
            />
          )}
        </div>
      </div>
    </section>
  )
}


/* ============================================================
   DETECTOR STATUS CARD

   Technically informative, visually clean. Reports each detector's
   real role and availability without implying a recommendation.

     Detector A       RESEARCH ADVISORY ONLY
     Detector B       SHADOW DIAGNOSTICS — NEVER PROMOTED
     UnivFD           BENCHMARK CANDIDATE — NOT PROMOTED

   The three-axis panel exists so a reader can see exactly which
   pipeline ran, which are advisory, and which are excluded from the
   canonical verdict. No detector is ever merged into a combined
   number — this is a transparency panel, not a consensus.
   ============================================================ */

interface DetectorStatusCardProps {
  detectorA: 'available' | 'unavailable' | 'ran_but_disagreed'
  detectorB: 'available' | 'unavailable' | 'ran_but_disagreed'
  univfd: 'available' | 'unavailable' | 'ran_but_disagreed'
}

const ROLES: Record<
  string,
  {
    label: string
    state:
      | 'researchAdvisory'
      | 'shadowDiagnostics'
      | 'benchmarkCandidate'
  }
> = {
  detectorA: {
    label: 'Detector A (EfficientNet-B0)',
    state: 'researchAdvisory',
  },
  detectorB: {
    label: 'Detector B (CLIP probe)',
    state: 'shadowDiagnostics',
  },
  univfd: { label: 'UnivFD', state: 'benchmarkCandidate' },
}

const ROLE_COLOR: Record<
  'researchAdvisory' | 'shadowDiagnostics' | 'benchmarkCandidate',
  string
> = {
  researchAdvisory: 'var(--color-intel)',
  shadowDiagnostics: 'var(--color-caution)',
  benchmarkCandidate: 'var(--color-text-dim)',
}

const STATUS_FRAGMENT: Record<
  'available' | 'unavailable' | 'ran_but_disagreed',
  string
> = {
  available: 'result.detectorAvailable',
  unavailable: 'result.detectorUnavailable',
  ran_but_disagreed: 'result.detectorDisagreed',
}

export function DetectorStatusCard({
  detectorA,
  detectorB,
  univfd,
}: DetectorStatusCardProps) {
  const { t } = useI18n()

  return (
    <div className="w-full max-w-xs rounded-xl border border-line/60 bg-surface-inset/40 p-4">
      <p className="mono-label text-[0.6rem] uppercase tracking-[0.14em] text-text-dim">
        {t('result.detectorStatus')}
      </p>

      {Object.entries(ROLES).map(([key, { label, state }]) => {
        const status = (() => {
          switch (key) {
            case 'detectorA':
              return detectorA
            case 'detectorB':
              return detectorB
            case 'univfd':
              return univfd
          }
        })() as 'available' | 'unavailable' | 'ran_but_disagreed'

        return (
          <div key={key} className="mt-3 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5 min-w-0">
              <span className="shrink-0">
                {state === 'researchAdvisory' ? (
                  <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-intel" />
                ) : state === 'shadowDiagnostics' ? (
                  <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-caution" />
                ) : (
                  <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-text-dim" />
                )}
              </span>
              <span className="truncate text-[0.76rem] text-text">{label}</span>
            </div>
            <span
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[0.62rem] font-normal',
                ROLE_COLOR[state],
                'border-transparent',
              )}
              style={{
                borderColor: `${ROLE_COLOR[state]}30`,
                backgroundColor: `${ROLE_COLOR[state]}10`,
              }}
            >
              {t(STATUS_FRAGMENT[status])}
            </span>
          </div>
        )
      })}
    </div>
  )
}
