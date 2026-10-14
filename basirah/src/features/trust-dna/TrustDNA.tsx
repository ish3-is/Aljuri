import { motion } from 'motion/react'
import { useMemo } from 'react'
import { dnaColorForValue } from '../../data/mockAnalysis'
import { useI18n } from '../../i18n/useI18n'
import type { TranslationKey } from '../../i18n/translations'
import type { DnaAxis, TrustDna } from '../../types/analysis'

/* ============================================================
   TRUST DNA

   BASIRAH's signature visualisation: a visual fingerprint of the
   analysed signal, not a chart.

   It is deliberately NOT a radar chart. A radar polygon implies
   comparison between series, and there is nothing to compare against
   here. Instead the DNA is drawn as a *signal specimen*:

     · five concentric fingerprint bands, one per axis
     · each band is an interrupted arc whose arc-length encodes the value
     · radial tick density increases with value (more detected signal)
     · the inner core glows in the dominant band's colour
     · a slow rotating scan cursor reads the specimen

   The result reads as biometric evidence under a lens, which is the
   point: two different signals produce visibly different specimens.
   ============================================================ */

const AXES: { id: DnaAxis; key: TranslationKey }[] = [
  { id: 'synthetic', key: 'dna.axes.synthetic' },
  { id: 'identity', key: 'dna.axes.identity' },
  { id: 'domain', key: 'dna.axes.domain' },
  { id: 'provenance', key: 'dna.axes.provenance' },
  { id: 'behavior', key: 'dna.axes.behavior' },
]

const SIZE = 320
const CENTER = SIZE / 2

interface TrustDnaProps {
  dna: TrustDna
  /** Animates bands in sequence after a result lands. */
  animate?: boolean
}

