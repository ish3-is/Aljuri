import { motion } from 'motion/react'
import { Moon, Sun } from 'lucide-react'
import { useI18n } from '../../i18n/useI18n'
import { useTheme } from '../../hooks/useTheme'

/* ============================================================
   THEME TOGGLE

   Sun/moon with the two icons stacked in a fixed-size box and a
   slide between them, rather than swapping one glyph for another.
   The transition carries the direction of the change, which a
   cross-fade does not.

   A real <button> with an explicit aria-label that states the
   ACTION ("Switch to light theme"), not the current state: a
   screen-reader user needs to know what pressing it will do. The
   current theme is exposed separately through aria-live so the
   result of the press is announced.

   `title` mirrors the aria-label, because the control is icon-only
   and a sighted keyboard user gets no tooltip otherwise.
   ============================================================ */

export function ThemeToggle({ className }: { className?: string }) {
  const { t } = useI18n()
  const { theme, toggleTheme } = useTheme()

  const isDark = theme === 'dark'
  const label = isDark ? t('theme.switchToLight') : t('theme.switchToDark')

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={label}
      title={label}
      className={[
        'relative inline-flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-full',
        'border border-line text-text-dim transition-colors duration-200',
        'hover:border-line-bright hover:text-text',
        className ?? '',
      ].join(' ')}
    >
      <motion.span
        aria-hidden
        className="absolute inset-0 flex items-center justify-center"
        animate={{ y: isDark ? 0 : '-140%' }}
        transition={{ type: 'spring', stiffness: 340, damping: 30 }}
      >
        {/* In dark mode the sun is the affordance (click for light). */}
        {isDark ? <Sun size={15} /> : <Moon size={15} />}
      </motion.span>

      {/* Announces the resulting state after a press. */}
      <span role="status" className="sr-only">
        {`${t('theme.current')}: ${isDark ? t('theme.dark') : t('theme.light')}`}
      </span>
    </button>
  )
}