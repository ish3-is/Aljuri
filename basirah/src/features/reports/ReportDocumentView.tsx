import basirahMark from '../../assets/basirah-mark.png'
import { useI18n } from '../../i18n/useI18n'
import { cn } from '../../lib/utils'
import { formatScore, formatOffset } from '../../lib/utils'
import { RISK_LABEL_KEYS } from './reportModel'
import type {
  ReportClaim,
  ReportClaimKind,
  ReportDocument,
  ReportModality,
} from '../../types/report'
import type { TranslationKey } from '../../i18n/translations'

/* ============================================================
   THE REPORT DOCUMENT

   This component IS the print artefact. The print stylesheet hides
   everything that is not `.basirah-report`, so what prints is
   exactly the tree below and nothing else — no app nav, no ambient
   background, no interactive controls (the stylesheet removes
   buttons outright).

   It is bilingual in the structural sense, not just the cosmetic
   one: `dir` is inherited from the document, every block uses
   logical properties, and the Latin-only values (URLs, filenames,
   ids, timestamps, forensic numbers) are wrapped in `ltr-embed` so
   they keep LTR ordering inside an RTL page. That is what makes the
   Arabic report a genuine RTL document rather than English text
   aligned to the right.
   ============================================================ */

const MODALITY_LABEL_KEYS = {
  image: 'reports.modalities.image',
  screenshot: 'reports.modalities.screenshot',
  qr: 'reports.modalities.qr',
  url: 'reports.modalities.url',
  text: 'reports.modalities.text',
  file: 'reports.modalities.file',
} as const satisfies Record<ReportModality, TranslationKey>

/* ------------------------------------------------------------------ */
/* Section wrapper                                                      */
/* ------------------------------------------------------------------ */

function Block({
  title,
  children,
  pageBreak = false,
}: {
  title: string
  children: React.ReactNode
  pageBreak?: boolean
}) {
  return (
    <section
      data-print-block={pageBreak ? 'page' : undefined}
      className="mt-8 first:mt-0"
    >
      <h3 className="font-arabic-display mb-3 text-[0.82rem] tracking-[0.16em] text-text-dim uppercase">
        {title}
      </h3>
      {children}
    </section>
  )
}

/* ------------------------------------------------------------------ */
/* Claim buckets                                                        */
/* ------------------------------------------------------------------ */

/**
 * The four epistemic buckets, in the order a reader needs them.
 *
 * The ORDER is the argument: measurements first (so the reader has
 * the raw material), then the model's conclusions (which depend on
 * those measurements), then the weak signals (which support
 * everything but decided nothing), then what could NOT be
 * established. Putting unavailable evidence LAST but always present
 * is deliberate — a reader who stops after the inferences has still
 * seen the gap list, because it is the section that closes the
 * evidence argument before the fusion explanation.
 */
const CLAIM_SECTIONS: {
  kind: ReportClaimKind
  titleKey: 'reportSections.verifiedFacts'
    | 'reportSections.modelInferences'
    | 'reportSections.heuristicSignals'
    | 'reportSections.unavailableEvidence'
  subtitleKey:
    | 'reportSections.verifiedFactsSub'
    | 'reportSections.modelInferencesSub'
    | 'reportSections.heuristicSignalsSub'
    | 'reportSections.unavailableEvidenceSub'
  tone: string
}[] = [
  {
    kind: 'verifiedFact',
    titleKey: 'reportSections.verifiedFacts',
    subtitleKey: 'reportSections.verifiedFactsSub',
    tone: 'text-trusted',
  },
  {
    kind: 'modelInference',
    titleKey: 'reportSections.modelInferences',
    subtitleKey: 'reportSections.modelInferencesSub',
    tone: 'text-signal',
  },
  {
    kind: 'heuristicSignal',
    titleKey: 'reportSections.heuristicSignals',
    subtitleKey: 'reportSections.heuristicSignalsSub',
    tone: 'text-caution',
  },
  {
    kind: 'unavailableEvidence',
    titleKey: 'reportSections.unavailableEvidence',
    subtitleKey: 'reportSections.unavailableEvidenceSub',
    tone: 'text-caution',
  },
]

/**
 * One claim line.
 *
 * `source` is rendered LTR in mono so a reader can trace any line
 * back to the module that produced it. A claim without a traceable
 * source is an assertion, and this document is not making those.
 */
