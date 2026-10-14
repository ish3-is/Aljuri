import { AnimatePresence, motion, useMotionValue, useSpring } from 'motion/react'
import { useCallback, useMemo, useRef, useState } from 'react'
import { useI18n } from '../../i18n/useI18n'
import { cn } from '../../lib/utils'
import type { InvestigationState, RiskLevel } from '../../types/analysis'

/* ============================================================
   BASIRAH INTELLIGENCE CORE

   The visual centre of the product. Five concentric systems:
     1. ambient bloom       — low-intensity depth behind everything
     2. aperture rings      — counter-rotating, speed tracks state
     3. orbital markers     — nodes on inclined paths
     4. scan plane          — a horizontal sweep during analysis
     5. signal core         — the lens that carries the verdict

   State is communicated by *speed and intensity*, not by colour alone:
   a user who cannot distinguish the palette still sees the machine
   change mode.
   ============================================================ */

interface IntelligenceCoreProps {
  state: InvestigationState
  riskLevel?: RiskLevel | null
  className?: string
}

/** Ring rotation speeds per state (seconds per revolution). */
const RING_SPEED: Record<
  InvestigationState,
  { outer: number; inner: number; scanOpacity: number; glow: number }
> = {
  idle: { outer: 34, inner: 46, scanOpacity: 0.35, glow: 0.28 },
  dragging: { outer: 20, inner: 27, scanOpacity: 0.5, glow: 0.45 },
  input_received: { outer: 24, inner: 32, scanOpacity: 0.45, glow: 0.38 },
  analyzing: { outer: 8, inner: 12, scanOpacity: 1, glow: 0.7 },
  result: { outer: 44, inner: 60, scanOpacity: 0.2, glow: 0.34 },
  /* Analysis failed. The core dims and slows rather than pretending to
     keep working — there is nothing to scan. */
  error: { outer: 60, inner: 80, scanOpacity: 0, glow: 0.12 },
}

const ORBIT_COUNT = 7

