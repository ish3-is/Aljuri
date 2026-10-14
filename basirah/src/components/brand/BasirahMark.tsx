import { useId } from 'react'

/* ============================================================
   The BASIRAH mark.

   An eye/aperture inside an aperture ring: the product looks beyond
   what appears. Drawn as SVG so it inherits currentColor, scales
   without artifacts, and needs no asset request.
   ============================================================ */

interface BasirahMarkProps {
  size?: number
  className?: string
  /** Adds a slow rotation — used only on the ambient header mark. */
  animated?: boolean
}

export function BasirahMark({
  size = 32,
  className,
  animated = false,
}: BasirahMarkProps) {
  const gradientId = useId()

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient id={gradientId} x1="4" y1="4" x2="44" y2="44">
          <stop stopColor="var(--color-signal)" />
          <stop offset="1" stopColor="var(--color-intel)" />
        </linearGradient>
      </defs>

      {/* Outer aperture ring, segmented like a lens barrel */}
      <g className={animated ? 'origin-center animate-spin-cw' : undefined}>
        <circle
          cx="24"
          cy="24"
          r="21"
          stroke={`url(#${gradientId})`}
          strokeWidth="1.25"
          strokeDasharray="26 8"
          strokeLinecap="round"
          opacity="0.85"
        />
      </g>

      {/* Counter-rotating inner arc — implies depth without 3D */}
      <g className={animated ? 'origin-center animate-spin-ccw' : undefined}>
        <circle
          cx="24"
          cy="24"
          r="15"
          stroke="var(--color-signal)"
          strokeWidth="0.75"
          strokeDasharray="4 10"
          strokeLinecap="round"
          opacity="0.4"
        />
      </g>

      {/* The aperture itself: an eye-shaped lens */}
      <path
        d="M9 24C14 16.5 19 13.5 24 13.5C29 13.5 34 16.5 39 24C34 31.5 29 34.5 24 34.5C19 34.5 14 31.5 9 24Z"
        stroke={`url(#${gradientId})`}
        strokeWidth="1.6"
        strokeLinejoin="round"
      />

      {/* Iris / pupil */}
      <circle cx="24" cy="24" r="5" fill={`url(#${gradientId})`} opacity="0.9" />
      <circle cx="24" cy="24" r="1.75" fill="var(--color-void)" />

      {/* Signal ticks — evidence sampling */}
      <g stroke="var(--color-signal)" strokeWidth="1" opacity="0.55" strokeLinecap="round">
        <path d="M24 3.5V7" />
        <path d="M24 41v3.5" />
        <path d="M3.5 24H7" />
        <path d="M41 24h3.5" />
      </g>
    </svg>
  )
}
