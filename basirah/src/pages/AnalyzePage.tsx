import { lazy, Suspense } from 'react'
import { useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import {
  File as FileIcon,
  FileText,
  Image as ImageIcon,
  Link2,
  Monitor,
  RotateCcw,
} from 'lucide-react'
import { IntelligenceCore } from '../components/core/IntelligenceCore'
import {
  LiveBadge,
  Magnetic,
  MockBadge,
  Panel,
  SectionLabel,
} from '../components/ui/primitives'
import { AnalysisJourney } from '../features/analysis/AnalysisJourney'
import { STAGE_ORDER } from '../features/analysis/stageModel'
import { InvestigationTimeline } from '../features/investigation-timeline/InvestigationTimeline'
import { EvidenceExplanation } from '../features/result/EvidenceExplanation'
import { EvidenceResultView } from '../features/result/EvidenceResultView'
import { ResultHero } from '../features/result/ResultHero'
import { AnalysisErrorState } from '../features/result/AnalysisErrorState'
import { TrustScore } from '../features/result/TrustScore'
import { ImageVerdictBanner } from '../features/result/ImageVerdictBanner'
import { ImageQualityWarning } from '../features/result/ImageQualityWarning'
import { ImageMetadataPanel } from '../features/result/ImageMetadataPanel'
import { ImageForensicsPanel } from '../features/result/ImageForensicsPanel'
import { ImageProvenancePanel } from '../features/result/ImageProvenancePanel'
import { ModelDisclosureCard } from '../features/result/ModelDisclosureCard'
import { SafetyNotice } from '../features/result/SafetyNotice'
import { TrustDNA } from '../features/trust-dna/TrustDNA'
import {
  buildArabicSummary,
  buildReportDocument,
  assessmentAr,
} from '../features/reports/reportModel'
import { saveReport } from '../features/reports/reportStore'
import {
  UniversalInput,
  type Modality,
} from '../features/universal-input/UniversalInput'
import { useInvestigation } from '../hooks/useInvestigation'
import { usePrefersReducedMotion } from '../hooks/useEnvironment'
import { useI18n } from '../i18n/useI18n'
import { isEvidenceResult } from '../types/analysis'
import type { TimelineEntry } from '../types/analysis'

/**
 * The Evidence Graph is a deferred chunk. It is a substantial
 * interactive SVG tree that only matters once a result exists, and
 * most first-time visitors never reach it — so it loads when the
 * result panel appears rather than on first paint of the app.
 */
const EvidenceGraphView = lazy(() =>
  import('../features/evidence-graph/EvidenceGraphView').then((module) => ({
    default: module.EvidenceGraphView,
  })),
)

/** Same footprint as the graph panel, so nothing shifts on arrival. */
function GraphFallback() {
  return (
    <div
      aria-hidden
      className="mx-auto h-[320px] w-full max-w-[560px] animate-breathe rounded-lg border border-line/40 bg-surface/25"
    />
  )
}

/**
 * While the investigation runs there is no result payload yet, so the
 * timeline is synthesised from the live progress counter. Offsets are
 * derived from the stage index, which keeps the record honest about
 * order even though the times are simulated.
 */
function progressStagesAsEntries(
  completed: number,
  activeStage: TimelineEntry['stage'] | null,
): TimelineEntry[] {
  return STAGE_ORDER.slice(0, Math.max(completed, activeStage ? 1 : 0)).map(
    (stage, index) => ({
      id: `live-${stage}`,
      stage,
      offsetSeconds: index * 0.5,
    }),
  )
}

/* ============================================================
   ANALYSIS WORKSPACE

   The section that runs an investigation. Composition order mirrors
   the lifecycle:
     modality → core → input → (analysing: journey) → (result:
     verdict, score, DNA, explanation, image panels, graph).

   This is the only section kept mounted across navigation — see the
   note in App.tsx. Every result panel below is the real pipeline's
   output; nothing here is re-derived or re-labelled.
   ============================================================ */

export function AnalyzePage() {
  const { t, language } = useI18n()
  const isArabic = language === 'ar'
  const reduced = usePrefersReducedMotion()
  /**
   * FOUR-mode selector. Image is the initial state because image
   * intelligence is the platform's PRIMARY modality.
   *
   * The selector changes which affordance LEADS the layout and which
   * `mode` hint the evidence endpoint receives — it never removes an
   * intake path. BASIRAH still infers the real signal type from the
   * submitted bytes, so selecting Screenshot and dropping a plain
   * photograph is analysed as what it actually is, with the
   * contradiction reported rather than silently obeyed.
   */
  const [modality, setModality] = useState<Modality>('image')

  const { state, signal, progress, result, error, submit, reset, setDragging } =
    useInvestigation({ pace: 380, reduced })

  const isAnalyzing = state === 'analyzing'
  const isResult = state === 'result' && result !== null
  const showJourney = isAnalyzing || isResult
  const showResultPanels = isResult

  /**
   * The image-only panels render from `imageDetail`, which the image
   * provider populates and nothing else does. Checking the field
   * rather than `signal.kind` means a URL result — or any future
   * signal type that produces no image detail — can never fall into
   * an empty image panel, and the panels cannot appear for a payload
   * that never came from the image pipeline.
   */
  const imageDetail = result?.imageDetail ?? null

  /**
   * The evidence result takes the whole result surface.
   *
   * When a payload came from the multimodal endpoint, the legacy
   * score-first stack below is NOT rendered at all: the evidence view
   * leads with the final assessment and carries provenance, agreement
   * and coverage ahead of any number. Rendering a big Trust Score
   * gauge above that would be exactly the inversion the result is
   * ordered to avoid.
   */
  const evidenceResult = result && isEvidenceResult(result) ? result.evidence : null

  /**
 * Issue a written report from the result on screen.
   *
   * The report is stored locally and the reader is taken to the
   * Reports Center with it. Nothing is uploaded — a report holds a
   * submitted URL and a set of measurements about someone's content,
   * and there is no server that asked to keep any of that.
   *
   * Both languages are written into the document at generation time,
   * derived from the SAME result, so the Arabic and English renderings
   * can never disagree about what the analysis found.
   */
  const handleGenerateReport = () => {
    if (!result) return
    const report = buildReportDocument(result, {
      summaryAr: buildArabicSummary(result),
      assessmentAr: assessmentAr(result),
    })
    saveReport(report)
    window.location.hash = '/reports'
  }

  return (
    <div className="px-5 pt-28 pb-6 sm:px-8 sm:pt-32">
      <div className="mx-auto flex max-w-[1400px] flex-col items-center">
        {/* ================= WORKSPACE HEADER ================= */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="w-full text-center"
        >
          <p className="mono-label text-text-dim">{t('workspace.subtitle')}</p>
          <h1 className="mt-4 text-3xl leading-tight font-extralight tracking-tight sm:text-4xl">
            <span className="text-gradient-signal">{t('workspace.title')}</span>
          </h1>
        </motion.div>

        {/* ---- Four-mode selector ----
            Image / Screenshot / File are uploads and take the
            emphasised surface; URL is present and labelled as the
            secondary modality rather than hidden. All four stay
            functional at all times — the selector changes emphasis,
            not capability. */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.12, duration: 0.7 }}
          role="group"
          aria-label={t('mode.label')}
          className="mt-8 grid w-full max-w-4xl grid-cols-2 gap-2.5 lg:grid-cols-4"
        >
          {(
            [
              { id: 'image' as const, icon: ImageIcon, titleKey: 'mode.image', noteKey: 'mode.imageNote' },
              { id: 'screenshot' as const, icon: Monitor, titleKey: 'mode.screenshot', noteKey: 'mode.screenshotNote' },
              { id: 'file' as const, icon: FileIcon, titleKey: 'mode.file', noteKey: 'mode.fileNote' },
              { id: 'url' as const, icon: Link2, titleKey: 'mode.url', noteKey: 'mode.urlNote' },
            ] as const
          ).map((option) => {
            const Icon = option.icon
            const active = modality === option.id
            // Image is the primary modality; the other uploads share
            // its signal tone, and URL is deliberately the most
            // restrained of the four.
            const isUrl = option.id === 'url'
            return (
              <button
                key={option.id}
                type="button"
                onClick={() => setModality(option.id)}
                aria-pressed={active}
                className={[
                  'flex items-start gap-3 rounded-lg border px-4 py-3.5 text-start transition-colors duration-200',
                  active
                    ? isUrl
                      ? 'border-caution/40 bg-caution/[0.05]'
                      : 'border-signal/45 bg-signal/[0.07]'
                    : 'border-line/70 bg-surface/35 hover:border-line-bright',
                ].join(' ')}
              >
                <span
                  className={[
                    'mt-0.5 shrink-0',
                    active ? (isUrl ? 'text-caution' : 'text-signal') : 'text-text-dim',
                  ].join(' ')}
                >
                  <Icon size={16} />
                </span>
                <span className="min-w-0">
                  <span
                    className={[
                      'block text-[0.82rem]',
                      active ? (isUrl ? 'text-caution' : 'text-signal') : 'text-text-muted',
                    ].join(' ')}
                  >
                    {t(option.titleKey)}
                  </span>
                  <span className="font-arabic-body mt-1 block text-[0.68rem] leading-relaxed text-text-dim">
                    {t(option.noteKey)}
                  </span>
                </span>
              </button>
            )
          })}
        </motion.div>

        {/* ---- The Core ---- */}
        <motion.div
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2, duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
          className="mt-10 w-full max-w-[440px]"
        >
          {/* The orbital core is the idle/analysing feedback. Once a
              result exists it would fill the entire first screen and
              push the verdict below the fold, so it collapses to give
              the answer the space. Removing decoration in favour of
              the requested result is the right trade. */}
          {result ? (
            <div className="mx-auto h-px w-24 bg-border/40" aria-hidden />
          ) : (
            <IntelligenceCore state={state} riskLevel={null} />
          )}
        </motion.div>

        {/* ---- Universal Input ---- */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
          className="mt-8 w-full max-w-3xl"
        >
          <UniversalInput
            state={state}
            signal={signal}
            modality={modality}
            onSubmit={submit}
            onReset={reset}
            onDragStateChange={setDragging}
          />

          {/* Three-way headline, directly beneath the input the user
              just submitted, so the verdict lands before any
              decoration. LEGACY image-pipeline results only — an
              evidence result gets the full provenance-first view below
              instead, which carries its own leading verdict. */}
          {imageDetail && result && !evidenceResult && (
            <div className="mt-8 w-full max-w-[720px]">
              {/* Both consumers below take a required number, so a
                  null confidence falls back to the image pipeline's own
                  synthetic figure. These branches only render for
                  legacy image results, which always carry one. */}
              <ImageVerdictBanner
                detail={imageDetail}
                confidence={result.confidence ?? 0}
              />
            </div>
          )}
        </motion.div>

        {/* --- Reset affordance --- */}
        <AnimatePresence>
          {(isResult || isAnalyzing) && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              className="mt-6"
            >
              <Magnetic strength={5}>
                <button
                  type="button"
                  onClick={reset}
                  className="inline-flex items-center gap-2 rounded-full border border-line px-4 py-2 text-[0.78rem] text-text-muted transition-colors hover:border-line-bright hover:text-text"
                >
                  <RotateCcw size={13} />
                  {t('actions.newInvestigation')}
                </button>
              </Magnetic>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

        {/* ================= ANALYSIS / RESULT ================= */}
        <AnimatePresence>
          {showJourney && (
            <motion.section
              key="journey"
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 12 }}
              transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
              className="px-5 py-12 sm:px-8"
            >
              <div className="mx-auto max-w-[1400px]">
                <Panel accent className="p-6 sm:p-8">
                  <div className="grid gap-8 lg:grid-cols-2">
                    {/* Journey topology */}
                    <div>
                      <div className="mb-5 flex items-center justify-between gap-3">
                        <h2 className="text-sm text-text">
                          {t('journey.title')}
                        </h2>
                        {/* The badge reflects the ACTUAL provenance of
                            the payload. A real backend result must not be
                            labelled "Mock", or a live result would be
                            presented as simulated. */}
                        {result && result.isMock && (
                          <MockBadge label={t('common.mockBadge')} />
                        )}
                      </div>
                      <AnalysisJourney
                        completed={progress.completed}
                        total={progress.total}
                        lanes={progress.lanes}
                        active={isAnalyzing}
                      />
                    </div>

                    {/* Timeline */}
                    <div>
                      <h2 className="mb-5 text-sm text-text">
                        {t('timeline.title')}
                      </h2>
                      {result ? (
                        <InvestigationTimeline
                          entries={result.timeline}
                          pace={isArabic ? 0.14 : 0.14}
                        />
                      ) : (
                        <InvestigationTimeline
                          entries={progressStagesAsEntries(progress.completed, progress.activeStage)}
                          pace={0.16}
                        />
                      )}
                    </div>
                  </div>
                </Panel>
              </div>
            </motion.section>
          )}
        </AnimatePresence>

        {/* --- Result panels --- */}
        <AnimatePresence>
          {showResultPanels && result && (
            <motion.section
              key="result"
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              className="px-5 py-8 sm:px-8"
            >
              <div className="mx-auto max-w-[1400px] space-y-6">
                {/*
                  The evidence path takes the ENTIRE result surface.
                  It renders its own final assessment first, so the
                  score-first stack below is skipped rather than
                  duplicated — a big gauge above a provenance-first
                  page would undo the ordering.
                */}
                {evidenceResult ? (
                  <EvidenceResultView evidence={evidenceResult} />
                ) : (
                  <>
                {/* ---- Evidence-quality limits, BEFORE any verdict ----
                    A low-resolution or heavily-compressed image can still
                    yield a confident-looking probability. Putting this
                    first is the point: the caveat has to land before
                    the number does. */}
                {imageDetail && (
                  <ImageQualityWarning quality={imageDetail.evidenceQuality} />
                )}

                {/* ResultHero — the premium categorical result surface,
                    leading with the assessment and the animated gauge. */}
                {imageDetail && (
                  <ResultHero
                    detail={imageDetail}
                    finalAssessment={result.finalAssessment}
                    evidenceStrength={
                      imageDetail.evidenceQuality.longEdge >= 1000
                        ? 'high'
                        : imageDetail.evidenceQuality.longEdge > 0
                          ? 'medium'
                          : 'low'
                    }
                    coverage={
                      imageDetail.synthetic.uncertain === true
                        ? { pixelsAnalyzed: imageDetail.fileSizeBytes }
                        : null
                    }
                    detectorAvailability={{
                      detectorA:
                        imageDetail.model.available && imageDetail.synthetic.syntheticProbability != null
                          ? 'available'
                          : 'unavailable',
                      detectorB:
                        imageDetail.model.available && imageDetail.synthetic.syntheticProbability != null
                          ? 'available'
                          : 'unavailable',
                      univfd:
                        imageDetail.model.available && imageDetail.synthetic.syntheticProbability != null
                          ? 'available'
                          : 'unavailable',
                    }}
                    reducedMotion={reduced}
                  />
                )}

                {/* Trust Score */}
                <Panel accent className="p-6 sm:p-8">
                  <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
                    <p className="ltr-embed truncate text-xs text-text-dim">
                      {isArabic ? result.signal.valueAr : result.signal.valueEn}
                    </p>
                    <div className="flex items-center gap-2">
                      {result.isMock ? (
                        <MockBadge label={t('common.mockBadge')} />
                      ) : (
                        <LiveBadge label={t('common.liveBadge')} />
                      )}
                      <span className="mono-label text-text-dim/70" dir="ltr">
                        {result.engine} v{result.engineVersion}
                      </span>
                    </div>
                  </div>
                  <TrustScore
                    score={result.trustScore}
                    riskLevel={result.riskLevel}
                    confidence={result.confidence ?? 0}
                    runKey={result.signal.valueEn + String(result.trustScore)}
                    assessmentLabel={
                      imageDetail?.assessment === 'uncertain'
                        ? 'UNCERTAIN'
                        : undefined
                    }
                  />

                  {/* ---- Issue a written report ----
                      Placed inside the result panel because it acts on
                      THIS result, not on a report the reader has to go
                      and find. It saves locally and navigates to the
                      Reports Center. */}
                  <div className="mt-6 border-t border-line/60 pt-5">
                    <Magnetic strength={5}>
                      <button
                        type="button"
                        onClick={handleGenerateReport}
                        className="inline-flex items-center gap-2 rounded-full border border-signal/35 bg-signal/10 px-4 py-2 text-[0.78rem] text-signal transition-colors duration-200 hover:border-signal/55 hover:bg-signal/15"
                      >
                        <FileText size={13} />
                        {t('reports.generate')}
                      </button>
                    </Magnetic>
                    <p className="font-arabic-body mt-2 max-w-md text-[0.68rem] leading-relaxed text-text-dim">
                      {t('reports.generateHint')}
                    </p>
                  </div>
                </Panel>

                {/* Two-column: DNA + explanation */}
                <div className="grid gap-6 lg:grid-cols-2">
                  <Panel className="p-6">
                    <SectionLabel
                      index="01"
                      title={t('dna.title')}
                      subtitle={
                        t('dna.subtitle')
                      }
                    />
                    <TrustDNA dna={result.dna} />
                  </Panel>

                  <Panel className="p-6">
                    <SectionLabel
                      index="02"
                      title={t('explanation.title')}
                    />
                    <EvidenceExplanation
                      primarySignal={result.primarySignal}
                      secondarySignals={result.secondarySignals}
                    />
                  </Panel>
                </div>

                {/* ---- Image evidence panels ----
                    Only for a payload that came from the image pipeline.
                    Metadata, forensics, provenance and the model
                    disclosure are the raw measurements the generic
                    explanation rail compresses into prose. */}
                {imageDetail && (
                  <>
                    <Panel className="p-6">
                      <SectionLabel
                        index="03"
                        title={t('image.metadata.title')}
                        subtitle={t('image.metadata.subtitle')}
                      />
                      <ImageMetadataPanel
                        metadata={imageDetail.metadata}
                        previewUrl={imageDetail.previewUrl}
                      />
                    </Panel>

                    <Panel className="p-6">
                      <SectionLabel
                        index="04"
                        title={t('image.forensics.title')}
                        subtitle={t('image.forensics.subtitle')}
                      />
                      <ImageForensicsPanel signals={imageDetail.forensics} />
                    </Panel>

                    <Panel className="p-6">
                      <SectionLabel
                        index="05"
                        title={t('image.provenance.title')}
                        subtitle={t('image.provenance.subtitle')}
                      />
                      <ImageProvenancePanel provenance={imageDetail.provenance} />
                    </Panel>

                    <Panel className="p-6">
                      <SectionLabel
                        index="06"
                        title={t('image.model.title')}
                        subtitle={t('image.model.subtitle')}
                      />
                      <ModelDisclosureCard model={imageDetail.model} />
                    </Panel>
                  </>
                )}

                {/* Evidence graph */}
                <Panel className="p-6">
                  <SectionLabel
                    index="07"
                    title={t('graph.title')}
                    subtitle={
                      t('graph.subtitle')
                    }
                  />
                  <Suspense fallback={<GraphFallback />}>
                    <EvidenceGraphView graph={result.graph} />
                  </Suspense>
                </Panel>

                {/* ---- Standing limitation ----
                    Closes the result, and cannot be dismissed. */}
                {imageDetail && <SafetyNotice />}
                  </>
                )}

                {/* ---- Report action ----
                    Outside both branches: a written report can be
                    issued from an evidence result exactly as from a
                    legacy one, and the fact/inference split is what
                    the report mapper now produces. */}
                {evidenceResult && (
                  <div className="border-t border-line/60 pt-5">
                    <Magnetic strength={5}>
                      <button
                        type="button"
                        onClick={handleGenerateReport}
                        className="inline-flex items-center gap-2 rounded-full border border-signal/35 bg-signal/10 px-4 py-2 text-[0.78rem] text-signal transition-colors duration-200 hover:border-signal/55 hover:bg-signal/15"
                      >
                        <FileText size={13} />
                        {t('reports.generate')}
                      </button>
                    </Magnetic>
                    <p className="font-arabic-body mt-2 max-w-md text-[0.68rem] leading-relaxed text-text-dim">
                      {t('reports.generateHint')}
                    </p>
                  </div>
                )}
              </div>
            </motion.section>
          )}
        </AnimatePresence>

        {/* --- Error state --- */}
        <AnimatePresence>
          {state === 'error' && error && (
            <AnalysisErrorState error={error} onReset={reset} />
          )}
        </AnimatePresence>
    </div>
  )
}
