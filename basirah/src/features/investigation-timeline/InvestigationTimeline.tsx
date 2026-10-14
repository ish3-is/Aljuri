import { motion } from 'motion/react'
import { useI18n } from '../../i18n/useI18n'
import { formatOffset } from '../../lib/utils'
import { STAGE_LABEL_KEY } from '../analysis/stageModel'
import type { TimelineEntry } from '../../types/analysis'

/* ============================================================
   INVESTIGATION TIMELINE

   Forensic record styling: a monospace clock offset, a stage name, and
   a spine that draws downward as entries arrive. The timestamps are
   synthetic but formatted as captured evidence offsets, which is the
   register the product wants.
   ============================================================ */

interface InvestigationTimelineProps {
  entries: TimelineEntry[]
  /** Stagger in seconds; entries land progressively. */
  pace?: number
}

export function InvestigationTimeline({
  entries,
  pace = 0.14,
}: InvestigationTimelineProps) {
  const { t, language } = useI18n()
  const isArabic = language === 'ar'

  return (
    <div>
      <ol className="relative space-y-0">
        {/* Spine */}
        <motion.span
          aria-hidden
          initial={{ scaleY: 0 }}
          animate={{ scaleY: 1 }}
          transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
          className="absolute inset-y-0 start-[3px] w-px origin-top bg-gradient-to-b from-signal/50 via-line to-transparent"
        />

        {entries.map((entry, index) => {
          const label = t(STAGE_LABEL_KEY[entry.stage])
          const isLast = index === entries.length - 1

          return (
            <motion.li
              key={entry.id}
              initial={{ opacity: 0, x: isArabic ? -10 : 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{
                delay: index * pace,
                duration: 0.45,
                ease: [0.16, 1, 0.3, 1],
              }}
              className="relative flex items-baseline gap-4 ps-7 py-2"
            >
              {/* Node marker */}
              <span
                aria-hidden
                className={`absolute start-0 top-[0.85rem] size-[7px] rounded-full border transition-colors ${
                  isLast
                    ? 'border-signal bg-signal'
                    : 'border-line-bright bg-surface'
                }`}
              />

              {/* Forensic clock */}
              <time
                dir="ltr"
                className="mono-label w-20 shrink-0 text-text-dim tabular-nums"
              >
                {formatOffset(entry.offsetSeconds)}
              </time>

              <span
                className={
                  isLast
                    ? 'text-[0.85rem] text-signal'
                    : 'text-[0.85rem] text-text-muted'
                }
              >
                {label}
              </span>
            </motion.li>
          )
        })}
      </ol>

      {entries.length === 0 && (
        <p className="text-sm text-text-dim">{t('timeline.emptyState')}</p>
      )}
    </div>
  )
}
