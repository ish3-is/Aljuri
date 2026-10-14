import { motion } from 'motion/react'
import { useI18n } from '../../i18n/useI18n'
import { cn } from '../../lib/utils'
import {
  AlertTriangle,
  CheckCircle,
  Circle,
  Clock,
  Gauge,
  HelpCircle,
  Info,
  ShieldAlert,
  FileWarning,
} from 'lucide-react'

/* ============================================================
   WHY THIS RESULT
   Evidence-source explanation panel rendered directly under
   the hero. Every entry is derived from real result fields
   only; nothing here is fabricated or inferred.
   ============================================================ */

export interface WhyReason {
  kind: string
  label: string
  message: string
}

export interface WhyThisResultProps {
  /** Driver-level explanation strings supplied by the result controller. */
  reasons?: WhyReason[]
  /** Whether the mounted route is image-scoped (shows the canonical card). */
  imageScoped?: boolean
  className?: string
}

const REASON_ICONS: Record<string, React.ElementType> = {
  detector_disagreement: AlertTriangle,
  out_of_distribution: Gauge,
  ensemble_abstained: Circle,
  provenance_unavailable: FileWarning,
  provenance_invalid: ShieldAlert,
  evidence_quality_warning: HelpCircle,
  analyzer_unavailable: Clock,
  synthetic_signal_strong: CheckCircle,
  no_synthetic_signal: CheckCircle,
  other: Info,
}

const REASON_COLOUR: Record<string, string> = {
  detector_disagreement: 'text-caution',
  out_of_distribution: 'text-caution',
  ensemble_abstained: 'text-text-muted',
  provenance_unavailable: 'text-text-dim',
  provenance_invalid: 'text-danger',
  evidence_quality_warning: 'text-signal',
  analyzer_unavailable: 'text-text-dim',
  synthetic_signal_strong: 'text-caution',
  no_synthetic_signal: 'text-trusted',
  other: 'text-text-dim',
}

export function WhyThisResult({
  reasons = [],
  imageScoped = true,
  className,
}: WhyThisResultProps) {
  const { t, language } = useI18n()
  const isArabic = language === 'ar'

  if (!imageScoped) {
    return null
  }

  if (reasons.length === 0) {
    return null
  }

  return (
    <section
      className={cn(
        'mt-6 rounded-2xl border border-line/60 bg-surface/30 p-5 sm:p-6',
        className,
      )}
      role="region"
      aria-label={t('result.whyThisResult')}
    >
      <div className="mb-4 flex items-center gap-2.5">
        <AlertTriangle className="h-4 w-4 text-signal" aria-hidden="true" />
        <h2
          className={cn(
            'text-sm tracking-tight text-text',
            isArabic ? 'text-start' : 'text-start',
          )}
        >
          {t('agreement.whyThisResult')}
        </h2>
        <span aria-hidden className="h-px flex-1 bg-line/40" />
      </div>

      <div className="space-y-3">
        {reasons.map((reason, index) => {
          const Icon = REASON_ICONS[reason.kind] ?? Info
          const tone = REASON_COLOUR[reason.kind] ?? 'text-text-dim'

          return (
            <motion.div
              key={reason.kind}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.08 * index, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
              className="flex gap-3"
            >
              <div
                className={cn(
                  'mt-0.5 flex shrink-0 items-center justify-center rounded-lg',
                  tone === 'text-caution'
                    ? 'bg-caution/[0.07]'
                    : tone === 'text-danger'
                      ? 'bg-danger/[0.07]'
                      : tone === 'text-signal'
                        ? 'bg-signal/[0.07]'
                        : tone === 'text-trusted'
                          ? 'bg-trusted/[0.07]'
                          : 'bg-surface-inset/40',
                  'h-8 w-8',
                )}
              >
                <Icon className={cn('h-4 w-4', tone)} aria-hidden="true" />
              </div>
              <div className="min-w-0 flex-1 space-y-1">
                <p
                  className={cn(
                    'text-[0.8rem] leading-snug text-text',
                    isArabic ? 'text-start' : 'text-start',
                  )}
                >
                  {reason.label}
                </p>
                <p
                  className="text-[0.74rem] leading-relaxed text-text-dim"
                  dir={isArabic ? 'rtl' : 'ltr'}
                >
                  {reason.message}
                </p>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Technical detail is out of scope for this component; reasons
          are rendered directly above. */}
    </section>
  )
}
