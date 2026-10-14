import { motion } from 'motion/react'
import { useI18n } from '../../i18n/useI18n'
import { cn } from '../../lib/utils'
import type { ModuleState } from '../../data/detectionCategories'

/* ============================================================
   STATE BADGE

   The single component that renders a module's state anywhere in
   the product. Having one implementation is a product-integrity
   control, not just tidiness: it means there is exactly one place
   where a state becomes a colour and a word, so "Planned" can never
   drift into looking active on one page and not another.
   ============================================================ */

/**
 * One palette per state.
 *
 * `researchGrade` and `advisory` are distinct on purpose: the image
 * model is a research candidate and the URL model is advisory — saying
 * "Active" for both would overstate one of them.
 */
const STATE_STYLES: Record<ModuleState, string> = {
  active: 'border-trusted/25 bg-trusted/8 text-trusted/90',
  researchGrade: 'border-signal/30 bg-signal/10 text-signal',
  advisory: 'border-caution/25 bg-caution/8 text-caution/90',
  planned: 'border-line-bright bg-surface-raised/60 text-text-dim',
  comingSoon: 'border-line-bright bg-surface-raised/60 text-text-dim',
  inDevelopment: 'border-intel/30 bg-intel/10 text-[color-mix(in_srgb,var(--color-intel)_82%,white)]',
  expanding: 'border-intel/25 bg-intel/8 text-[color-mix(in_srgb,var(--color-intel)_75%,white)]',
  capability: 'border-signal/20 bg-signal/6 text-signal/80',
  /**
   * LIMITED renders in its own caution family, deliberately NOT the
   * trusted/active green. A partially-supported module must never
   * look fully supported at a glance.
   */
  limited: 'border-caution/30 bg-caution/10 text-caution',
}

/** The dot inside the badge mirrors the border colour family. */
const STATE_DOT: Record<ModuleState, string> = {
  active: 'bg-trusted',
  researchGrade: 'bg-signal',
  advisory: 'bg-caution',
  planned: 'bg-text-dim',
  comingSoon: 'bg-text-dim',
  inDevelopment: 'bg-intel',
  expanding: 'bg-intel/80',
  capability: 'bg-signal/70',
  limited: 'bg-caution',
}

export interface StateBadgeProps {
  state: ModuleState
  /** Overrides the default translation-key lookup. */
  className?: string
  /** Static (non-animated) rendering, for dense grids. */
  still?: boolean
}

export function StateBadge({ state, className, still = false }: StateBadgeProps) {
  const { t } = useI18n()
  const label = t(`state.${state}`)

  return (
    <span
      data-state={state}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1',
        'text-[0.62rem] tracking-[0.14em] uppercase',
        STATE_STYLES[state],
        className,
      )}
    >
      <span aria-hidden className="relative flex size-1">
        {still ? (
          <span className={cn('size-1 rounded-full', STATE_DOT[state])} />
        ) : (
          <>
            <motion.span
              className="absolute inset-0 rounded-full"
              animate={{ opacity: [0.45, 0, 0.45], scale: [1, 2.1, 1] }}
              transition={{ duration: 2.8, repeat: Infinity, ease: 'easeOut' }}
              style={{ backgroundColor: 'currentColor' }}
            />
            <span className={cn('relative size-1 rounded-full', STATE_DOT[state])} />
          </>
        )}
      </span>
      {label}
    </span>
  )
}