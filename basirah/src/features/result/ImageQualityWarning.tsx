import { motion } from 'motion/react'
import { ScanSearch, TriangleAlert } from 'lucide-react'
import { useI18n } from '../../i18n/useI18n'
import type { ImageEvidenceQuality } from '../../types/analysis'

/* ============================================================
   IMAGE QUALITY WARNING

   Evidence-quality limits, promoted to the top of the result.

   A low-resolution or heavily-compressed image can produce a
   confident-looking number that is not supported by the evidence.
   Burying that caveat under the verdict would let a 0.97 read as
   well-founded when the pixels were never there to support it — so
   this banner is placed ABOVE the verdict banner in AnalyzePage, not
   beside it.

   Severity 'high' (low_resolution) uses the caution accent rather
   than danger: it is a limitation of the evidence, not a failure.
   ============================================================ */

interface ImageQualityWarningProps {
  quality: ImageEvidenceQuality
}

export function ImageQualityWarning({ quality }: ImageQualityWarningProps) {
  const { t, language } = useI18n()
  const isArabic = language === 'ar'

  const warnings = quality.warnings
  if (warnings.length === 0) return null

  // The most severe warning sets the banner's tone. A high-severity
  // warning (low resolution) gets the strong headline, because that
  // case genuinely invalidates a confident reading; a medium one
  // (heavy compression) is still surfaced prominently but gets the
  // softer headline — overstating a compression note as "this cannot
  // support a reliable reading" would be the same category of error
  // as overstating the verdict itself.
  const isSevere = warnings.some((warning) => warning.severity === 'high')
  const accent = isSevere ? 'var(--color-caution)' : 'var(--color-text-muted)'

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      // Assertive: this qualifies the headline the user is about to read.
      role="alert"
      className="relative overflow-hidden rounded-lg border border-caution/30 bg-caution/[0.06] p-5 sm:p-6"
      style={{ borderColor: `${accent}4d` }}
    >
      {/* Full-bleed leading rule so it reads as a banner, not a card */}
      <span
        aria-hidden
        className="absolute inset-y-0 start-0 w-[2px]"
        style={{ background: accent }}
      />

      <div className="flex items-start gap-4">
        <span className="mt-0.5 shrink-0" style={{ color: accent }}>
          <TriangleAlert size={19} />
        </span>

        <div className="min-w-0 flex-1">
          <p className="mono-label" style={{ color: accent }}>
            {t('image.quality.title')}
          </p>
          <h3 className="mt-2 text-base leading-snug font-light text-text sm:text-lg">
            {isSevere
              ? t('image.quality.titleWarning')
              : t('image.quality.titleAdvisory')}
          </h3>
          <p className="mt-2 text-[0.82rem] leading-relaxed text-text-muted">
            {t('image.quality.subtitle')}
          </p>

          {/* Each warning verbatim from the backend. They are written as
              measured statements and must not be paraphrased upward. */}
          <ul className="mt-4 space-y-3">
            {warnings.map((warning) => (
              <li
                key={warning.code}
                className="flex items-start gap-3 border-t border-line/50 pt-3"
              >
                <ScanSearch
                  size={14}
                  aria-hidden
                  className="mt-0.5 shrink-0 text-text-dim"
                />
                <p className="text-[0.82rem] leading-relaxed text-text-muted">
                  {isArabic ? warning.ar : warning.en}
                </p>
              </li>
            ))}
          </ul>

          {/* The measured figure behind the warning, so it is checkable
              rather than an assertion. */}
          <p className="ltr-embed mt-4 text-[0.7rem] text-text-dim/80">
            {t('image.quality.longEdge')}: {quality.longEdge} {t('image.quality.pixels')}
          </p>
        </div>
      </div>
    </motion.div>
  )
}