import { motion } from 'motion/react'
import { Minus } from 'lucide-react'
import { useI18n } from '../../i18n/useI18n'
import { cn } from '../../lib/utils'
import type { TranslationKey } from '../../i18n/translations'
import type { ImageForensicSignal } from '../../types/analysis'

/* ============================================================
   IMAGE FORENSICS PANEL

   Every measured forensic characteristic, each carrying BOTH halves
   of what it means.

   The backend supplies `meaningEn` and `doesNotMeanEn` for every
   signal, and this component renders both, always. The "does not
   mean" half is not a disclaimer — it is the load-bearing half. The
   forensic signals here (compression structure, high-frequency
   energy, noise floor, spectral slope) are precisely the class of
   measurement that a measurable value can encode collection
   methodology rather than image origin. Showing the number without
   the caveat would let a reader do exactly the inference the
   pipeline says cannot be drawn.

   Language is capped at "supporting signal" / "observed
   characteristic". Never "proof", never "confirmed".

   The `meaningEn` / `doesNotMeanEn` text is English-only in the
   payload, so it is embedded LTR and marked as such in Arabic mode
   rather than being silently mistranslated.
   ============================================================ */

interface ImageForensicsPanelProps {
  signals: ImageForensicSignal[]
}

const NAME_KEYS: Record<string, TranslationKey> = {
  compression_anomaly: 'image.forensics.names.compression_anomaly',
  high_frequency_energy: 'image.forensics.names.high_frequency_energy',
  noise_floor: 'image.forensics.names.noise_floor',
  spectral_slope: 'image.forensics.names.spectral_slope',
}

export function ImageForensicsPanel({ signals }: ImageForensicsPanelProps) {
  const { t, language } = useI18n()
  const isArabic = language === 'ar'

  if (signals.length === 0) {
    return (
      <p className="rounded-lg border border-line/70 bg-surface/40 p-4 text-[0.82rem] leading-relaxed text-text-dim">
        {t('image.forensics.noSignals')}
      </p>
    )
  }

  return (
    <div className="space-y-4">
      <ul className="space-y-3">
        {signals.map((signal, index) => {
          const nameKey = NAME_KEYS[signal.name]
          const isMeasured = signal.value !== null

          return (
            <motion.li
              key={signal.name}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                delay: 0.1 + index * 0.06,
                duration: 0.4,
                ease: [0.16, 1, 0.3, 1],
              }}
              className="rounded-lg border border-line/70 bg-surface/40 p-4"
            >
              {/* ---- Header: name, role, measured value ---- */}
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
                <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1">
                  <h4 className="text-[0.85rem] font-normal text-text">
                    {nameKey ? t(nameKey) : signal.name}
                  </h4>
                  {/* Role tag, never a verdict. */}
                  <span className="mono-label rounded-full border border-line-bright/60 px-2 py-0.5 text-text-dim">
                    {isMeasured
                      ? t('image.forensics.observedLabel')
                      : t('image.forensics.notMeasured')}
                  </span>
                </div>

                {/* The measurement. Unmeasured reads as N/A, and the
                    dash carries the same meaning as elsewhere. */}
                {isMeasured ? (
                  <span
                    className="font-mono text-xs tabular-nums text-text-muted"
                    dir="ltr"
                  >
                    {(signal.value as number).toFixed(4)}
                  </span>
                ) : (
                  <span
                    className="flex items-center gap-1 text-[0.68rem] tracking-wider text-text-dim"
                    title={t('image.forensics.notMeasured')}
                  >
                    <Minus size={11} aria-hidden />
                    N/A
                  </span>
                )}
              </div>

              {/* ---- Meaning, and the limit on that meaning ---- */}
              <div className="mt-3 space-y-2.5 border-t border-line/50 pt-3">
                <div>
                  <p className="text-[0.68rem] leading-tight text-signal/70">
                    {t('image.forensics.meaningLabel')}
                  </p>
                  {/* Backend-supplied prose is English-only; keep it LTR
                      and legible rather than forcing it through the RTL
                      flow. */}
                  <p
                    dir="ltr"
                    className={cn(
                      'mt-1 text-[0.76rem] leading-relaxed text-text-muted',
                      isArabic && 'text-start',
                    )}
                  >
                    {signal.meaningEn}
                  </p>
                </div>

                <div>
                  <p className="text-[0.68rem] leading-tight text-caution/80">
                    {t('image.forensics.doesNotMeanLabel')}
                  </p>
                  <p
                    dir="ltr"
                    className={cn(
                      'mt-1 text-[0.76rem] leading-relaxed text-text-dim',
                      isArabic && 'text-start',
                    )}
                  >
                    {signal.doesNotMeanEn}
                  </p>
                </div>
              </div>
            </motion.li>
          )
        })}
      </ul>

      {/* The role label applied to the whole set, and a note on the
          language of the definitions so their English is not mistaken
          for a rendering bug. */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line/50 pt-3.5">
        <span className="mono-label text-text-dim">
          {t('image.forensics.supportingLabel')}
        </span>
        {isArabic && (
          <span className="text-[0.68rem] text-text-dim/70">
            {t('image.forensics.latinNote')}
          </span>
        )}
      </div>
    </div>
  )
}