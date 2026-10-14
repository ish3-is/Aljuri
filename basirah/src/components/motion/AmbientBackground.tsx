import { motion, useMotionValue, useSpring } from 'motion/react'
import { useEffect, useMemo } from 'react'
import { useRichMotion } from '../../hooks/useEnvironment'

/* ============================================================
   AMBIENT BACKGROUND

   Depth in four cheap layers: a grid, two radial glows, a sparse
   particle field and a faint noise wash. Everything is fixed-position
   and pointer-events-none, so it never intercepts input or triggers
   layout.

   Particle count scales with the viewport and is skipped entirely on
   touch / reduced-motion, where an ambient loop is cost without payoff.
   ============================================================ */

const PARTICLE_COUNT_DESKTOP = 46
const PARTICLE_COUNT_TABLET = 24

export function AmbientBackground() {
  const rich = useRichMotion()

  // Slow parallax follow of the page scroll — the background drifts at a
  // fraction of scroll distance, which is what sells the depth. Writes
  // straight to motion values, so scrolling causes no React render.
  const rawX = useMotionValue(0)
  const rawY = useMotionValue(0)
  const x = useSpring(rawX, { stiffness: 40, damping: 26 })
  const y = useSpring(rawY, { stiffness: 40, damping: 26 })

  useEffect(() => {
    if (!rich) return
    let frame = 0

    const onScroll = () => {
      if (frame) return
      frame = window.requestAnimationFrame(() => {
        frame = 0
        const max = Math.max(
          document.documentElement.scrollHeight - window.innerHeight,
          1,
        )
        const progress = window.scrollY / max
        rawX.set(progress * -26)
        rawY.set(progress * -18)
      })
    }

    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      if (frame) window.cancelAnimationFrame(frame)
    }
  }, [rich, rawX, rawY])

  const particles = useMemo(() => {
    const count = rich ? PARTICLE_COUNT_DESKTOP : PARTICLE_COUNT_TABLET
    // Deterministic pseudo-random layout: no Math.random in render, so
    // the field is stable across re-renders and SSR-safe.
    return Array.from({ length: count }, (_, i) => {
      const seed = (i * 9301 + 49297) % 233280
      const r1 = seed / 233280
      const seed2 = (i * 4523 + 7919) % 233280
      const r2 = seed2 / 233280
      return {
        id: i,
        x: r1 * 100,
        y: r2 * 100,
        size: 0.6 + r2 * 1.5,
        delay: r1 * 8,
        duration: 9 + r2 * 14,
      }
    })
  }, [rich])

  return (
    <div
      aria-hidden
      data-ambient
      className="basirah-ambient pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-void"
    >
      {/* --- Layer 1: base gradient wash --- */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(120% 80% at 50% -10%, var(--bas-wash-top) 0%, transparent 60%)',
        }}
      />

      {/* --- Layer 2: technical grid --- */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            'linear-gradient(var(--bas-grid) 1px, transparent 1px), linear-gradient(90deg, var(--bas-grid) 1px, transparent 1px)',
          backgroundSize: '68px 68px',
          opacity: 'var(--bas-grid-opacity)',
          // Fade the grid out toward the bottom so content stays readable.
          maskImage:
            'radial-gradient(120% 90% at 50% 20%, black 0%, transparent 78%)',
          WebkitMaskImage:
            'radial-gradient(120% 90% at 50% 20%, black 0%, transparent 78%)',
        }}
      />

      {/* --- Layer 3: drifting glows (parallax) --- */}
      <motion.div
        style={{ x, y }}
        className="absolute inset-0"
      >
        <div
          className="animate-drift absolute -top-[18%] left-[6%] size-[42rem] rounded-full blur-[130px]"
          style={{
            background:
              'radial-gradient(circle, var(--bas-glow-cyan) 0%, transparent 68%)',
            opacity: 'var(--bas-glow-strength)',
          }}
        />
        <div
          className="animate-drift absolute top-[42%] right-[2%] size-[38rem] rounded-full blur-[140px]"
          style={{
            background:
              'radial-gradient(circle, var(--bas-glow-violet) 0%, transparent 68%)',
            opacity: 'var(--bas-glow-strength)',
            animationDelay: '-11s',
          }}
        />
      </motion.div>

      {/* --- Layer 4: sparse signal particles --- */}
      <div className="absolute inset-0">
        {particles.map((particle) => (
          <motion.span
            key={particle.id}
            className="absolute rounded-full bg-signal"
            style={{
              insetInlineStart: `${particle.x}%`,
              top: `${particle.y}%`,
              width: particle.size,
              height: particle.size,
              opacity: 0.16,
            }}
            animate={
              rich
                ? { opacity: [0.08, 0.3, 0.08], y: [0, -14, 0] }
                : { opacity: 0.12 }
            }
            transition={{
              duration: particle.duration,
              delay: particle.delay,
              repeat: rich ? Infinity : 0,
              ease: 'easeInOut',
            }}
          />
        ))}
      </div>

      {/* --- Layer 5: noise wash, kills gradient banding --- */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='140' height='140' filter='url(%23n)' opacity='0.42'/%3E%3C/svg%3E\")",
          // The token resolves to a CSS blend keyword; TS cannot see
          // through the var() indirection, so the cast is the honest
          // boundary here.
          mixBlendMode:
            'var(--bas-noise-blend)' as React.CSSProperties['mixBlendMode'],
          opacity: 'var(--bas-noise-opacity)',
        }}
      />

      {/* --- Layer 6: vignette, pulls focus to the centre --- */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(110% 80% at 50% 45%, transparent 45%, var(--bas-vignette) 100%)',
          opacity: 'var(--bas-vignette-opacity)',
        }}
      />
    </div>
  )
}
