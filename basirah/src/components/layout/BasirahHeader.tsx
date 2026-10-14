import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { Menu, X } from 'lucide-react'
import { useI18n } from '../../i18n/useI18n'
import { checkBackendAvailable } from '../../features/analysis/providers'
import { SECTIONS, type SectionId } from '../../app/sections'
import { cn } from '../../lib/utils'
import { BasirahMark } from '../brand/BasirahMark'
import { ThemeToggle } from './ThemeToggle'

/* ------------------------------------------------------------------ */
/* Language toggle                                                    */
/* ------------------------------------------------------------------ */

/**
 * Segmented EN / AR control. Both options stay rendered (rather than a
 * single swap button) because it makes the available languages
 * discoverable and the current one unmistakable.
 */
export function LanguageToggle({ className }: { className?: string }) {
  const { language, setLanguage, t } = useI18n()

  const options = [
    { code: 'en', label: 'EN', name: 'English', title: t('language.switchToEnglish') },
    { code: 'ar', label: 'ع', name: 'Arabic', title: t('language.switchToArabic') },
  ] as const

  return (
    <div
      role="group"
      aria-label={t('language.toggle')}
      className={cn(
        'relative inline-flex items-center rounded-full border border-line',
        'bg-surface/60 p-0.5',
        className,
      )}
    >
      {options.map((option) => {
        const active = language === option.code
        return (
          <button
            key={option.code}
            type="button"
            onClick={() => setLanguage(option.code)}
            aria-pressed={active}
            title={option.title}
            className={cn(
              'relative z-10 rounded-full px-3 py-1 text-xs transition-colors duration-200',
              active ? 'text-void' : 'text-text-dim hover:text-text-muted',
              option.code === 'ar' ? 'font-[var(--font-arabic)] text-sm' : 'mono-label',
            )}
          >
            {active && (
              <motion.span
                layoutId="language-pill"
                aria-hidden
                className="absolute inset-0 -z-10 rounded-full bg-signal"
                transition={{ type: 'spring', stiffness: 380, damping: 32 }}
              />
            )}
            <span lang={option.code}>{option.label}</span>
          </button>
        )
      })}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* System status                                                      */
/* ------------------------------------------------------------------ */

/**
 * Honest status line.
 *
 * This used to say "Demo mode" unconditionally, which was accurate only
 * while there was no backend at all. With live image and URL models
 * behind the service, an unconditional "Demo mode" label became a false
 * statement about real analysis.
 *
 * It reflects whether a backend is actually reachable, probed once per
 * session. When the probe fails it reads "Service offline" rather than
 * "Demo mode", because the analysis path has no mock fallback: an
 * unreachable backend produces an explicit error, never a simulated
 * result. The dot turns caution-coloured to match.
 */
export function SystemStatus() {
  const { t } = useI18n()
  const [live, setLive] = useState<boolean | null>(null)

  useEffect(() => {
    let cancelled = false
    checkBackendAvailable()
      .then((ok: boolean) => {
        if (!cancelled) setLive(ok)
      })
      .catch(() => {
        if (!cancelled) setLive(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const label = live ? t('status.live') : t('status.demoMode')
  const tooltip = live ? t('status.liveTooltip') : t('status.tooltip')

  return (
    <div
      className="group relative inline-flex items-center gap-2"
      title={tooltip}
      data-testid="system-status"
      data-live={live === null ? 'unknown' : String(live)}
    >
      <span className="relative flex size-1.5" aria-hidden>
        <span
          className={cn(
            'absolute inline-flex size-full animate-ping rounded-full',
            live ? 'bg-trusted/70' : 'bg-caution/60',
          )}
        />
        <span
          className={cn(
            'relative inline-flex size-1.5 rounded-full',
            live ? 'bg-trusted' : 'bg-caution',
          )}
        />
      </span>
      <span className="mono-label text-text-dim">{label}</span>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Header                                                             */
/* ------------------------------------------------------------------ */

interface BasirahHeaderProps {
  section: SectionId
  onNavigate: (section: SectionId) => void
}

/**
 * The header is the product's table of contents: identity on the
 * inline-start edge, the seven sections as the primary landmark, and
 * the language switch always visible.
 *
 * Section links are real anchors pointing at hash URLs, so browser
 * Back, middle-click and "open in new tab" all behave correctly. Only
 * a plain unmodified left click is intercepted, which keeps every
 * native affordance intact.
 */
export function BasirahHeader({ section, onNavigate }: BasirahHeaderProps) {
  const { t, tLatin, language } = useI18n()
  const [menuOpen, setMenuOpen] = useState(false)

  const isArabic = language === 'ar'

  /** Intercept only a plain left click; let modified clicks through. */
  const handleNavClick = (
    event: React.MouseEvent<HTMLAnchorElement>,
    id: SectionId,
  ) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) {
      return
    }
    event.preventDefault()
    // Choosing a destination also dismisses the menu that listed it.
    // Closing here rather than in an effect keyed on `section` keeps
    // the state transition in the same event as the click, which is
    // where the user actually expressed the intent.
    setMenuOpen(false)
    onNavigate(id)
  }

  return (
    <motion.header
      initial={{ opacity: 0, y: -14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
      className="fixed inset-x-0 top-0 z-50"
    >
      <div className="panel-glass border-x-0 border-t-0">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-4 px-5 py-3 sm:px-6">
          {/* Identity */}
          <a
            href="#/overview"
            onClick={(event) => handleNavClick(event, 'overview')}
            className="flex shrink-0 items-center gap-3"
          >
            <BasirahMark size={28} />
            <span className="hidden leading-none sm:block">
              <span
                className="block text-[0.9rem] font-medium tracking-[0.14em] text-text"
                dir="ltr"
              >
                {tLatin('brand.name')}
              </span>
              <span className="mt-1 block max-w-[14rem] truncate text-[0.62rem] tracking-[0.04em] text-text-dim">
                {t('brand.subtitle')}
              </span>
            </span>
          </a>

          {/* Primary navigation (desktop) */}
          <nav aria-label={t('nav.label')} className="hidden lg:block">
            <ul className="flex items-center gap-0.5">
              {SECTIONS.map((item) => {
                const active = section === item.id
                return (
                  <li key={item.id}>
                    <a
                      href={`#/${item.id}`}
                      onClick={(event) => handleNavClick(event, item.id)}
                      aria-current={active ? 'page' : undefined}
                      className={cn(
                        'relative block rounded-full px-3 py-1.5 text-[0.76rem] transition-colors duration-200',
                        // Arabic nav labels take the Medium weight of the
                        // display face; English keeps its tight tracking.
                        'font-arabic-emph',
                        active ? 'text-signal' : 'text-text-dim hover:text-text-muted',
                      )}
                    >
                      {active && (
                        <motion.span
                          layoutId="nav-pill"
                          aria-hidden
                          className="absolute inset-0 -z-10 rounded-full border border-signal/25 bg-signal/[0.08]"
                          transition={{ type: 'spring', stiffness: 380, damping: 34 }}
                        />
                      )}
                      {t(item.labelKey)}
                    </a>
                  </li>
                )
              })}
            </ul>
          </nav>

          {/* Actions */}
          <div className="flex shrink-0 items-center gap-3">
            <div className="hidden xl:block">
              <SystemStatus />
            </div>

            <LanguageToggle />

            <ThemeToggle />

            <button
              type="button"
              onClick={() => setMenuOpen((open) => !open)}
              aria-expanded={menuOpen}
              aria-label={menuOpen ? t('nav.close') : t('nav.open')}
              className={cn(
                'inline-flex size-9 items-center justify-center rounded-full lg:hidden',
                'border border-line text-text-dim transition-all duration-200',
                'hover:border-line-bright hover:text-text',
                menuOpen && 'border-signal/40 text-signal',
                isArabic && 'rtl:-scale-x-100',
              )}
            >
              {menuOpen ? <X size={16} /> : <Menu size={16} />}
            </button>
          </div>
        </div>

        {/* Compact nav sheet */}
        <AnimatePresence>
          {menuOpen && (
            <motion.nav
              aria-label={t('nav.label')}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
              className="overflow-hidden border-t border-line/70 lg:hidden"
            >
              <ul className="mx-auto grid max-w-[1400px] grid-cols-2 gap-1 px-5 py-3 sm:px-6">
                {SECTIONS.map((item) => {
                  const active = section === item.id
                  return (
                    <li key={item.id}>
                      <a
                        href={`#/${item.id}`}
                        onClick={(event) => handleNavClick(event, item.id)}
                        aria-current={active ? 'page' : undefined}
                        className={cn(
                          'block rounded-md px-3 py-2 text-[0.8rem] font-arabic-emph transition-colors duration-200',
                          active
                            ? 'bg-signal/[0.08] text-signal'
                            : 'text-text-muted hover:bg-surface-raised/60 hover:text-text',
                        )}
                      >
                        {t(item.labelKey)}
                      </a>
                    </li>
                  )
                })}
              </ul>
              <div className="border-t border-line/60 px-5 py-3 sm:px-6">
                <SystemStatus />
              </div>
            </motion.nav>
          )}
        </AnimatePresence>
      </div>
    </motion.header>
  )
}
