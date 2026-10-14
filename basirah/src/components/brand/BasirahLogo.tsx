import { motion } from 'motion/react'
import basirahMark from '../../assets/basirah-mark.png'
import { usePrefersReducedMotion } from '../../hooks/useEnvironment'
import { cn } from '../../lib/utils'

/* ============================================================
   BRAND CENTERPIECE

   The official BASIRAH project mark: an eye/magnifier with a check
   mark and fractured-glass motif, above a bilingual wordmark.

   The source PNG is 1024x1024 with content occupying only ~27% of
   the canvas, so `scripts/trim-assets.mjs` produces a padding-free
   copy (447x628, aspect 0.712) that is what this component imports.
   Using the raw file would render the mark at roughly a quarter of
   its intended size and misalign it against adjacent text. The crop
   only removes transparent padding — the aspect ratio is untouched,
   so the mark can never be stretched here.

   Because the mark is PORTRAIT (symbol above wordmark), it is sized
   by HEIGHT and its width follows from the intrinsic ratio. The box
   reserves that width so the orbit rings below cannot reflow when
   the image loads.
   ============================================================ */

interface BasirahLogoProps {
  /** Rendered height in px; width is derived from the aspect ratio. */
  height?: number
  className?: string
  /** Adds the slow scan sweep across the mark. */
  scanning?: boolean
}

export function BasirahLogo({
  height = 168,
  className,
  scanning = true,
}: BasirahLogoProps) {
  const reduced = usePrefersReducedMotion()
  const active = scanning && !reduced

  // 447x628 source → 0.7118 aspect. Reserving the box up front keeps
  // the surrounding layout from shifting once the image decodes.
  const width = Math.round(height * (447 / 628))

  return (
    <div
      className={cn('relative isolate flex items-center justify-center', className)}
      style={{ width, height }}
    >
      {/* --- Orbital glow: two offset radial washes, no particles --- */}
      <motion.span
        aria-hidden
        className="pointer-events-none absolute -inset-[22%] -z-10 blur-[52px]"
        style={{
          background:
            'radial-gradient(ellipse at 38% 32%, color-mix(in srgb, var(--color-signal) 34%, transparent) 0%, transparent 62%), radial-gradient(ellipse at 66% 74%, color-mix(in srgb, var(--color-intel) 30%, transparent) 0%, transparent 60%)',
        }}
        animate={active ? { opacity: [0.5, 0.85, 0.5] } : { opacity: 0.7 }}
        transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut' }}
      />

      {/* --- Orbit ring: one dashed ellipse, counter-rotating slowly --- */}
      <motion.svg
        aria-hidden
        viewBox="0 0 200 260"
        className="pointer-events-none absolute -inset-[14%] -z-10 h-[128%] w-[128%]"
        animate={active ? { rotate: 360 } : undefined}
        transition={{ duration: 64, repeat: Infinity, ease: 'linear' }}
        style={{ transformOrigin: '50% 50%' }}
      >
        <ellipse
          cx="100"
          cy="130"
          rx="96"
          ry="36"
          fill="none"
          stroke="var(--color-signal)"
          strokeWidth="0.6"
          strokeDasharray="3 9"
          opacity="0.32"
          transform="rotate(-28 100 130)"
        />
      </motion.svg>

      {/* --- The mark itself --- */}
      <motion.img
        src={basirahMark}
        alt="BASIRAH بصيرة"
        width={width}
        height={height}
        decoding="async"
        className="relative z-10 h-full w-auto select-none object-contain"
        initial={{ opacity: 0, scale: 0.94 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1] }}
        draggable={false}
      />

      {/* --- Scan sweep: a single slow pass, not a looping strobe --- */}
      {active && (
        <span
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 z-20 h-full overflow-hidden"
        >
          <motion.span
            className="absolute inset-x-0 h-14"
            style={{
              background:
                'linear-gradient(to bottom, transparent, color-mix(in srgb, var(--color-signal) 16%, transparent) 45%, color-mix(in srgb, var(--color-signal) 30%, transparent) 50%, transparent)',
            }}
            animate={{ y: ['-10%', '720%'] }}
            transition={{ duration: 7.5, repeat: Infinity, ease: 'easeInOut' }}
          />
        </span>
      )}

      {/* --- Baseline rule: grounds the mark instead of letting it float --- */}
      <span
        aria-hidden
        className="hairline absolute inset-x-2 -bottom-3 h-px"
      />
    </div>
  )
}