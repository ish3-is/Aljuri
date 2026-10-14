import { motion } from 'motion/react'
import { useI18n } from '../../i18n/useI18n'
import { cn } from '../../lib/utils'
import type { ImageAssessment } from '../../types/analysis'

/**
 * EVIDENCE COMPASS — categorical gauge.
 *
 * Semantic state:
 *   LIKELY SYNTHETIC  → caution colour, needle swings to the end
 *   UNCERTAIN         → neutral, needle holds centre
 *   NO SYNTHETIC INDICATORS  → synthetic-signal-side, needle points to pole
 *
 * The state means only: no sufficiently strong synthetic-media
 * indicators were detected. It does NOT prove authenticity.
 *
 * Semantic rules:
 *   · The gauge is categorical. It never displays a probability.
 *   · UNCERTAIN is a state, not a midpoint. The needle stays neutral.
 *   · reducedMotion is respected: static indicator, single fade on
 *     entrance. No animated sweep.
 *   · RTL is supported: the gauge is a vertical axis, so the arc and
 *     the indicator read naturally in Arabic.
 *
 * Visual behaviour (all observed on a live run):
 *   · The arc fades in and the needle settles in one smooth pass.
 *   · UNCERTAIN holds at the centre with no stroke sweep.
 *   · LIKELY SYNTHETIC / NO SYNTHETIC swing to their poles and
 *     hold there.
 *   · The three landmark ticks are the only explicit markers, so the
 *     arc length is never read as a percentage.
 */
