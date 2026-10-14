import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import basirahMark from '../../assets/basirah-mark.png'
import { usePrefersReducedMotion } from '../../hooks/useEnvironment'
import { useI18n } from '../../i18n/useI18n'

/* ============================================================
   BRAND REVEAL

   A short identity beat on FIRST ENTRY, not a splash screen.

   It is explicitly NON-BLOCKING in the strongest sense: the app
   underneath is fully interactive from the first frame, the reveal
   layer is `pointer-events-none`, and nothing waits for it. A reader
   who ignores it entirely loses nothing except a logo animation.

   It runs ONCE per session. A reader who navigates away and back
   must not be held at a logo again — that is the difference between
   a brand reveal and an obstruction.

   The arc is ~1100ms: mark scales and fades up, a ring expands, a
   scan pulse crosses the wordmark, then the whole layer fades out
   while Overview is already readable underneath.

   UNDER REDUCED MOTION it degrades to a plain 400ms fade with no
   scale, no ring, no scan — the identity still appears, and nothing
   moves.
   ============================================================ */

const SESSION_KEY = 'basirah.reveal.v1'

/** Total duration in ms, including the fade-out tail. */
const DURATION_MS = 1100

function hasRevealed(): boolean {
  try {
    return window.sessionStorage.getItem(SESSION_KEY) === '1'
  } catch {
    // Private mode: reveal once per page load instead of per session.
    return false
  }
}

function markRevealed(): void {
  try {
    window.sessionStorage.setItem(SESSION_KEY, '1')
  } catch {
    // Non-fatal. Worst case the reader sees the reveal twice.
  }
}

/**
 * Whether the reveal should run, decided ONCE at mount.
 *
 * This is a lazy initialiser rather than an effect + setState: the
 * answer cannot change after the first render, so computing it in an
 * effect would cause a second render for no reason — and would
 * briefly paint the `null` branch. Reading sessionStorage during
 * initialisation is safe here because this is a browser-only SPA
 * with no SSR.
 */
function initialVisibility(): boolean {
  if (typeof window === 'undefined') return false
  if (hasRevealed()) return false
  markRevealed()
  return true
}

export function BrandReveal() {
  const { t, tLatin, language } = useI18n()
  const reduced = usePrefersReducedMotion()

  // `true` until the reveal finishes; false if it was already seen.
  const [visible, setVisible] = useState(initialVisibility)

  // The timer is the only thing that changes state afterwards.
  useEffect(() => {
    if (!visible) return
    const id = window.setTimeout(() => setVisible(false), DURATION_MS)
    return () => window.clearTimeout(id)
  }, [visible])

  // Skip-to-content must win over the reveal. The layer is
  // pointer-events-none, so focusing past it is safe.
  useEffect(() => {
    if (!visible) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' || event.key === 'Enter') setVisible(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [visible])

  const isArabic = language === 'ar'

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          // A decorative, non-interactive overlay: hidden from the
          // accessibility tree entirely, because the brand is
          // already announced by the header and the hero beneath.
          aria-hidden
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: reduced ? 0.35 : 0.45, ease: 'easeInOut' }}
          className="pointer-events-none fixed inset-0 z-[80] flex items-center justify-center bg-[var(--bas-bg)]"
        >
          <div className="relative flex flex-col items-center">
            {/* --- expanding ring: the instrument coming online --- */}
            {!reduced && (
              <motion.span
                aria-hidden
                className="absolute size-40 rounded-full border border-signal/40"
                initial={{ scale: 0.7, opacity: 0 }}
                animate={{ scale: 1.5, opacity: 0 }}
                transition={{ duration: 1, ease: 'easeOut' }}
              />
            )}

            {/* --- the mark --- */}
            <motion.img
              src={basirahMark}
              alt=""
              width={84}
              height={118}
              decoding="sync"
              draggable={false}
              className="relative select-none object-contain"
              initial={reduced ? { opacity: 0 } : { opacity: 0, scale: 0.86 }}
              animate={
                reduced
                  ? { opacity: 1 }
                  : { opacity: 1, scale: 1 }
              }
              transition={
                reduced
                  ? { duration: 0.4 }
                  : { duration: 0.7, ease: [0.16, 1, 0.3, 1] }
              }
            />

            {/* --- wordmark + scan pulse --- */}
            <motion.p
              dir="ltr"
              className="mt-4 text-[0.8rem] tracking-[0.42em] text-text"
              initial={reduced ? { opacity: 0 } : { opacity: 0, y: 8 }}
              animate={reduced ? { opacity: 1 } : { opacity: 1, y: 0 }}
              transition={{
                delay: reduced ? 0.1 : 0.34,
                duration: reduced ? 0.3 : 0.55,
                ease: [0.16, 1, 0.3, 1],
              }}
            >
              {tLatin('brand.name')}
            </motion.p>

            {/* One scan pulse crossing the wordmark, not a loop. */}
            {!reduced && (
              <motion.span
                aria-hidden
                className="absolute inset-x-0 bottom-0 h-px overflow-hidden"
                initial={{ opacity: 0 }}
                animate={{ opacity: [0, 1, 1, 0] }}
                transition={{ duration: 0.9, times: [0, 0.2, 0.6, 1] }}
              >
                <motion.span
                  className="absolute inset-y-0 w-16"
                  style={{
                    background:
                      'linear-gradient(90deg, transparent, var(--bas-accent-cyan), transparent)',
                  }}
                  initial={{ x: '-100%' }}
                  animate={{ x: '700%' }}
                  transition={{ duration: 0.85, delay: 0.36, ease: 'easeInOut' }}
                />
              </motion.span>
            )}

            {/* --- descriptor, bilingual --- */}
            <motion.p
              dir={isArabic ? 'rtl' : 'ltr'}
              className="font-arabic-body mt-3 max-w-[80vw] text-center text-[0.66rem] leading-relaxed text-text-dim"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: reduced ? 0.15 : 0.55, duration: 0.4 }}
            >
              {t('brand.subtitle')}
            </motion.p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}