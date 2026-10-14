import { motion, useMotionValue, animate } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { RISK_COLORS } from '../../data/mockAnalysis'
import { useI18n } from '../../i18n/useI18n'
import { formatScore } from '../../lib/utils'
import type { RiskLevel } from '../../types/analysis'

/* ============================================================
   TRUST SCORE

   An animated counting gauge. The number climbs through intermediate
   values and settles on the result — the brief's 00 → 14 → 39 → 63 →
   progression is deliberate: a number that appears instantly reads as a
   lookup, one that counts reads as a computation.

   The arc is a measured 240° sweep with the filled portion carrying the
   risk colour. Language is probabilistic throughout: a band name and a
   confidence figure, never a verdict.
   ============================================================ */

interface TrustScoreProps {
  score: number
  riskLevel: RiskLevel
  confidence: number
  /** Override the numeric readout and count-up when the result is not an
   * authenticity score (e.g. canonical "uncertain"). A numeric "0/100" would
   * read as "0% trusted", which is misleading for uncertain. Instead the
   * gauge visualizes the categorical assessment state and the label is shown. */
  assessmentLabel?: string
  /** Re-runs the count-up whenever the result changes. */
  runKey?: string | number
}

const RADIUS = 88
const SWEEP = 240 // degrees of arc
const START = 150 // degrees, measured clockwise from 3 o'clock
const CX = 108
const CY = 108

function polar(angleDeg: number, radius: number) {
  const rad = (angleDeg * Math.PI) / 180
  return { x: Math.cos(rad) * radius, y: Math.sin(rad) * radius }
}

/**
 * The full track arc, drawn once.
 *
 * The fill is expressed with stroke-dashoffset rather than by animating
 * this path's `d`: Motion treats every number in a path string as
 * animatable, so it would also interpolate the arc flags (0/1) and emit
 * invalid geometry. A static `d` + an animated dash is correct and
 * cheaper.
 *
 * A full elliptical arc command is
 *   A rx ry x-axis-rotation large-arc-flag sweep-flag x y
 * so the endpoint must be present after the flags.
 */
const TRACK_PATH = (() => {
  const end = polar(START + SWEEP, RADIUS)
  return `M ${CX} ${CY} L ${CX + end.x} ${CY + end.y} A ${RADIUS} ${RADIUS} 0 1 1 ${
    CX + end.x
  } ${CY + end.y}`
})()

/**
 * Arc length = radius * sweep in radians. Exact for a circular arc, so
 * the dash denominator matches the rendered geometry precisely.
 */
const TRACK_LENGTH = (RADIUS * (SWEEP * Math.PI)) / 180

