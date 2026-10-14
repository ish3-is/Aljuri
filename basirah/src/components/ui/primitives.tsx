import { motion, useMotionValue, useSpring } from 'motion/react'
import {
  useCallback,
  useRef,
  type ButtonHTMLAttributes,
  type ReactNode,
} from 'react'
import { cn } from '../../lib/utils'

/* ============================================================
   Shared UI primitives.

   Deliberately few: the product's identity comes from the Core, DNA
   and Graph, not from a large kit of wrapper components.
   ============================================================ */

/* ------------------------------------------------------------------ */
/* Magnetic wrapper                                                   */
/* ------------------------------------------------------------------ */

interface MagneticProps {
  children: ReactNode
  /** Maximum displacement in px at the pointer edge of the element. */
  strength?: number
  className?: string
}

/**
 * Pulls its child subtly toward the cursor.
 *
 * Implemented with motion values + springs so pointer movement never
 * triggers a React render — only transform writes to the DOM node.
 * Applied sparingly (primary actions, the Core), never on lists.
 */
export function Magnetic({ children, strength = 10, className }: MagneticProps) {
  const ref = useRef<HTMLDivElement>(null)
  const x = useSpring(useMotionValue(0), { stiffness: 220, damping: 18, mass: 0.4 })
  const y = useSpring(useMotionValue(0), { stiffness: 220, damping: 18, mass: 0.4 })

  const handlePointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      const node = ref.current
      if (!node) return
      const rect = node.getBoundingClientRect()
      const relX = (event.clientX - rect.left) / rect.width - 0.5
      const relY = (event.clientY - rect.top) / rect.height - 0.5
      x.set(relX * strength * 2)
      y.set(relY * strength * 2)
    },
    [strength, x, y],
  )

  const handlePointerLeave = useCallback(() => {
    x.set(0)
    y.set(0)
  }, [x, y])

  return (
    <motion.div
      ref={ref}
      className={className}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
      style={{ x, y }}
    >
      {children}
    </motion.div>
  )
}

/* ------------------------------------------------------------------ */
/* Button                                                             */
/* ------------------------------------------------------------------ */

type ButtonVariant = 'primary' | 'ghost' | 'subtle'

/**
 * Native button props, minus the animation-event handlers that conflict
 * with Motion's own `onAnimationStart` signature.
 */
type NativeButtonProps = Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  'onAnimationStart' | 'onDragStart' | 'onDragEnd' | 'onDrag'
>

interface ButtonProps extends NativeButtonProps {
  variant?: ButtonVariant
  magnetic?: boolean
  children: ReactNode
}

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary:
    'bg-signal/12 text-signal border-signal/35 hover:bg-signal/18 hover:border-signal/55 hover:text-signal',
  subtle:
    'bg-surface-raised/70 text-text-muted border-line hover:text-text hover:border-line-bright',
  ghost: 'bg-transparent text-text-dim border-transparent hover:text-text',
}

/** Primary action. Uses `active:` scale rather than a spring for tap
    feedback — a tap is an impulse, not an orbit. */
export function Button({
  variant = 'primary',
  magnetic = false,
  className,
  children,
  ...rest
}: ButtonProps) {
  const button = (
    <motion.button
      whileTap={{ scale: 0.97 }}
      transition={{ type: 'spring', stiffness: 400, damping: 24 }}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-full border px-5 py-2.5',
        'text-[0.8rem] font-medium tracking-[0.02em] transition-colors duration-200',
        'disabled:pointer-events-none disabled:opacity-40',
        BUTTON_VARIANTS[variant],
        className,
      )}
      {...rest}
    >
      {children}
    </motion.button>
  )

  if (!magnetic) return button
  return <Magnetic strength={6}>{button}</Magnetic>
}

/* ------------------------------------------------------------------ */
/* Panel                                                              */
/* ------------------------------------------------------------------ */

interface PanelProps {
  children: ReactNode
  className?: string
  /** Adds the accent hairline along the top edge. */
  accent?: boolean
}

/**
 * The one surface primitive. Panels are frameless in spirit: a hairline
 * border and a barely-there fill, never a filled card with a shadow.
 * Corners stay square-ish to read as instrumentation, not as app chrome.
 */
export function Panel({ children, className, accent = false }: PanelProps) {
  return (
    <div
      className={cn(
        'relative rounded-lg border border-line/70 bg-surface/45',
        className,
      )}
    >
      {accent && (
        <span
          aria-hidden
          className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-signal/45 to-transparent"
        />
      )}
      {children}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Section heading                                                    */
/* ------------------------------------------------------------------ */

interface SectionLabelProps {
  index: string
  title: string
  subtitle?: string
  className?: string
}

/** Forensic-style section marker: index, title, hairline. */
export function SectionLabel({
  index,
  title,
  subtitle,
  className,
}: SectionLabelProps) {
  return (
    <div className={cn('mb-6', className)}>
      <div className="flex items-center gap-3">
        <span className="mono-label text-signal/70">{index}</span>
        <h2 className="text-base font-normal tracking-tight text-text">{title}</h2>
        <span aria-hidden className="hairline h-px flex-1" />
      </div>
      {subtitle && (
        <p className="mt-2 text-sm leading-relaxed text-text-dim">{subtitle}</p>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Mock badge                                                         */
/* ------------------------------------------------------------------ */

/**
 * Persistent, non-dismissible marker that the surrounding data is
 * simulated. This is a product-integrity control, not decoration —
 * it must never be removable by the user.
 */
export function MockBadge({ label, className }: { label: string; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border border-caution/25',
        'bg-caution/8 px-2.5 py-1 text-[0.65rem] tracking-[0.14em]',
        'text-caution/90 uppercase',
        className,
      )}
    >
      <span aria-hidden className="size-1 rounded-full bg-caution" />
      {label}
    </span>
  )
}

/**
 * Counterpart to MockBadge for a result that came from the real
 * analysis pipeline. Phase 2 introduced this: labelling a live backend
 * result as "Mock" would understate it, and labelling a mock result as
 * live would be far worse.
 */
export function LiveBadge({ label, className }: { label: string; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border border-trusted/25',
        'bg-trusted/8 px-2.5 py-1 text-[0.65rem] tracking-[0.14em]',
        'text-trusted/90 uppercase',
        className,
      )}
    >
      <span aria-hidden className="size-1 rounded-full bg-trusted" />
      {label}
    </span>
  )
}
