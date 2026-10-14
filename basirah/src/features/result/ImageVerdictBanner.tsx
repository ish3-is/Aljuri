import { motion } from 'motion/react'
import { useI18n } from '../../i18n/useI18n'
import type { TranslationKey } from '../../i18n/translations'
import type { ImageAssessment, ImageDetail } from '../../types/analysis'

/* ============================================================
   IMAGE VERDICT BANNER

   The headline for an image analysis, and the component with the
   greatest risk of overstating what the pipeline knows.

   Three rules govern everything below:

   1. THREE-WAY ONLY. likely_authentic / uncertain /
      likely_synthetic. There is no binary "fake" state anywhere in
      this file, because a probabilistic detector rendered as a
      boolean reads as proof.

   2. NEVER "IS AI-GENERATED". The wording is about indicators that
      were detected or not detected. Detecting synthetic-media
      indicators is not a fact about how the image was made.

   3. UNCERTAINTY IS SHOWN, NOT SMOOTHED. When the probability lands
      inside the validation band, the banner says so in as many words
      as the probability itself, so 0.52 and 0.97 do not read as the
      same kind of claim.

   Colour is deliberately restrained: "likely synthetic" takes
   CAUTION, not DANGER. Escalating to the danger accent would
   overstate a research-grade probability; danger stays reserved for
   genuine failures.
   ============================================================ */

interface ImageVerdictBannerProps {
  detail: ImageDetail
  /** Model confidence in the score, 0-100, from the parent result. */
  confidence: number
}

/** Semantic colour per assessment band. Deliberately excludes danger. */
const BAND_COLOR: Record<ImageAssessment, string> = {
  likely_synthetic: 'var(--color-caution)',
  uncertain: 'var(--color-text-muted)',
  likely_authentic: 'var(--color-trusted)',
}

const TITLE_KEY: Record<ImageAssessment, TranslationKey> = {
  likely_synthetic: 'image.verdict.titleLikelySynthetic',
  likely_authentic: 'image.verdict.titleLikelyAuthentic',
  uncertain: 'image.verdict.titleUncertain',
}

const BODY_KEY: Record<ImageAssessment, TranslationKey> = {
  likely_synthetic: 'image.verdict.likelySynthetic',
  likely_authentic: 'image.verdict.likelyAuthentic',
  uncertain: 'image.verdict.uncertain',
}

export function ImageVerdictBanner({
  detail,
  confidence,
}: ImageVerdictBannerProps) {
  const { t } = useI18n()

  const { assessment, synthetic } = detail
  const color = BAND_COLOR[assessment]
  const probability = synthetic.syntheticProbability

  const percent = probability === null ? null : Math.round(probability * 100)
  const lowerPct = Math.round(synthetic.uncertaintyLower * 100)
  const upperPct = Math.round(synthetic.uncertaintyUpper * 100)

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="relative overflow-hidden rounded-lg border border-line/70 bg-surface/45 p-5 sm:p-6"
      // Announced as a status region: this is the outcome of the run.
      role="status"
      aria-live="polite"
    >
      {/* Vertical accent on the inline-start edge, coloured by band */}
      <span
        aria-hidden
        className="absolute inset-y-0 start-0 w-px"
        style={{
          background: `linear-gradient(to bottom, ${color}, transparent)`,
        }}
      />

      <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:gap-8">
        {/* ---------------- Headline ---------------- */}
        <div className="min-w-0 flex-1">
          <p className="mono-label text-text-dim">{t('image.verdict.label')}</p>
          <h3
            className="mt-2.5 text-xl leading-snug font-light sm:text-2xl"
            style={{ color }}
          >
            {t(TITLE_KEY[assessment])}
          </h3>
          <p className="mt-3 max-w-lg text-[0.88rem] leading-relaxed text-text-muted">
            {t(BODY_KEY[assessment])}
          </p>
        </div>

        {/* ---------------- Figures ---------------- */}
        <div className="shrink-0 sm:w-[260px]">
          {/* Probability */}
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-[0.72rem] leading-tight text-text-dim">
              {t('image.verdict.probabilityLabel')}
            </span>
            {percent !== null ? (
              <span
                className="font-mono text-lg tabular-nums"
                style={{ color }}
                dir="ltr"
              >
                {percent}%
              </span>
            ) : (
              <span className="font-mono text-[0.7rem] tracking-wider text-text-dim">
                {t('image.forensics.notMeasured')}
              </span>
            )}
          </div>

          {/* Likelihood track. When no probability was produced the
              track stays empty and reads as unmeasured — never 0%. */}
          <div className="mt-2 h-px w-full bg-line" aria-hidden>
            <motion.div
              className="h-px"
              style={{ background: color }}
              initial={{ width: 0 }}
              animate={{ width: percent === null ? '0%' : `${percent}%` }}
              transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
            />
          </div>

          {/* The uncertainty band, drawn on the same 0-100 scale so the
              probability's position relative to it is readable. */}
          <div className="relative mt-1.5 h-2" aria-hidden>
            <span
              className="absolute inset-y-0 rounded-sm bg-line-bright/50"
              style={{
                insetInlineStart: `${lowerPct}%`,
                width: `${Math.max(upperPct - lowerPct, 1)}%`,
              }}
            />
            {percent !== null && (
              <motion.span
                className="absolute top-1/2 size-1.5 -translate-y-1/2 rounded-full"
                style={{
                  background: color,
                  insetInlineStart: `calc(${percent}% - 3px)`,
                }}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8, duration: 0.4 }}
              />
            )}
          </div>

          {percent === null && (
            <p className="mt-2 text-[0.7rem] leading-relaxed text-text-dim">
              {t('image.verdict.probabilityUnavailable')}
            </p>
          )}

          {/* Confidence — the model's confidence in the score itself,
              which is a different figure from the probability above. */}
          <div className="mt-5 flex items-baseline justify-between gap-3">
            <span className="text-[0.72rem] leading-tight text-text-dim">
              {t('image.verdict.confidenceLabel')}
            </span>
            <span
              className="font-mono text-xs tabular-nums text-text-muted"
              dir="ltr"
            >
              {Math.round(confidence)}%
            </span>
          </div>

          {/* Uncertainty state, in words */}
          <div className="mt-4 border-t border-line/60 pt-3.5">
            <p className="mono-label text-text-dim">
              {t('image.verdict.uncertaintyLabel')}
            </p>
            <p className="mt-2 text-[0.76rem] leading-relaxed text-text-muted">
              {synthetic.uncertain
                ? t('image.verdict.uncertaintyInside')
                : t('image.verdict.uncertaintyResolved')}
            </p>
            {/* The band edges are thresholds for this classification,
                not research performance figures, so they are shown. */}
            <p className="ltr-embed mt-2 text-[0.68rem] text-text-dim/80">
              {lowerPct}% – {upperPct}%
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  )
}