export function TrustScore({
  score,
  riskLevel,
  confidence,
  runKey = 0,
  assessmentLabel,
}: TrustScoreProps) {
  const { t, language } = useI18n()
  const isArabic = language === 'ar'

  const [display, setDisplay] = useState(0)
  const [displayConfidence, setDisplayConfidence] = useState(0)
  const countValue = useMotionValue(0)
  const confidenceMotion = useMotionValue(0)
  const gaugeRef = useRef<SVGPathElement>(null)

  // When the caller passes an assessmentLabel (canonical "uncertain" / non-auth
  // result), do NOT run the numeric count-up: 0/100 would read as "0% trusted".
  // The label renders the categorical verdict and the gauge stays neutral.
  const showCategorical =
    typeof assessmentLabel !== 'undefined' && assessmentLabel !== null

  // The gauge arc is a plain <path>, not a motion component, and its
  // stroke-dashoffset is written straight to the DOM node here.
  //
  // It must not be a motion.path with an animated `d`: Motion treats
  // every number in a path string as animatable, so it would also
  // interpolate the arc flags (0/1) and emit invalid geometry on nearly
  // every frame. Writing one attribute per tick is cheaper as well.
  useEffect(() => {
    const node = gaugeRef.current
    if (!node) return
    node.style.strokeDasharray = `${TRACK_LENGTH}`
    node.style.strokeDashoffset = `${TRACK_LENGTH}`
  }, [])

  // Count-up: a long ease-out reads as a value converging, not a CSS
  // transition. Confidence animates on its own, slightly later clock so
  // the two figures do not appear to move as one number.
  useEffect(() => {
    if (showCategorical) return

    countValue.set(0)
    confidenceMotion.set(0)

    const scoreControls = animate(countValue, score, {
      duration: 1.9,
      ease: [0.16, 1, 0.3, 1],
    })
    const confidenceControls = animate(confidenceMotion, confidence, {
      duration: 1.5,
      delay: 0.45,
      ease: [0.16, 1, 0.3, 1],
    })

    const unsubscribeScore = countValue.on('change', (latest) => {
      setDisplay(Math.round(latest))
      const node = gaugeRef.current
      if (node) {
        node.style.strokeDashoffset = `${TRACK_LENGTH * (1 - Math.min(latest, 100) / 100)}`
      }
    })
    const unsubscribeConfidence = confidenceMotion.on('change', (latest) => {
      setDisplayConfidence(Math.round(latest))
    })

    return () => {
      scoreControls.stop()
      confidenceControls.stop()
      unsubscribeScore()
      unsubscribeConfidence()
    }
  }, [score, confidence, runKey, countValue, confidenceMotion, showCategorical])

  const color = RISK_COLORS[riskLevel]
  const filledAngle = (Math.min(display, 100) / 100) * SWEEP
  const head = polar(START + filledAngle, RADIUS)

  const riskLabel = isArabic
    ? riskLevel === 'high_risk'
      ? 'خطورة عالية'
      : riskLevel === 'caution'
        ? 'تحفّظ'
        : 'موثوق'
    : t(`score.${riskLevel === 'high_risk' ? 'highRisk' : riskLevel}`)

  return (
    <div className="flex flex-col items-center gap-5 sm:flex-row sm:gap-7">
      {/* ---------------- Gauge ---------------- */}
      <div className="relative shrink-0" style={{ width: 216, height: 216 }}>
        <svg viewBox="0 0 216 216" className="size-full">
          <defs>
            <filter id="score-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="b" />
              <feMerge>
                <feMergeNode in="b" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Track */}
          <path
            d={TRACK_PATH}
            stroke="var(--color-line)"
            strokeWidth="7"
            fill="none"
            strokeLinecap="round"
            opacity="0.55"
          />

          {/* Confidence reference arc (inner, subtle) — static context
              for the model-confidence figure shown in the panel beside it. */}
          <circle
            cx={CX}
            cy={CY}
            r={RADIUS - 11}
            fill="none"
            stroke="var(--color-intel)"
            strokeWidth="1.5"
            strokeDasharray={`${(2 * Math.PI * (RADIUS - 11) * confidence) / 100} ${2 * Math.PI * (RADIUS - 11)}`}
            transform={`rotate(150 ${CX} ${CY})`}
            opacity="0.35"
            strokeLinecap="round"
          />

          {/* Filled portion — the score itself.
              Plain path; stroke-dashoffset is driven imperatively from
              the count-up so the `d` is never touched by an animation. */}
          <path
            ref={gaugeRef}
            d={TRACK_PATH}
            stroke={color}
            strokeWidth="7"
            fill="none"
            strokeLinecap="round"
            filter="url(#score-glow)"
            style={{
              strokeDasharray: TRACK_LENGTH,
              strokeDashoffset: TRACK_LENGTH,
            }}
          />

          {/* Scale ticks */}
          {Array.from({ length: 21 }).map((_, i) => {
            const angle = START + (i / 20) * SWEEP
            const long = i % 5 === 0
            const outer = polar(angle, RADIUS + 10)
            const inner = polar(angle, RADIUS + (long ? 19 : 15))
            return (
              <line
                key={i}
                x1={CX + outer.x}
                y1={CY + outer.y}
                x2={CX + inner.x}
                y2={CY + inner.y}
                stroke="var(--color-line-bright)"
                strokeWidth={long ? 0.8 : 0.4}
                opacity={long ? 0.7 : 0.35}
              />
            )
          })}

          {/* Leading head — a bright cap that rides the arc */}
          {display > 0 && (
            <circle
              cx={CX + head.x}
              cy={CY + head.y}
              r="3.4"
              fill={color}
              filter="url(#score-glow)"
            />
          )}
        </svg>

        {/* Numeric readout */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          {/* If asked to show a categorical assessment (uncertain), show the
              label instead of a fake 0/100 authenticity score. */}
          {showCategorical ? (
            <span
              className="font-mono text-[3.1rem] leading-none font-light tabular-nums"
              style={{ color: color }}
            >
              {assessmentLabel}
            </span>
          ) : (
            <div dir="ltr">
              <span
                className="font-mono text-[3.1rem] leading-none font-light tabular-nums"
                style={{ color }}
              >
                {formatScore(display)}
              </span>
              <span className="mt-1.5 font-mono text-sm text-text-dim">/100</span>
            </div>
          )}
          <span className="mono-label mt-2.5 text-text-dim">{t('score.title')}</span>
        </div>
      </div>

      {/* ---------------- Classification ---------------- */}
      <div className="min-w-0 flex-1">
        <p className="mono-label text-text-dim">{t('score.classificationLabel')}</p>
        <p
          className="mt-1.5 text-2xl leading-snug font-light"
          style={{ color }}
        >
          {riskLabel}
        </p>

        {/* Confidence */}
        <div className="mt-5">
          <div className="mb-2 flex items-baseline justify-between gap-2">
            <span className="text-[0.75rem] text-text-dim">
              {t('score.confidenceLabel')}
            </span>
            <span className="font-mono text-xs text-text-muted" dir="ltr">
              {displayConfidence}%
            </span>
          </div>
          <div className="h-px w-full bg-line">
            <motion.div
              className="h-px bg-intel/70"
              animate={{ width: `${displayConfidence}%` }}
              transition={{ duration: 0.3, ease: 'linear' }}
            />
          </div>
        </div>

        <p className="mt-5 text-[0.75rem] leading-relaxed text-text-dim">
          {t('score.provisional')}
        </p>
      </div>
    </div>
  )
}