function ClaimLine({ item }: { item: ReportClaim }) {
  const { pick } = useI18n()
  return (
    <li
      data-print-block
      data-claim-kind={item.kind}
      className="border-b border-line/40 py-2.5 last:border-b-0"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <span className="font-arabic-body text-[0.82rem] text-text">
          {pick({ en: item.labelEn, ar: item.labelAr })}
        </span>
        <span className="mono-label text-text-dim/70">{item.source}</span>
      </div>
      <p className="font-arabic-body mt-1 text-[0.76rem] leading-relaxed text-text-muted">
        {pick({ en: item.detailEn, ar: item.detailAr })}
      </p>
    </li>
  )
}

/* ------------------------------------------------------------------ */
/* Key-value table                                                      */
/* ------------------------------------------------------------------ */

function Row({ label, value, latin = false }: { label: string; value: string; latin?: boolean }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 border-b border-line/50 py-2 last:border-b-0">
      <span className="text-[0.78rem] text-text-dim">{label}</span>
      <span
        className={
          latin
            ? 'ltr-embed max-w-[62%] text-end text-[0.78rem] break-words text-text'
            : 'max-w-[62%] text-end font-arabic-body text-[0.78rem] break-words text-text'
        }
      >
        {value}
      </span>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Project stamp                                                        */
/* ------------------------------------------------------------------ */

/**
 * The BASIRAH project seal.
 *
 * Deliberately NOT the University of Bisha mark: that logo is an
 * institutional identifier for an academic affiliation, and reusing
 * it as a certification stamp on an analysis document would imply
 * the university validated the report. It never certified anything.
 * The affiliation appears once, as text, in the header — which is
 * what it actually is.
 */
function ReportStamp({ reportId, createdLabel }: { reportId: string; createdLabel: string }) {
  const { t, language } = useI18n()
  const isArabic = language === 'ar'

  return (
    <div className="flex items-center gap-5">
      <div
        aria-hidden
        className="flex size-[104px] shrink-0 rotate-[-6deg] flex-col items-center justify-center gap-0.5 rounded-full border-2 border-signal/45 text-center"
        style={{
          boxShadow: 'inset 0 0 0 4px color-mix(in srgb, var(--bas-surface) 70%, transparent)',
        }}
      >
        <span dir="ltr" className="text-[0.6rem] tracking-[0.34em] text-signal">
          {t('reports.stamp.project')}
        </span>
        <span
          className="font-arabic-emph px-2 text-[0.56rem] leading-tight text-text-dim"
          lang={isArabic ? 'ar' : 'en'}
        >
          {isArabic ? t('reports.stamp.descriptorAr') : t('reports.stamp.descriptorEn')}
        </span>
        <span aria-hidden className="h-px w-8 bg-signal/40" />
        <span
          className="font-arabic-emph px-2 text-[0.52rem] leading-tight text-text-dim"
          lang={isArabic ? 'ar' : 'en'}
        >
          {isArabic ? t('reports.stamp.titleAr') : t('reports.stamp.titleEn')}
        </span>
      </div>

      <div className="min-w-0 flex-1">
        <p className="mono-label text-text-dim">{t('reports.stampArea')}</p>
        <p dir="ltr" className="ltr-embed mt-1.5 text-[0.8rem] text-text">
          {reportId}
        </p>
        <p className="mt-1 text-[0.72rem] text-text-dim">{createdLabel}</p>
        <p className="mt-2 max-w-md font-arabic-body text-[0.68rem] leading-relaxed text-text-dim">
          {t('reports.stampLine')}
        </p>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* The report                                                           */
/* ------------------------------------------------------------------ */

interface ReportDocumentViewProps {
  report: ReportDocument
}

export function ReportDocumentView({ report }: ReportDocumentViewProps) {
  const { t, tLatin, language, pick } = useI18n()
  const isArabic = language === 'ar'

  const created = new Date(report.createdAt)
  const createdLabel = created.toLocaleString(
    isArabic ? 'ar-SA' : 'en-GB',
    { dateStyle: 'medium', timeStyle: 'short' },
  )

  // Both languages were written into the document at generation
  // time from one result, so this is a lookup rather than a
  // translation performed at render.
  const assessment = isArabic
    ? (report.assessmentAr ?? report.assessment)
    : report.assessment

  const summary = isArabic
    ? (report.overallAssessmentAr || report.overallAssessment)
    : report.overallAssessment

  const riskLabel = t(RISK_LABEL_KEYS[report.riskLevel])

  return (
    <article className="basirah-report mx-auto max-w-[860px] px-5 py-4 sm:px-8">
      {/* ================= HEADER ================= */}
      <header
        data-print-block
        className="flex flex-wrap items-start justify-between gap-6 border-b border-line pb-6"
      >
        <div className="min-w-0">
          <img
            src={basirahMark}
            alt=""
            width={44}
            height={62}
            decoding="async"
            className="h-14 w-auto object-contain"
          />
          <h1
            dir="ltr"
            className="mt-3 text-[1.05rem] tracking-[0.22em] text-text"
          >
            {tLatin('brand.name')}
          </h1>
          <p className="font-arabic-body mt-1 text-[0.74rem] text-text-dim">
            {t('brand.subtitle')}
          </p>
        </div>

        <div className="min-w-0 text-end">
          {/* Academic affiliation as TEXT, not as a seal. */}
          <p className="mono-label text-text-dim">{t('team.universityTitle')}</p>
          <p className="font-arabic-body mt-1 text-[0.78rem] text-text-muted">
            {t('team.universityName')}
          </p>
          <p className="font-arabic-body text-[0.68rem] text-text-dim">
            {t('team.universitySub')}
          </p>
        </div>
      </header>

      {/* ---- report metadata ---- */}
      <div className="mt-6">
        <Row label={t('reports.reportId')} value={report.reportId} latin />
        <Row label={t('reports.created')} value={createdLabel} />
        <Row label={t('reports.modality')} value={t(MODALITY_LABEL_KEYS[report.modality])} />
        <Row label={t('reports.item')} value={report.inputSummary} latin />
      </div>

      {/* ================= EXECUTIVE SUMMARY ================= */}
      <Block title={t('reports.executiveSummary')}>
        <p className="font-arabic-body text-[0.86rem] leading-relaxed text-text-muted">
          {summary}
        </p>
      </Block>

      {/* ================= ASSESSMENT ================= */}
      <Block title={t('reports.assessment')}>
        <div className="grid gap-x-8 gap-y-2 sm:grid-cols-3">
          <div>
            <p className="mono-label text-text-dim">{t('charts.labelAssessment')}</p>
            <p className="font-arabic-body mt-1 text-[0.9rem] text-signal">
              {assessment ?? '—'}
            </p>
          </div>
          <div>
            <p className="mono-label text-text-dim">{t('charts.labelTrust')}</p>
            {/* The score is a measured number, so it renders in the
                Latin mono face in BOTH languages. */}
            <p dir="ltr" className="ltr-embed mt-1 text-[0.9rem] text-text">
              {formatScore(report.trust)} {t('score.outOf')}
            </p>
          </div>
          <div>
            <p className="mono-label text-text-dim">{t('charts.labelRisk')}</p>
            {/* Risk band in WORDS, never as colour alone. */}
            <p className="font-arabic-body mt-1 text-[0.9rem] text-text">
              {riskLabel}
            </p>
          </div>
        </div>
        {/* Stated as "not measured" rather than as a zero when the
            pipeline published no confidence figure. */}
        <p className="font-arabic-body mt-3 text-[0.7rem] text-text-dim">
          {t('score.confidenceLabel')}:{' '}
          {report.confidence === null ? (
            <span>{t('reports.notMeasured')}</span>
          ) : (
            <span dir="ltr" className="ltr-embed">
              {formatScore(report.confidence)}
            </span>
          )}
        </p>
      </Block>

      {/* ================= TRUST DNA ================= */}
      <Block title={t('reports.dnaSummary')}>
        <div className="border-y border-line/60">
          {report.dna.map((axis) => (
            <div
              key={axis.axis}
              className="flex items-center justify-between gap-4 border-b border-line/40 py-2 last:border-b-0"
            >
              <span className="font-arabic-body text-[0.78rem] text-text-muted">
                {t(axis.labelKey)}
              </span>
              <span className="flex items-center gap-3">
                {/* An unmeasured axis shows words, not a zero. */}
                <span className="font-arabic-body text-[0.72rem] text-text-dim">
                  {axis.value === null ? t('reports.notMeasured') : null}
                </span>
                {axis.value !== null && (
                  <>
                    <span
                      aria-hidden
                      className="h-1 w-24 overflow-hidden rounded-full bg-line"
                    >
                      <span
                        className="block h-full rounded-full bg-signal/70"
                        style={{ width: `${Math.max(0, Math.min(100, axis.value))}%` }}
                      />
                    </span>
                    <span dir="ltr" className="ltr-embed w-6 text-[0.78rem] text-text">
                      {formatScore(axis.value)}
                    </span>
                  </>
                )}
              </span>
            </div>
          ))}
        </div>
        <p className="font-arabic-body mt-2 text-[0.68rem] text-text-dim">
          {t('dna.scaleLabel')}
        </p>
      </Block>

      {/* ================= FACT / INFERENCE SEPARATION =================
          Rendered immediately after the assessment and BEFORE the
          evidence graph, because everything below it is elaboration
          on these four buckets. A reader who takes only this section
          still gets the honest version of the analysis. */}
      {report.claims.length > 0 &&
        CLAIM_SECTIONS.map((section) => {
          const items = report.claims.filter((item) => item.kind === section.kind)
          if (items.length === 0) return null
          return (
            <Block key={section.kind} title={t(section.titleKey)}>
              <p className="font-arabic-body mb-3 text-[0.72rem] leading-relaxed text-text-dim">
                {t(section.subtitleKey)}
              </p>
              <div
                className={cn(
                  'border-s-2 ps-4',
                  section.kind === 'verifiedFact' && 'border-trusted/40',
                  section.kind === 'modelInference' && 'border-signal/40',
                  section.kind === 'heuristicSignal' && 'border-caution/35',
                  section.kind === 'unavailableEvidence' && 'border-caution/50',
                )}
              >
                {items.map((item) => (
                  <ClaimLine key={item.id} item={item} />
                ))}
              </div>
            </Block>
          )
        })}

      {/* ================= KEY EVIDENCE ================= */}
      <Block title={t('reports.keyEvidence')}>
        {report.evidence.length === 0 ? (
          <p className="font-arabic-body text-[0.8rem] text-text-dim">
            {t('reports.noEvidence')}
          </p>
        ) : (
          <ul className="space-y-3">
            {report.evidence.map((item) => (
              <li key={item.id} data-print-block className="border-s border-line ps-4">
                <p className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <span className="font-arabic-body text-[0.84rem] text-text">
                    {item.label}
                  </span>
                  {/* Polarity as a word plus a rule weight, never as a
                      colour a reader might not perceive. */}
                  <span className="mono-label text-text-dim">
                    {item.polarity}/{item.weight}
                  </span>
                </p>
                <p className="font-arabic-body mt-1 text-[0.76rem] leading-relaxed text-text-muted">
                  {item.detail}
                </p>
              </li>
            ))}
          </ul>
        )}
      </Block>

      {/* ---- URL signals: URL modality only ---- */}
      {report.urlSignals.length > 0 && (
        <Block title={t('explanation.secondaryLabel')}>
          <div className="border-y border-line/60">
            {report.urlSignals.map((signal, index) => (
              <Row
                key={`${signal.labelKey}-${index}`}
                label={t(signal.labelKey)}
                value={pick({ en: signal.valueEn, ar: signal.valueAr })}
              />
            ))}
          </div>
        </Block>
      )}

      {/* ---- metadata: image modality only ---- */}
      {report.metadata.length > 0 && (
        <Block title={t('reports.metadataSection')}>
          <div className="border-y border-line/60">
            {report.metadata.map((row) => (
              <Row
                key={row.labelKey}
                label={t(row.labelKey)}
                value={pick({ en: row.valueEn, ar: row.valueAr })}
              />
            ))}
          </div>
        </Block>
      )}

      {/* ---- provenance: image modality only ---- */}
      {report.provenance.length > 0 && (
        <Block title={t('image.provenance.title')}>
          {report.provenance.map((row, index) => (
            <div key={index} data-print-block className="mb-3 last:mb-0">
              <Row
                label={t(row.statusKey)}
                value={pick({ en: row.statusEn, ar: row.statusAr })}
              />
              <p className="font-arabic-body mt-1.5 text-[0.74rem] leading-relaxed text-text-dim">
                {pick({ en: row.limitationEn, ar: row.limitationAr })}
              </p>
            </div>
          ))}
        </Block>
      )}

      {/* ---- forensics: image modality only ---- */}
      {report.forensics.length > 0 && (
        <Block title={t('image.forensics.title')}>
          <div className="space-y-3">
            {report.forensics.map((row) => (
              <div key={row.name} data-print-block>
                <div className="flex items-baseline justify-between gap-4">
                  <span className="ltr-embed text-[0.8rem] text-text" dir="ltr">
                    {row.name}
                  </span>
                  <span className="ltr-embed text-[0.8rem] text-signal" dir="ltr">
                    {row.value === null ? t('image.forensics.notMeasured') : formatScore(row.value)}
                  </span>
                </div>
                <p className="font-arabic-body mt-1 text-[0.74rem] leading-relaxed text-text-muted">
                  {pick({ en: row.meaningEn, ar: row.meaningAr })}
                </p>
                {/* The "does not mean" line travels with the finding,
                    on paper exactly as on screen. */}
                <p className="font-arabic-body mt-0.5 text-[0.72rem] leading-relaxed text-caution">
                  {pick({ en: row.doesNotMeanEn, ar: row.doesNotMeanAr })}
                </p>
              </div>
            ))}
          </div>
        </Block>
      )}

      {/* ================= HOW THE FUSION DECIDED =================
          The backend's own account of how it ranked the evidence.
          Placed after the claims and before the timeline so the
          reader has the reasoning and the resulting measurements
          adjacent. */}
      {report.fusionExplanationEn && (
        <Block title={t('reportSections.fusionExplanation')}>
          <p className="font-arabic-body text-[0.8rem] leading-relaxed text-text-muted">
            {isArabic ? report.fusionExplanationAr || report.fusionExplanationEn : report.fusionExplanationEn}
          </p>
        </Block>
      )}

      {/* ================= TIMELINE ================= */}
      <Block title={t('reports.timelineSection')}>
        {report.timeline.length === 0 ? (
          <p className="font-arabic-body text-[0.8rem] text-text-dim">
            {t('reports.noTimeline')}
          </p>
        ) : (
          <ol className="space-y-1.5">
            {report.timeline.map((item, index) => (
              <li
                key={`${item.stage}-${index}`}
                data-print-block
                className="flex items-baseline gap-4"
              >
                <span dir="ltr" className="ltr-embed w-16 shrink-0 text-[0.72rem] text-text-dim">
                  {formatOffset(item.offsetSeconds)}
                </span>
                <span className="font-arabic-body text-[0.8rem] text-text-muted">
                  {t(`journey.stages.${item.stage}` as TranslationKey)}
                </span>
              </li>
            ))}
          </ol>
        )}
      </Block>

      {/* ================= MODEL DISCLOSURE ================= */}
      <Block title={t('reports.modelSection')}>
        <div className="border-y border-line/60">
          <Row label={t('image.model.name')} value={report.modelInfo.engine} latin />
          <Row
            label={t('image.model.statusLabel')}
            value={pick({
              en: report.modelInfo.statusEn,
              ar: report.modelInfo.statusAr,
            })}
          />
          <Row
            label={t('image.model.advisoryLabel')}
            value={report.modelInfo.advisoryOnly ? t('common.yes') : t('common.no')}
          />
          <Row
            label={t('image.model.enforcementLabel')}
            value={
              report.modelInfo.fitForAutomatedEnforcement
                ? t('common.yes')
                : t('common.no')
            }
          />
        </div>

        <div className="mt-3">
          <p className="mono-label text-text-dim">
            {t('image.model.limitationsTitle')}
          </p>
          {report.modelInfo.limitationsEn.length === 0 ? (
            <p className="font-arabic-body mt-1 text-[0.74rem] text-text-dim">
              {t('reports.noLimitations')}
            </p>
          ) : (
            <ul className="mt-1.5 space-y-1.5">
              {report.modelInfo.limitationsEn.map((_limitation, index) => (
                <li
                  key={index}
                  data-print-block
                  className="flex gap-2 font-arabic-body text-[0.74rem] leading-relaxed text-text-muted"
                >
                  <span aria-hidden className="text-text-dim">
                    ·
                  </span>
                  <span>
                    {pick({
                      en: report.modelInfo.limitationsEn[index],
                      ar: report.modelInfo.limitationsAr[index],
                    })}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Block>

      {/* ================= TEAM ================= */}
      <Block title={t('reports.teamSection')}>
        <ul className="grid gap-x-6 gap-y-1.5 sm:grid-cols-2">
          {report.team.map((member) => (
            <li key={member.studentId} className="flex items-baseline gap-2">
              <span className="font-arabic-body text-[0.76rem] text-text-muted">
                {member.name}
              </span>
              <span dir="ltr" className="ltr-embed text-[0.66rem] text-text-dim">
                {member.studentId}
              </span>
              {member.isLeader && (
                <span className="text-[0.62rem] text-signal">
                  {t('team.leader')}
                </span>
              )}
            </li>
          ))}
        </ul>
      </Block>

      {/* ================= DISCLAIMER ================= */}
      <Block title={t('reports.safetySection')}>
        <div className="rounded-md border border-caution/35 bg-caution/[0.06] p-4">
          <p className="font-arabic-body text-[0.8rem] leading-relaxed text-text">
            {t('reports.disclaimer')}
          </p>
        </div>
      </Block>

      {/* ================= STAMP ================= */}
      <div className="mt-8 border-t border-line pt-6">
        <ReportStamp reportId={report.reportId} createdLabel={createdLabel} />
      </div>
    </article>
  )
}