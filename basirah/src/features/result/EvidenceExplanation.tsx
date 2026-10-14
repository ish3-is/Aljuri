import { motion } from 'motion/react'
import { useI18n } from '../../i18n/useI18n'
import { RISK_COLORS } from '../../data/mockAnalysis'
import type { EvidenceSignal, RiskLevel } from '../../types/analysis'

/* ============================================================
   EVIDENCE EXPLANATION — "Why BASIRAH flagged this"

   Hierarchical by design: the primary signal gets a bordered block with
   narrative weight, secondary signals collapse into a compact metric
   rail. Deliberately NOT a uniform list — a flat list of identical rows
   communicates that all findings carry equal weight, which would be a
   lie about the evidence.
   ============================================================ */

interface EvidenceExplanationProps {
  primarySignal: {
    titleEn: string
    titleAr: string
    bodyEn: string
    bodyAr: string
  } | null
  secondarySignals: EvidenceSignal[]
}

const SEVERITY_COLOR: Record<RiskLevel | 'neutral', string> = {
  high_risk: RISK_COLORS.high_risk,
  caution: RISK_COLORS.caution,
  trusted: RISK_COLORS.trusted,
  neutral: 'var(--color-text-dim)',
}

export function EvidenceExplanation({
  primarySignal,
  secondarySignals,
}: EvidenceExplanationProps) {
  const { t, language } = useI18n()
  const isArabic = language === 'ar'

  return (
    <div className="space-y-5">
      {/* ---------- Primary signal ---------- */}
      {primarySignal ? (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="relative overflow-hidden rounded-lg border border-signal/25 bg-signal/[0.04] p-5"
        >
          <span
            aria-hidden
            className="absolute inset-y-0 start-0 w-px bg-gradient-to-b from-signal/60 to-transparent"
          />
          <p className="mono-label text-signal">{t('explanation.primaryLabel')}</p>
          <h3 className="mt-2.5 text-lg leading-snug font-light text-text">
            {isArabic ? primarySignal.titleAr : primarySignal.titleEn}
          </h3>
          <p className="mt-2.5 text-[0.85rem] leading-relaxed text-text-muted">
            {isArabic ? primarySignal.bodyAr : primarySignal.bodyEn}
          </p>
        </motion.div>
      ) : (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.25, duration: 0.4 }}
          className="rounded-lg border border-line/70 bg-surface/40 p-4 text-[0.85rem] leading-relaxed text-text-dim"
        >
          {t('explanation.noPrimary')}
        </motion.p>
      )}

      {/* ---------- Secondary signals ---------- */}
      {secondarySignals.length > 0 && (
        <div>
          <p className="mono-label mb-3 text-text-dim">
            {t('explanation.secondaryLabel')}
          </p>
          <ul className="divide-y divide-line/60">
            {secondarySignals.map((signal, index) => (
              <motion.li
                key={signal.id}
                initial={{ opacity: 0, x: isArabic ? -8 : 8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{
                  delay: 0.4 + index * 0.07,
                  duration: 0.4,
                  ease: [0.16, 1, 0.3, 1],
                }}
                className="flex items-center justify-between gap-4 py-2.5"
              >
                <span className="flex min-w-0 items-center gap-2.5">
                  <span
                    aria-hidden
                    className="size-1 shrink-0 rounded-full"
                    style={{
                      background: SEVERITY_COLOR[signal.severity],
                    }}
                  />
                  <span className="truncate text-[0.82rem] text-text-muted">
                    {t(signal.metricKey)}
                  </span>
                </span>
                <span
                  className="shrink-0 font-mono text-xs tabular-nums"
                  style={{ color: SEVERITY_COLOR[signal.severity] }}
                >
                  {isArabic ? signal.valueAr : signal.valueEn}
                </span>
              </motion.li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
