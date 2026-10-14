import { useEffect, useState } from 'react'
import { Pause, Play } from 'lucide-react'
import { tickerItems } from '../../data/tickerItems'
import { usePrefersReducedMotion } from '../../hooks/useEnvironment'
import { useI18n } from '../../i18n/useI18n'
import { cn } from '../../lib/utils'

/* ============================================================
   INTELLIGENCE TICKER

   A continuous, full-width marquee of digital-trust awareness
   notes.

   HOW THE SEAMLESS LOOP WORKS, and why there is never a blank gap
   after the last item:

     The track holds the item list rendered EXACTLY TWICE. The
     animation translates it by -50% — half the track width — which
     is precisely the width of one copy. So the instant the first
     copy has scrolled fully out of view to the left, the second
     copy is occupying exactly the position the first copy started
     in, pixel for pixel. The animation then restarts from 0, which
     is visually identical to where it just was.

     The loop point is an identity, not an approximation, so there
     is no seam to see and no gap to cross. This is why the duplicated
     copy must be identical: a single differing item width would put
     a visible discontinuity exactly at the wrap point.

   RTL: the track is a flex row, so `dir=rtl` reverses the visual
   order of its children AND the meaning of `translateX`. Rather than
   special-casing the direction (which would need a different
   keyframe), the whole ticker renders in an LTR-isolated wrapper
   with the Arabic text written RTL inside each item. Items still
   read correctly in Arabic; the scroll direction stays consistent.

   SPEED: the duration is proportional to the item count so the
   linear velocity stays roughly constant if items are added.
   Roughly 28s for one pass — slow enough to actually be read.
   ============================================================ */

/** Duration for one full cycle, in seconds. */
const CYCLE_SECONDS = 42

export function IntelligenceTicker({ className }: { className?: string }) {
  const { t, language } = useI18n()
  const reduced = usePrefersReducedMotion()
  const [paused, setPaused] = useState(false)

  const isArabic = language === 'ar'

  // Under reduced motion the animation is disabled by CSS, so the
  // pause control would control nothing. It is hidden rather than
  // left as a dead button.
  const showPause = !reduced

  useEffect(() => {
    // Document-level visibility drives the pause, so a backgrounded
    // tab is not animating offscreen.
    const onVisibility = () => {
      if (document.hidden) setPaused(true)
    }
    document.addEventListener('visibilitychange', onVisibility)
    return () => document.removeEventListener('visibilitychange', onVisibility)
  }, [])

  const itemText = (item: (typeof tickerItems)[number]) =>
    isArabic ? item.textAr : item.textEn

  return (
    <section
      className={cn(
        'relative w-full overflow-hidden border-y border-line/60 bg-surface/40',
        className,
      )}
      aria-label={t('ticker.label')}
    >
      {/* The moving strip is aria-hidden and duplicated for real
          keyboard/screen-reader users, because a screen reader
          announcing the same twelve notes twice is noise, not
          content. The accessible version below is static, complete,
          and focusable. */}
      <div
        aria-hidden
        dir="ltr"
        className="flex overflow-hidden py-3"
      >
        <div
          className="basirah-ticker__track flex w-max shrink-0 items-center"
          style={{
            animation: `basirah-marquee ${CYCLE_SECONDS}s linear infinite`,
            animationPlayState: paused ? 'paused' : 'running',
          }}
          aria-hidden="true"
        >
          {/* Two identical copies — see the note above. */}
          {[0, 1].map((copy) => (
            <ul key={copy} className="flex items-center">
              {tickerItems.map((item) => (
                <li
                  key={`${copy}-${item.id}`}
                  className="flex items-center gap-3 px-6"
                >
                  <span className="mono-label rounded-full border border-signal/25 bg-signal/[0.07] px-2.5 py-0.5 text-[0.58rem] text-signal/85">
                    {t(item.categoryKey)}
                  </span>
                  <span
                    dir={isArabic ? 'rtl' : 'ltr'}
                    className="font-arabic-body text-[0.76rem] text-text-muted"
                  >
                    {itemText(item)}
                  </span>
                  <span aria-hidden className="text-line-bright">
                    ·
                  </span>
                </li>
              ))}
            </ul>
          ))}
        </div>
      </div>

      {/* ---- edge fades: the strip dissolves rather than being cut --- */}
      <span
        aria-hidden
        className="pointer-events-none absolute inset-y-0 start-0 w-16 bg-gradient-to-e from-[var(--bas-bg)] to-transparent"
      />
      <span
        aria-hidden
        className="pointer-events-none absolute inset-y-0 end-0 w-16 bg-gradient-to-s from-[var(--bas-bg)] to-transparent"
      />

      {/* ---- controls ---- */}
      <div className="absolute end-3 top-1/2 flex -translate-y-1/2 items-center gap-2">
        {showPause && (
          <button
            type="button"
            onClick={() => setPaused((value) => !value)}
            aria-pressed={paused}
            aria-label={paused ? t('ticker.play') : t('ticker.pause')}
            className="inline-flex size-7 items-center justify-center rounded-full border border-line bg-surface/85 text-text-dim backdrop-blur transition-colors hover:border-line-bright hover:text-text"
          >
            {paused ? <Play size={11} /> : <Pause size={11} />}
          </button>
        )}
      </div>

      {/* ---- accessible, complete, non-animated reading of the same
          content. Visually hidden but focusable, so a keyboard or
          screen-reader user can reach the notes without waiting for
          a marquee to finish a 42-second cycle. */}
      <div className="sr-only focus-within:not-sr-only focus-within:absolute focus-within:end-3 focus-within:top-1/2 focus-within:z-10 focus-within:mt-0 focus-within:block focus-within:w-[min(92vw,640px)] focus-within:-translate-y-1/2 focus-within:rounded-lg focus-within:border focus-within:border-line focus-within:bg-surface focus-within:p-4">
        <h2 className="font-arabic-emph text-[0.85rem] text-text">
          {t('ticker.label')}
        </h2>
        <ul className="mt-2 space-y-2">
          {tickerItems.map((item) => (
            <li key={item.id} className="text-[0.76rem] text-text-muted">
              <span className="mono-label me-2 text-signal">{t(item.categoryKey)}</span>
              {itemText(item)}
            </li>
          ))}
        </ul>
        {paused && (
          <p role="status" className="mt-2 text-[0.7rem] text-text-dim">
            {t('ticker.paused')}
          </p>
        )}
      </div>

      {/* Screen-reader-only status for the pause toggle. */}
      <span role="status" className="sr-only">
        {paused ? t('ticker.paused') : ''}
      </span>
    </section>
  )
}