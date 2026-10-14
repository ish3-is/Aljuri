import { motion } from 'motion/react'
import { useI18n } from '../../i18n/useI18n'
import { clamp } from '../../lib/utils'
import type { AnalysisLane } from '../../types/analysis'
import { ANALYSIS_LANES, LANE_LABEL_KEY, STAGE_LABEL_KEY } from './stageModel'

/* ============================================================
   ANALYSIS JOURNEY

   Renders the fusion topology from the brief:

        INPUT
          ├── URL Intelligence
          ├── Synthetic Media
          ├── Metadata
          ├── Provenance
          └── Identity Analysis
                    ↓
             Evidence Fusion
                    ↓
              Trust Score

   A lane only lights up if it ran for this signal type, and its fill
   derives from the same progress counter the timeline uses — so the
   diagram reports the run rather than decorating it.
   ============================================================ */

interface AnalysisJourneyProps {
  completed: number
  total: number
  lanes: AnalysisLane[]
  active: boolean
}

export function AnalysisJourney({
  completed,
  total,
  active,
  lanes,
}: AnalysisJourneyProps) {
  const { t } = useI18n()
  const ratio = clamp(completed / Math.max(total, 1), 0, 1)
  const percent = Math.round(ratio * 100)
  const fused = ratio > 0.55
  const scored = ratio >= 1

  return (
    <div className="w-full">
      {/* --- Progress meter --- */}
      <div className="mb-5">
        <div className="mb-2 flex items-baseline justify-between gap-3">
          <span className="mono-label text-text-dim">{t('journey.progressLabel')}</span>
          <span className="mono-label text-signal/80" dir="ltr">
            {percent}%
          </span>
        </div>
        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
          aria-label={t('journey.progressLabel')}
          className="h-px w-full overflow-hidden bg-line"
        >
          <motion.div
            className="h-full bg-gradient-to-r from-signal/50 via-signal to-intel"
            animate={{ width: `${percent}%` }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          />
        </div>
      </div>

      {/* --- Topology --- */}
      <div className="space-y-4">
        <div className="flex items-center gap-2.5">
          <span aria-hidden className="size-1.5 rounded-full bg-signal" />
          <span className="mono-label text-signal/85">INPUT</span>
        </div>

        {/* Parallel lanes */}
        <ul className="grid gap-2 sm:grid-cols-2">
          {ANALYSIS_LANES.map((lane, index) => {
            const ran = lanes.includes(lane)
            return (
              <motion.li
                key={lane}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: ran ? 1 : 0.3, y: 0 }}
                transition={{
                  delay: index * 0.06,
                  duration: 0.45,
                  ease: [0.16, 1, 0.3, 1],
                }}
                className={
                  ran
                    ? 'rounded-lg border border-line-bright bg-surface/60 px-3.5 py-2.5'
                    : 'rounded-lg border border-line/40 bg-surface/20 px-3.5 py-2.5'
                }
              >
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={
                      ran
                        ? 'text-[0.82rem] text-text-muted'
                        : 'text-[0.82rem] text-text-dim/50'
                    }
                  >
                    {t(LANE_LABEL_KEY[lane])}
                  </span>
                  <motion.span
                    animate={{ opacity: ran ? 0.9 : 0.3 }}
                    aria-hidden
                    className="mono-label text-signal"
                  >
                    {ran ? '◈' : '·'}
                  </motion.span>
                </div>
              </motion.li>
            )
          })}
        </ul>

        {/* Convergence into fusion */}
        <div className="flex justify-center" aria-hidden>
          <svg width="20" height="24" viewBox="0 0 20 24" fill="none">
            <path
              d="M2 0v12c0 4 3.6 6 8 6s8-2 8-6V0"
              stroke="var(--color-line-bright)"
              strokeWidth="1"
            />
            <motion.path
              d="M10 18v6"
              stroke="var(--color-signal)"
              strokeWidth="1"
              animate={{ opacity: fused ? 0.9 : 0.2 }}
              transition={{ duration: 0.4 }}
            />
          </svg>
        </div>

        {/* Evidence Fusion */}
        <motion.div
          animate={{ opacity: fused ? 1 : 0.45 }}
          transition={{ duration: 0.4 }}
          className="rounded-lg border border-line/80 bg-surface/50 px-4 py-3"
        >
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm text-text">{t('journey.lanes.fusion')}</span>
            <span className="mono-label text-text-dim" dir="ltr">
              {fused ? 'MERGE' : 'READY'}
            </span>
          </div>
        </motion.div>

        {/* Score output */}
        <div className="flex justify-center" aria-hidden>
          <motion.svg
            width="20"
            height="18"
            viewBox="0 0 20 18"
            fill="none"
            animate={{ opacity: fused ? 1 : 0.3 }}
          >
            <path
              d="M10 0v18"
              stroke="var(--color-signal)"
              strokeWidth="1"
              strokeDasharray="3 4"
            />
          </motion.svg>
        </div>

        <motion.div
          animate={{ opacity: scored ? 1 : 0.4 }}
          transition={{ duration: 0.4 }}
          className="rounded-lg border border-signal/25 bg-signal/[0.05] px-4 py-3"
        >
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm text-signal">{t('journey.lanes.score')}</span>
            <span className="mono-label text-signal/70" dir="ltr">
              {scored ? 'DONE' : 'PENDING'}
            </span>
          </div>
        </motion.div>
      </div>

      {/* Screen-reader narrative of what has run so far */}
      <p className="sr-only" aria-live="polite">
        {active
          ? `${t('journey.progressLabel')}: ${percent}%`
          : t(STAGE_LABEL_KEY.score)}
      </p>
    </div>
  )
}