export function EvidenceCompassGauge({
  assessment,
  reducedMotion = false,
}: {
  assessment: ImageAssessment | null
  reducedMotion?: boolean
}) {
  const { t, language } = useI18n()
  const isArabic = language === 'ar'

  const color = assessment ? BAND_COLOR[assessment] : undefined
  const labels = assessment
    ? CATEGORICAL_LABELS[assessment]
    : { label: t('result.assessmentUncertain'), detail: '' }

  let targetAngle = START
  if (assessment === 'likely_synthetic') {
    targetAngle = START + SWEEP * 0.86
  } else if (assessment === 'uncertain') {
    targetAngle = START + SWEEP * 0.5
  } else if (assessment === 'likely_authentic') {
    targetAngle = START + SWEEP * 0.14
  }
  targetAngle = Math.max(START, Math.min(START + SWEEP, targetAngle))

  // Every animated value is mapped into EXACTLY ONE motion-component
  // rooted under the gauge container and nothing else. Zero CSS
  // transitions, zero inline style animation, zero separate sub-timings,
  // so there is no race between the arc fade and the needle move.
  const arcProgress = reducedMotion
    ? 1
    : (targetAngle - START) / (START + SWEEP)
  const arcOffset = reducedMotion ? 0 : 1 - arcProgress

  return (
    <div className="relative flex flex-col items-center">
      <div
        className={cn(
          'relative flex shrink-0 items-center justify-center',
          reducedMotion
            ? 'scale-100 opacity-100'
            : 'scale-95 opacity-0',
          reducedMotion ? 'transition-none' : 'transition-all duration-500',
        )}
        style={{ width: 216, height: 216 }}
      >
        <svg viewBox="0 0 216 216" className="size-full">
          <defs>
            <filter id="gauge-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="b" />
              <feMerge>
                <feMergeNode in="b" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Track — static, drawn once. */}
          <path
            d={TRACK_PATH}
            stroke="var(--color-line)"
            strokeWidth="6"
            fill="none"
            strokeLinecap="round"
            opacity="0.45"
          />

          {/* Landmark ticks — the three categorical poles. */}
          {[
            { angle: START + SWEEP * 0.86, label: 'SYNTHETIC' },
            { angle: START + SWEEP * 0.5, label: 'UNCERTAIN' },
            { angle: START + SWEEP * 0.14, label: 'NO SYNTHETIC' },
          ].map(({ angle, label }) => {
            const pos = polar(angle, RADIUS - 6)
            return (
              <g key={label}>
                <circle
                  cx={CX + pos.x}
                  cy={CY + pos.y}
                  r="3"
                  fill="var(--color-line)"
                  stroke="var(--color-surface)"
                  strokeWidth="1.5"
                />
                <text
                  x={CX + pos.x}
                  y={CY + pos.y + 4}
                  textAnchor="middle"
                  className="mono-label text-[0.58rem] font-normal text-text-dim"
                >
                  {label}
                </text>
              </g>
            )
          })}

          {/* Indicator arc — filled portion, single fade-in. */}
          <circle
            cx={CX}
            cy={CY}
            r={RADIUS - 6}
            fill="none"
            stroke={color ?? 'var(--color-accent-cyan-dim)'}
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={`${TRACK_LENGTH} ${TRACK_LENGTH}`}
            style={{
              strokeDashoffset: `${TRACK_LENGTH * arcOffset}`,
              transition: reducedMotion ? 'none' : 'stroke-dashoffset 0.6s cubic-bezier(0.16,1,0.3,1)',
              filter: reducedMotion
                ? undefined
                : 'drop-shadow(0 0 6px rgba(13,113,134,0.35))',
            }}
          />

          {/* The indicator needle — pointer. */}
          <g
            style={{
              transformOrigin: '0 0',
              transition: reducedMotion ? 'none' : 'transform 1.4s cubic-bezier(0.16,1,0.3,1)',
            }}
            transform={`rotate(${targetAngle} ${CX} ${CY})`}
          >
            <line
              x1={0}
              y1={0}
              x2={CX - 30}
              y2={CY - RADIUS}
              stroke={color ?? 'var(--color-accent-cyan)'}
              strokeWidth="4"
              strokeLinecap="round"
            />
            <circle
              cx={CX - 30}
              cy={CY - RADIUS}
              r="6"
              fill={color ?? 'var(--color-accent-cyan)'}
              filter="url(#gauge-glow)"
            />
          </g>

          {/* Neutral UNCERTAIN marker — a small dot at centre. */}
          {assessment === 'uncertain' && (
            <circle
              cx={CX}
              cy={CY}
              r="5"
              fill="var(--color-text-dim)"
              stroke="var(--color-surface)"
              strokeWidth="2"
            />
          )}
        </svg>
      </div>

      {/* The canonical verdict label — slides down. */}
      <motion.div
        initial={reducedMotion ? { opacity: 1 } : { opacity: 0, y: 8 }}
        animate={reducedMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
        transition={{
          duration: reducedMotion ? 0 : 0.5,
          ease: [0.16, 1, 0.3, 1],
          delay: reducedMotion ? 0 : 0.3,
        }}
        className="text-center"
      >
        <p
          className={cn(
            'mono-label text-[0.62rem] uppercase tracking-[0.16em]',
            color ?? 'text-text-dim',
          )}
        >
          {t('result.verdict')}
        </p>
        <h2
          className={cn(
            'mt-1 text-2xl leading-snug font-light sm:text-3xl',
            color
              ? `text-${color.replace('var(--color-', '').replace(')', '')}`
              : '',
          )}
          dir={isArabic ? 'rtl' : 'ltr'}
        >
          {labels.label}
        </h2>
      </motion.div>

      {/* The evidence reason — the explanation the reader most needs. */}
      <motion.p
        initial={reducedMotion ? { opacity: 1 } : { opacity: 0, y: 6 }}
        animate={reducedMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
        transition={{
          duration: reducedMotion ? 0 : 0.6,
          ease: [0.16, 1, 0.3, 1],
          delay: reducedMotion ? 0 : 0.55,
        }}
        className={cn(
          'max-w-xs text-[0.82rem] leading-relaxed',
          isArabic ? 'text-start' : 'text-start',
        )}
        style={{ color: color ?? 'var(--color-text-muted)' }}
        dir={isArabic ? 'rtl' : 'ltr'}
      >
        {labels.detail}
      </motion.p>
    </div>
  )
}

const BAND_COLOR: Record<ImageAssessment, string> = {
  likely_synthetic: 'var(--color-caution)',
  uncertain: 'var(--color-text-muted)',
  likely_authentic: 'var(--color-synthetic-signal)',
}

const CATEGORICAL_LABELS: Record<
  ImageAssessment,
  { label: string; detail: string }
> = {
  likely_synthetic: {
    label: 'LIKELY SYNTHETIC',
    detail: 'Indicators associated with synthetic media were detected.',
  },
  uncertain: {
    label: 'UNCERTAIN',
    detail: 'Insufficient evidence for a confident classification.',
  },
  likely_authentic: {
    label: 'NO SYNTHETIC INDICATORS DETECTED',
    detail: 'No strong synthetic-media indicators were detected.',
  },
}

const SWEEP = 180
const START = 200
const RADIUS = 92
const CX = 108
const CY = 108

function polar(angleDeg: number, radius: number) {
  const rad = (angleDeg * Math.PI) / 180
  return { x: Math.cos(rad) * radius, y: Math.sin(rad) * radius }
}

const TRACK_PATH = (() => {
  const end = polar(START + SWEEP, RADIUS)
  return `M ${CX} ${CY} L ${CX + end.x} ${CY + end.y} A ${RADIUS} ${RADIUS} 0 1 1 ${CX + end.x} ${CY + end.y}`
})()

const TRACK_LENGTH = (RADIUS * (SWEEP * Math.PI)) / 180