export function IntelligenceCore({
  state,
  riskLevel = null,
  className,
}: IntelligenceCoreProps) {
  const { t } = useI18n()
  const [hovered, setHovered] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Pointer-driven parallax. Motion values + springs only: no re-render
  // per pointer event.
  const pointerX = useSpring(useMotionValue(0), { stiffness: 120, damping: 20 })
  const pointerY = useSpring(useMotionValue(0), { stiffness: 120, damping: 20 })
  const tiltX = useSpring(useMotionValue(0), { stiffness: 150, damping: 22 })
  const tiltY = useSpring(useMotionValue(0), { stiffness: 150, damping: 22 })

  const handlePointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      const node = containerRef.current
      if (!node) return
      const rect = node.getBoundingClientRect()
      const nx = (event.clientX - rect.left) / rect.width - 0.5
      const ny = (event.clientY - rect.top) / rect.height - 0.5
      // Shift the whole core slightly toward the cursor (magnetic pull)…
      pointerX.set(nx * 14)
      pointerY.set(ny * 14)
      // …and tilt the 3D plane a little further for depth.
      tiltY.set(nx * 9)
      tiltX.set(-ny * 9)
    },
    [pointerX, pointerY, tiltX, tiltY],
  )

  const handlePointerLeave = useCallback(() => {
    pointerX.set(0)
    pointerY.set(0)
    tiltX.set(0)
    tiltY.set(0)
    setHovered(false)
  }, [pointerX, pointerY, tiltX, tiltY])

  const speeds = RING_SPEED[state]
  const isAnalyzing = state === 'analyzing'
  const isDragging = state === 'dragging'
  const isResult = state === 'result'

  /** The core takes the verdict colour once a result exists. */
  const coreColor = useMemo(() => {
    if (!isResult || !riskLevel) return 'var(--color-signal)'
    if (riskLevel === 'high_risk') return 'var(--color-danger)'
    if (riskLevel === 'caution') return 'var(--color-caution)'
    return 'var(--color-trusted)'
  }, [isResult, riskLevel])

  const statusCopy = useMemo(() => {
    switch (state) {
      case 'dragging':
        return t('core.dragHint')
      case 'analyzing':
        return t('core.analyzingHint')
      case 'result':
        return t('core.resultHint')
      case 'input_received':
        return t('core.analyzingHint')
      default:
        return t('core.idleHint')
    }
  }, [state, t])

  const statusLabel = useMemo(() => {
    switch (state) {
      case 'dragging':
        return t('core.statusDragging')
      case 'analyzing':
      case 'input_received':
        return t('core.statusAnalyzing')
      case 'result':
        return t('core.statusResult')
      default:
        return t('core.statusIdle')
    }
  }, [state, t])

  return (
    <div
      ref={containerRef}
      onPointerMove={handlePointerMove}
      onPointerEnter={() => setHovered(true)}
      onPointerLeave={handlePointerLeave}
      className={cn('relative aspect-square w-full max-w-[520px]', className)}
      style={{ perspective: 1100 }}
      aria-hidden
    >
      <motion.div
        className="relative size-full"
        style={{ x: pointerX, y: pointerY, rotateX: tiltX, rotateY: tiltY }}
      >
        {/* ---------- 1. Ambient bloom ---------- */}
        <motion.div
          className="absolute inset-[6%] rounded-full blur-[70px]"
          style={{
            background: `radial-gradient(circle at 50% 50%, ${coreColor} 0%, transparent 68%)`,
          }}
          animate={{ opacity: speeds.glow * (hovered ? 1.5 : 1) }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />

        <svg viewBox="0 0 400 400" className="absolute inset-0 size-full overflow-visible">
          <defs>
            <radialGradient id="core-fill" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor={coreColor} stopOpacity="0.30" />
              <stop offset="55%" stopColor="var(--color-intel)" stopOpacity="0.10" />
              <stop offset="100%" stopColor="var(--color-void)" stopOpacity="0" />
            </radialGradient>
            <linearGradient id="ring-grad" x1="0" y1="0" x2="1" y2="1">
              <stop stopColor="var(--color-signal)" stopOpacity="0.9" />
              <stop offset="1" stopColor="var(--color-intel)" stopOpacity="0.9" />
            </linearGradient>
          </defs>

          {/* ---------- 2. Static reference grid ---------- */}
          <g opacity="0.16" stroke="var(--color-line-bright)" strokeWidth="0.5">
            {[1, 2, 3].map((i) => (
              <circle key={i} cx="200" cy="200" r={i * 45} fill="none" strokeDasharray="1 6" />
            ))}
            <path d="M200 20V380M20 200H380" strokeDasharray="2 8" />
          </g>

          {/* ---------- 3. Outer aperture ring ---------- */}
          <motion.g
            style={{ originX: '200px', originY: '200px' }}
            animate={{ rotate: 360 }}
            transition={{ duration: speeds.outer, repeat: Infinity, ease: 'linear' }}
          >
            <circle
              cx="200"
              cy="200"
              r="176"
              fill="none"
              stroke="url(#ring-grad)"
              strokeWidth="1.1"
              strokeDasharray="52 26"
              strokeLinecap="round"
              opacity="0.75"
            />
            {/* Ring ticks — reads as an instrument dial */}
            {Array.from({ length: 48 }).map((_, i) => {
              const angle = (i / 48) * Math.PI * 2
              const long = i % 4 === 0
              const r1 = 176
              const r2 = 176 - (long ? 11 : 5)
              return (
                <line
                  key={i}
                  x1={200 + Math.cos(angle) * r1}
                  y1={200 + Math.sin(angle) * r1}
                  x2={200 + Math.cos(angle) * r2}
                  y2={200 + Math.sin(angle) * r2}
                  stroke="var(--color-signal)"
                  strokeWidth={long ? 1.1 : 0.5}
                  opacity={long ? 0.5 : 0.22}
                />
              )
            })}
          </motion.g>

          {/* ---------- 4. Counter-rotating inner ring ---------- */}
          <motion.g
            style={{ originX: '200px', originY: '200px' }}
            animate={{ rotate: -360 }}
            transition={{ duration: speeds.inner, repeat: Infinity, ease: 'linear' }}
          >
            <circle
              cx="200"
              cy="200"
              r="148"
              fill="none"
              stroke="var(--color-intel)"
              strokeWidth="0.9"
              strokeDasharray="8 22"
              strokeLinecap="round"
              opacity="0.55"
            />
          </motion.g>

          {/* ---------- 5. Inclined orbital paths ---------- */}
          <g fill="none" stroke="var(--color-signal)" strokeWidth="0.5" opacity="0.28">
            <ellipse cx="200" cy="200" rx="126" ry="44" />
            <ellipse
              cx="200"
              cy="200"
              rx="126"
              ry="44"
              transform="rotate(58 200 200)"
            />
            <ellipse
              cx="200"
              cy="200"
              rx="126"
              ry="44"
              transform="rotate(-58 200 200)"
            />
          </g>

          {/* ---------- 6. Orbiting signal markers ---------- */}
          {Array.from({ length: ORBIT_COUNT }).map((_, i) => {
            // Each marker rides one of the three inclined orbits.
            const orbitAngle = (i / ORBIT_COUNT) * Math.PI * 2
            const tilt = [0, 58, -58, 0, 58, -58, 30][i % 7]
            const duration = isAnalyzing ? 5 + i * 0.7 : 16 + i * 2.4
            return (
              <motion.g
                key={i}
                style={{ originX: '200px', originY: '200px' }}
                animate={{ rotate: orbitAngle }}
                transition={{ duration, repeat: Infinity, ease: 'linear' }}
              >
                <g transform={`rotate(${tilt} 200 200)`}>
                  <circle
                    cx="200"
                    cy="74"
                    r={i % 3 === 0 ? 4 : 2.6}
                    fill={i % 3 === 0 ? 'var(--color-signal)' : 'var(--color-intel)'}
                    opacity={isAnalyzing ? 0.95 : 0.6}
                  />
                  {/* Trailing wake — implies direction of travel */}
                  <circle
                    cx="200"
                    cy="74"
                    r="8"
                    fill="none"
                    stroke={coreColor}
                    strokeWidth="0.6"
                    opacity={isAnalyzing ? 0.4 : 0.16}
                    className={isAnalyzing ? 'animate-pulse-node' : undefined}
                    style={{ transformOrigin: '200px 74px' }}
                  />
                </g>
              </motion.g>
            )
          })}

          {/* ---------- 7. Signal lines (analysis only) ---------- */}
          <AnimatePresence>
            {isAnalyzing && (
              <motion.g
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.5 }}
              >
                {Array.from({ length: 6 }).map((_, i) => {
                  const angle = (i / 6) * Math.PI * 2 + 0.4
                  const x1 = 200 + Math.cos(angle) * 52
                  const y1 = 200 + Math.sin(angle) * 52
                  const x2 = 200 + Math.cos(angle) * 142
                  const y2 = 200 + Math.sin(angle) * 142
                  return (
                    <line
                      key={i}
                      x1={x1}
                      y1={y1}
                      x2={x2}
                      y2={y2}
                      stroke="var(--color-signal)"
                      strokeWidth="0.8"
                      strokeDasharray="4 10"
                      opacity="0.55"
                      className="animate-signal-dash"
                      style={{ animationDelay: `${i * 0.28}s` }}
                    />
                  )
                })}
              </motion.g>
            )}
          </AnimatePresence>

          {/* ---------- 8. Scan plane ---------- */}
          <motion.g
            initial={{ opacity: 0 }}
            animate={{ opacity: speeds.scanOpacity }}
            transition={{ duration: 0.6 }}
          >
            <rect
              x="24"
              y="197"
              width="352"
              height="3"
              fill={`url(#ring-grad)`}
              opacity="0.5"
              className="animate-scan"
            />
            <rect
              x="24"
              y="186"
              width="352"
              height="25"
              fill="url(#core-fill)"
              opacity="0.5"
              className="animate-scan"
              style={{ animationDelay: '0.05s' }}
            />
          </motion.g>

          {/* ---------- 9. The lens / signal core ---------- */}
          <circle cx="200" cy="200" r="86" fill="url(#core-fill)" />
          <circle
            cx="200"
            cy="200"
            r="62"
            fill="var(--color-surface-inset)"
            stroke={coreColor}
            strokeWidth="1"
            opacity="0.9"
          />
          {/* Aperture blades */}
          <g opacity="0.85">
            {Array.from({ length: 6 }).map((_, i) => {
              const angle = (i / 6) * Math.PI * 2
              return (
                <line
                  key={i}
                  x1={200 + Math.cos(angle) * 22}
                  y1={200 + Math.sin(angle) * 22}
                  x2={200 + Math.cos(angle + 0.5) * 60}
                  y2={200 + Math.sin(angle + 0.5) * 60}
                  stroke={coreColor}
                  strokeWidth="0.9"
                  opacity="0.5"
                />
              )
            })}
          </g>
          <circle
            cx="200"
            cy="200"
            r="18"
            fill={coreColor}
            className="animate-breathe"
            opacity="0.85"
          />
          <circle cx="200" cy="200" r="7" fill="var(--color-void)" />

          {/* Hover emphasis ring — responds to the cursor */}
          <motion.circle
            cx="200"
            cy="200"
            r="86"
            fill="none"
            stroke={coreColor}
            strokeWidth="0.8"
            animate={{ opacity: hovered ? 0.65 : 0, scale: hovered ? 1.06 : 1 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            style={{ originX: '200px', originY: '200px' }}
          />
        </svg>

        {/* ---------- 10. State label ---------- */}
        <div className="pointer-events-none absolute inset-x-0 bottom-[6%] text-center">
          <AnimatePresence mode="wait">
            <motion.div
              key={`${state}-${statusLabel}`}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
            >
              <p
                className="mono-label"
                style={{ color: coreColor, opacity: 0.9 }}
              >
                {statusLabel}
              </p>
              <p className="mt-1.5 text-sm text-text-muted">{statusCopy}</p>
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Drag-mode banner */}
        <AnimatePresence>
          {isDragging && (
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              className="pointer-events-none absolute inset-x-0 top-1/2 -translate-y-1/2 text-center"
            >
              <span
                className="mono-label rounded-full border border-signal/40 bg-signal/10 px-4 py-2 text-signal backdrop-blur-sm"
              >
                {t('core.dragHint')}
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  )
}