export function TrustDNA({ dna, animate = true }: TrustDnaProps) {
  const { t, language } = useI18n()
  const isArabic = language === 'ar'

  /**
   * The axis with the strongest detected signal drives the core glow.
   * Null (not-applicable) axes are excluded — a missing measurement must
   * not be treated as a score of zero.
   */
  const dominant = useMemo(() => {
    let best: DnaAxis = 'domain'
    let bestValue = -1
    for (const axis of AXES) {
      const value = dna[axis.id]
      if (value !== null && value > bestValue) {
        best = axis.id
        bestValue = value
      }
    }
    return best
  }, [dna])

  const coreColor =
    dnaColorForValue(dna[dominant] ?? 0)

  /** How many axes carry a real measurement, for the scale caption. */
  const measuredCount = AXES.filter((axis) => dna[axis.id] !== null).length
  const hasUnavailable = measuredCount < AXES.length

  return (
    <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-center sm:gap-7">
      {/* ---------------- Specimen ---------------- */}
      <div className="relative shrink-0" style={{ width: SIZE, height: SIZE }}>
        {/* Ambient bloom behind the specimen */}
        <div
          aria-hidden
          className="absolute inset-6 rounded-full blur-3xl"
          style={{
            background: `radial-gradient(circle, ${coreColor}22 0%, transparent 70%)`,
          }}
        />

        <svg
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          className="relative size-full"
          role="img"
          aria-label={t('dna.title')}
        >
          <defs>
            <filter id="dna-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3.2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Static reference frame */}
          <circle
            cx={CENTER}
            cy={CENTER}
            r={148}
            fill="none"
            stroke="var(--color-line)"
            strokeWidth="0.5"
          />
          <circle
            cx={CENTER}
            cy={CENTER}
            r={28}
            fill="none"
            stroke="var(--color-line)"
            strokeWidth="0.5"
          />

          {/* Rotating scan cursor — reads the specimen like an instrument */}
          <motion.g
            style={{ originX: `${CENTER}px`, originY: `${CENTER}px` }}
            animate={{ rotate: 360 }}
            transition={{ duration: 22, repeat: Infinity, ease: 'linear' }}
          >
            <line
              x1={CENTER}
              y1={CENTER - 30}
              x2={CENTER}
              y2={CENTER - 148}
              stroke={coreColor}
              strokeWidth="0.7"
              opacity="0.5"
            />
            <circle cx={CENTER} cy={CENTER - 148} r="2" fill={coreColor} opacity="0.8" />
          </motion.g>

          {/* --- The five fingerprint bands --- */}
          {AXES.map((axis, index) => {
            const value = dna[axis.id]
            const isAvailable = value !== null
            const color = dnaColorForValue(value ?? 0)
            const radius = 44 + index * 25
            // Full circumference minus a fixed gap; arc length carries the value.
            const gap = 26
            const circumference = 2 * Math.PI * radius
            const arc = (circumference - gap) * ((value ?? 0) / 100)

            return (
              <g key={axis.id} opacity={isAvailable ? 1 : 0.35}>
                {/* Track — the unfilled remainder of the band */}
                <circle
                  cx={CENTER}
                  cy={CENTER}
                  r={radius}
                  fill="none"
                  stroke="var(--color-line-soft)"
                  strokeWidth="7"
                  strokeLinecap="round"
                  strokeDasharray={`${circumference - gap} ${gap + 20}`}
                  transform={`rotate(${-90 + index * 9} ${CENTER} ${CENTER})`}
                />

                {/* Value arc */}
                <motion.circle
                  cx={CENTER}
                  cy={CENTER}
                  r={radius}
                  fill="none"
                  stroke={color}
                  strokeWidth="7"
                  strokeLinecap="round"
                  strokeDasharray={arc}
                  strokeDashoffset={circumference - gap}
                  transform={`rotate(${-90 + index * 9} ${CENTER} ${CENTER})`}
                  filter="url(#dna-glow)"
                  initial={animate && isAvailable ? { strokeDashoffset: circumference - gap } : false}
                  animate={{ strokeDashoffset: circumference - gap - arc }}
                  transition={{
                    duration: 1.1,
                    // Staggered so the specimen "develops" band by band.
                    delay: index * 0.11,
                    ease: [0.16, 1, 0.3, 1],
                  }}
                />

                {/* Radial tick density encodes the value as texture */}
                {isAvailable &&
                  Array.from({
                    length: Math.round((value ?? 0) / 12.5) + 1,
                  }).map((_, tick) => {
                    const angle =
                      ((tick * 360) / (((value ?? 0) / 12.5) + 1)) *
                      (Math.PI / 180)
                    const r1 = radius - 4
                    const r2 = radius - 9
                    return (
                      <line
                        key={tick}
                        x1={CENTER + Math.cos(angle) * r1}
                        y1={CENTER + Math.sin(angle) * r1}
                        x2={CENTER + Math.cos(angle) * r2}
                        y2={CENTER + Math.sin(angle) * r2}
                        stroke={color}
                        strokeWidth="0.8"
                        opacity="0.5"
                      />
                    )
                  })}

                {/* Band label at the band's start angle */}
                <text
                  x={CENTER}
                  y={CENTER - radius - 7}
                  textAnchor="middle"
                  className="mono-label"
                  fill="var(--color-text-dim)"
                  style={{ fontSize: 8, letterSpacing: '0.16em' }}
                >
                  {t(axis.key).toUpperCase()}
                </text>
                <text
                  x={CENTER}
                  y={CENTER - radius - 17}
                  textAnchor="middle"
                  fill={isAvailable ? color : 'var(--color-text-dim)'}
                  style={{
                    fontSize: isAvailable ? 11 : 8,
                    fontWeight: 500,
                    fontFamily: 'var(--font-mono)',
                    letterSpacing: isAvailable ? undefined : '0.08em',
                  }}
                >
                  {isAvailable ? value : isArabic ? 'غير متاح' : 'N/A'}
                </text>
              </g>
            )
          })}

          {/* Core — tinted by the dominant axis */}
          <circle cx={CENTER} cy={CENTER} r="26" fill="var(--color-surface-inset)" />
          <motion.circle
            cx={CENTER}
            cy={CENTER}
            r="26"
            fill="none"
            stroke={coreColor}
            strokeWidth="1"
            initial={animate ? { opacity: 0 } : false}
            animate={{ opacity: 0.75 }}
            transition={{ duration: 0.9, delay: 0.5 }}
          />
          <circle cx={CENTER} cy={CENTER} r="9" fill={coreColor} opacity="0.85" />
          <circle cx={CENTER} cy={CENTER} r="3.5" fill="var(--color-surface-inset)" />
        </svg>
      </div>

      {/* ---------------- Legend ---------------- */}
      <div className="w-full min-w-0">
        <ul className="space-y-2.5">
          {AXES.map((axis, index) => {
            const value = dna[axis.id]
            const isAvailable = value !== null
            const color = dnaColorForValue(value ?? 0)
            return (
              <motion.li
                key={axis.id}
                initial={{ opacity: 0, x: 8 }}
                animate={{ opacity: isAvailable ? 1 : 0.45, x: 0 }}
                transition={{ delay: 0.3 + index * 0.07, duration: 0.4 }}
                className="flex items-center gap-3"
              >
                <span
                  aria-hidden
                  className="size-1.5 shrink-0 rounded-full"
                  style={{
                    // An unmeasured axis gets no coloured dot — a dot
                    // would imply a signal was found.
                    background: isAvailable ? color : 'var(--color-line-bright)',
                  }}
                />
                <span className="flex-1 text-[0.82rem] text-text-muted">
                  {t(axis.key)}
                </span>

                {isAvailable ? (
                  <>
                    {/* Inline micro-bar: value readable without the specimen */}
                    <span className="h-px w-12 shrink-0 bg-line" aria-hidden>
                      <motion.span
                        className="block h-px"
                        style={{ background: color }}
                        initial={animate ? { width: 0 } : false}
                        animate={{ width: `${value}%` }}
                        transition={{
                          duration: 0.8,
                          delay: 0.35 + index * 0.07,
                          ease: [0.16, 1, 0.3, 1],
                        }}
                      />
                    </span>
                    <span
                      className="w-7 shrink-0 text-end font-mono text-xs tabular-nums"
                      style={{ color }}
                      dir="ltr"
                    >
                      {value}
                    </span>
                  </>
                ) : (
                  <span
                    className="w-16 shrink-0 text-end font-mono text-[0.68rem] tracking-wider text-text-dim"
                    title={
                      isArabic
                        ? 'لا ينطبق على هذا النوع من الإشارة'
                        : 'Not applicable to this signal type'
                    }
                  >
                    {isArabic ? 'غير متاح' : 'N/A'}
                  </span>
                )}
              </motion.li>
            )
          })}
        </ul>

        <p className="mt-4 text-[0.7rem] leading-relaxed text-text-dim/80">
          {t('dna.scaleLabel')}
        </p>

        {/* When an axis was not measured, say so explicitly rather than
            letting the reader assume a low score. */}
        {hasUnavailable && (
          <p className="mt-2 text-[0.7rem] leading-relaxed text-text-dim/70">
            {isArabic
              ? `أُقيس ${measuredCount} من ٥ محاور؛ المحاور غير المنطبقة على هذا النوع من الإشارة لا تُعرض كقيمة.`
              : `${measuredCount} of 5 axes measured. Axes marked N/A do not apply to this signal type and are not scored.`}
          </p>
        )}
      </div>
    </div>
  )
}
