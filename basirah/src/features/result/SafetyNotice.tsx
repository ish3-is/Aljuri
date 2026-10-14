import { motion } from 'motion/react'
import { ShieldAlert } from 'lucide-react'
import { useI18n } from '../../i18n/useI18n'

/* ============================================================
   SAFETY NOTICE

   The standing limitation on every image result.

   Deliberately NOT dismissible and NOT styled as an error. A notice
   the user can close is a notice they will close; this is the
   condition under which the result should be read, so it stays on
   screen for as long as the result does.

   The wording is fixed product copy rather than backend prose,
   because it is a claim about how BASIRAH may be used — not a fact
   about this particular image — and that claim must not vary with
   the pipeline's response.
   ============================================================ */

export function SafetyNotice() {
  const { t } = useI18n()

  return (
    <motion.aside
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.5, duration: 0.5 }}
      className="flex items-start gap-3.5 rounded-lg border border-line/70 bg-surface/30 px-4 py-3.5 sm:px-5"
      aria-label={t('image.safety.label')}
    >
      <ShieldAlert
        size={15}
        aria-hidden
        className="mt-0.5 shrink-0 text-text-dim"
      />
      <div className="min-w-0">
        <p className="mono-label text-text-dim">{t('image.safety.label')}</p>
        <p className="mt-1.5 text-[0.8rem] leading-relaxed text-text-muted">
          {t('image.safety.notice')}
        </p>
      </div>
    </motion.aside>
  )
}