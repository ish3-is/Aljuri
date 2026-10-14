import type { ReactNode } from 'react'
import { motion } from 'motion/react'
import { useI18n } from '../../i18n/useI18n'
import { cn } from '../../lib/utils'

/* ============================================================
   SHARED RESULT-VIEW PRIMITIVES

   The result page is provenance-first, which means the reading
   order is a product decision, not a stack of cards. These four
   small pieces let every panel speak the same visual language
   without each one re-deriving it:

     · ResultSection  — numbered heading + hairline
     · FieldRow       — label / value pair, LTR-safe for URLs & ids
     · StatBlock      — a single measured number with its unit
     · NoteBlock      — a stated caveat or limit

   Everything here renders a value it was GIVEN. None of these
   components compute, average, round into a verdict, or fill a gap
   with a plausible default — an absent measurement renders as an
   explicit "not measured", because that is the only honest option.
   ============================================================ */

/* ------------------------------------------------------------------ */
/* Section wrapper                                                     */
/* ------------------------------------------------------------------ */

interface ResultSectionProps {
  index: string
  title: string
  subtitle?: string
  children: ReactNode
  className?: string
}

export function ResultSection({
  index,
  title,
  subtitle,
  children,
  className,
}: ResultSectionProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className={cn('rounded-lg border border-line/70 bg-surface/40 p-5 sm:p-6', className)}
    >
      <div className="mb-5 flex items-center gap-3">
        <span className="mono-label text-signal/70">{index}</span>
        <h2 className="text-sm tracking-tight text-text">{title}</h2>
        <span aria-hidden className="hairline h-px flex-1" />
      </div>
      {subtitle && (
        <p className="mb-5 text-[0.76rem] leading-relaxed text-text-dim">{subtitle}</p>
      )}
      {children}
    </motion.section>
  )
}

/* ------------------------------------------------------------------ */
/* Field row                                                           */
/* ------------------------------------------------------------------ */

interface FieldRowProps {
  label: string
  /** Rendered verbatim. Use `latin` for URLs, ids and model names. */
  value: string
  /**
   * Force LTR isolation. Required for anything URL-shaped or
   * identifier-shaped inside an Arabic page: without it, a trailing
   * `/path` visually reorders to the front of the string and the
   * reader sees a different address than the one that was scored.
   */
  latin?: boolean
  tone?: 'default' | 'risk' | 'caution' | 'trust'
  /** Long technical values (validator warnings, notes) wrap. */
  wrap?: boolean
}

const TONE_CLASS: Record<NonNullable<FieldRowProps['tone']>, string> = {
  default: 'text-text',
  risk: 'text-danger',
  caution: 'text-caution',
  trust: 'text-trusted',
}

export function FieldRow({
  label,
  value,
  latin = false,
  tone = 'default',
  wrap = false,
}: FieldRowProps) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-5 gap-y-1 border-b border-line/40 py-2 last:border-b-0">
      <dt className="text-[0.75rem] text-text-dim">{label}</dt>
      <dd
        dir={latin ? 'ltr' : undefined}
        className={cn(
          'ltr-embed max-w-[68%] text-end text-[0.76rem]',
          latin ? '' : 'font-arabic-body',
          wrap ? 'break-words' : '',
          TONE_CLASS[tone],
        )}
      >
        {value}
      </dd>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Stat block                                                          */
/* ------------------------------------------------------------------ */

interface StatBlockProps {
  label: string
  value: string
  hint?: string
  tone?: 'default' | 'risk' | 'caution' | 'trust'
  latin?: boolean
}

/**
 * One measured number, stated with its unit and its meaning.
 *
 * A stat block never shows a bare percentage: `hint` carries what the
 * number is and, where the pipeline says so, what it is not. A number
 * without its qualifier is the fastest way to overstate a
 * probabilistic model.
 */
export function StatBlock({
  label,
  value,
  hint,
  tone = 'default',
  latin = true,
}: StatBlockProps) {
  const valueClass =
    tone === 'risk'
      ? 'text-danger'
      : tone === 'caution'
        ? 'text-caution'
        : tone === 'trust'
          ? 'text-trusted'
          : 'text-text'

  return (
    <div className="rounded-md border border-line/60 bg-surface-inset/40 px-4 py-3">
      <p className="mono-label text-text-dim">{label}</p>
      <p
        dir={latin ? 'ltr' : undefined}
        className={cn(
          'mt-1.5 text-[1.05rem] leading-tight',
          latin ? 'ltr-embed' : 'font-arabic-body',
          valueClass,
        )}
      >
        {value}
      </p>
      {hint && (
        <p className="font-arabic-body mt-1 text-[0.68rem] leading-relaxed text-text-dim">
          {hint}
        </p>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Note block                                                          */
/* ------------------------------------------------------------------ */

interface NoteBlockProps {
  children: ReactNode
  /**
   * `trust` exists so a positive finding can be stated in words as
   * well as in colour. A ground-truth match that agreed with the
   * pipeline is a real outcome and deserves a real tone rather than
   * being downgraded to "neutral" for lack of a colour.
   */
  tone?: 'neutral' | 'caution' | 'danger' | 'info' | 'trust'
  className?: string
}

const NOTE_TONE: Record<NonNullable<NoteBlockProps['tone']>, string> = {
  neutral: 'border-line/60 bg-surface-inset/40 text-text-muted',
  caution: 'border-caution/25 bg-caution/[0.05] text-caution',
  danger: 'border-danger/30 bg-danger/[0.06] text-danger',
  info: 'border-signal/25 bg-signal/[0.05] text-signal',
  trust: 'border-trusted/25 bg-trusted/[0.05] text-trusted',
}

/**
 * A stated caveat, limit or absence.
 *
 * This is the component the honesty rules depend on: an "unavailable"
 * or "abstained" state renders as one of these rather than as an empty
 * card, a zero, or a dash that reads like a formatting artefact.
 */
export function NoteBlock({ children, tone = 'neutral', className }: NoteBlockProps) {
  return (
    <p
      className={cn(
        'font-arabic-body rounded-md border px-4 py-3 text-[0.74rem] leading-relaxed',
        NOTE_TONE[tone],
        className,
      )}
    >
      {children}
    </p>
  )
}

/* ------------------------------------------------------------------ */
/* "Did not run" placeholder                                           */
/* ------------------------------------------------------------------ */

/**
 * Shown for a branch the pipeline did not execute.
 *
 * Explicit rather than omitted: a reader comparing two runs needs to
 * tell "nothing was found" apart from "nothing was looked for", and
 * only the second is a statement about the pipeline.
 */
export function DidNotRun({ className }: { className?: string }) {
  const { t } = useI18n()
  return (
    <NoteBlock className={className} tone="neutral">
      {t('result.sectionUnavailable')}
    </NoteBlock>
  )
}
